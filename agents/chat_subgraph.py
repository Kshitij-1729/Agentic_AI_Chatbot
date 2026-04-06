"""
Chat Subgraph — the CORE agent with ReAct-style tool loop.

Flow:
  START → chat_reasoning_node
    → tool_decision (conditional edge)
      → YES: tool_execution_node → loop back to chat_reasoning_node
      → NO : END (return to parent graph)
"""

from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from agents.state import AgentState
from llm.provider import get_llm
from tools.tool_registry import get_all_tools


CHAT_SYSTEM_PROMPT = """You are a highly capable AI assistant with access to tools.

Your capabilities:
- General conversation and Q&A
- Web search (use 'web_search' for current information, news, facts)
- Stock prices (use 'get_stock_price' with a ticker symbol like AAPL, GOOGL)
- Research (use 'tavily_search' for in-depth research with multiple sources)
- Document Search (use 'rag_qa_tool' as priority first for uploaded PDFs, docs, or files, or if user doesn't mention any file name)
- Vectorless RAG (use 'vectorless_rag_tool' ONLY if user asks to use vectorless rag or if 'rag_qa_tool' fails to answer the query in previous chat. If no file name is mentioned, explicitly ask the user which file they mean)

Guidelines:
1. Be helpful, accurate, and conversational
2. When the user asks about current events, real-time data, or facts you're unsure about — USE TOOLS
3. When asked about stock prices — ALWAYS use the get_stock_price tool
4. For complex research questions — use tavily_search for comprehensive results
5. You can chain multiple tool calls if needed
6. After getting tool results, synthesize them into a clear, helpful response
7. If you don't need tools, just respond directly
8. Use markdown formatting for structured responses
9. Be concise but thorough

{summary_context}
"""


def _build_system_prompt(state: AgentState) -> str:
    """Build system prompt with optional summary context."""
    summary = state.get("summary", "")
    if summary:
        summary_context = f"\nPrevious conversation summary:\n{summary}\n"
    else:
        summary_context = ""
    return CHAT_SYSTEM_PROMPT.format(summary_context=summary_context)


def chat_reasoning_node(state: AgentState) -> dict:
    """
    The Chat Reasoning Node — invokes the LLM with tools bound.
    If the LLM decides to call tools, the AIMessage will contain tool_calls.
    """
    provider = state.get("llm_provider", "openai")
    model = state.get("llm_model", None)
    tool_mode = state.get("tool_mode", "auto")

    llm = get_llm(provider=provider, model=model, temperature=0.7)

    # Bind tools to LLM (unless tool_mode is 'none')
    if tool_mode != "none":
        tools = get_all_tools()
        llm_with_tools = llm.bind_tools(tools)
    else:
        llm_with_tools = llm

    # Build the message list
    system_prompt = _build_system_prompt(state)
    messages = state.get("messages", [])

    # Prepend system message
    full_messages = [SystemMessage(content=system_prompt)] + list(messages)

    # Invoke LLM
    response = llm_with_tools.invoke(full_messages)

    return {"messages": [response]}


def tool_execution_node(state: AgentState) -> dict:
    """
    Execute all tool calls from the last AIMessage and return ToolMessages.
    """
    import time
    import json

    messages = state.get("messages", [])
    last_message = messages[-1]

    tool_messages = []
    tool_calls_log = list(state.get("tool_calls_log", []))

    # Get tools as a dict for lookup
    tools = get_all_tools()
    tool_map = {t.name: t for t in tools}

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        start_time = time.time()
        try:
            if tool_name in tool_map:
                result = tool_map[tool_name].invoke(tool_args)
            else:
                result = f"Tool '{tool_name}' not found."
            status = "success"
        except Exception as e:
            result = f"Tool error: {str(e)}"
            status = "error"

        elapsed_ms = int((time.time() - start_time) * 1000)

        # Create ToolMessage
        tool_messages.append(
            ToolMessage(
                content=str(result),
                tool_call_id=tool_call["id"],
                name=tool_name,
            )
        )

        # Log tool call
        tool_calls_log.append({
            "name": tool_name,
            "input": json.dumps(tool_args),
            "output": str(result)[:2000],  # Truncate for storage
            "execution_time_ms": elapsed_ms,
            "status": status,
        })

    return {
        "messages": tool_messages,
        "tool_calls_log": tool_calls_log,
    }


def should_use_tools(state: AgentState) -> str:
    """
    Conditional edge: check if the last AIMessage contains tool_calls.
    Returns 'tool_node' or 'end'.
    """
    messages = state.get("messages", [])
    if not messages:
        return "end"

    last_message = messages[-1]

    # Check if the message has tool_calls
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tool_node"

    return "end"


def build_chat_subgraph():
    """
    Build and compile the Chat subgraph with ReAct tool loop.

    Graph structure:
      START → chat_reasoning
        → should_use_tools?
          → YES: tool_execution → chat_reasoning (loop)
          → NO : END
    """
    builder = StateGraph(AgentState)

    # Add nodes
    builder.add_node("chat_reasoning", chat_reasoning_node)
    builder.add_node("tool_execution", tool_execution_node)

    # Set entry point
    builder.set_entry_point("chat_reasoning")

    # Conditional edge from reasoning: check if tools needed
    builder.add_conditional_edges(
        "chat_reasoning",
        should_use_tools,
        {
            "tool_node": "tool_execution",
            "end": END,
        },
    )

    # After tool execution, loop back to reasoning
    builder.add_edge("tool_execution", "chat_reasoning")

    return builder.compile()


# Pre-compiled subgraph instance
chat_subgraph = build_chat_subgraph()
