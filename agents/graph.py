"""
Main LangGraph Workflow — assembles all nodes and subgraphs into
the complete agentic workflow.

FLOW:
  START
    → Orchestrator Node (intent + planning)
    → Conditional Router
      → Chat Subgraph (with tool loop) | CRAG | Blog | Travel | Academic
    → Response Aggregator
    → Memory Update Node
    → Summarization Check
      → [Yes] Summarizer → END
      → [No]  END
"""

from langgraph.graph import StateGraph, END
from agents.state import AgentState

# Import nodes
from agents.orchestrator import orchestrator_node
from agents.router import route_to_agent
from agents.response_aggregator import response_aggregator_node
from agents.memory_node import memory_update_node
from agents.summarizer import (
    summarization_check_node,
    should_summarize,
    summarizer_node,
)

# Import subgraphs
from agents.chat_subgraph import chat_subgraph
from agents.crag_subgraph import crag_subgraph
from agents.blog_subgraph import blog_subgraph
from agents.travel_subgraph import travel_subgraph
from agents.academic_subgraph import academic_subgraph


def build_main_graph():
    """
    Build and compile the main workflow graph.
    """
    builder = StateGraph(AgentState)

    # ─── 1. Add all nodes ────────────────────────────────
    builder.add_node("orchestrator", orchestrator_node)

    # Subgraphs added as compiled graph nodes
    builder.add_node("chat_subgraph", chat_subgraph)
    builder.add_node("crag_subgraph", crag_subgraph)
    builder.add_node("blog_subgraph", blog_subgraph)
    builder.add_node("travel_subgraph", travel_subgraph)
    builder.add_node("academic_subgraph", academic_subgraph)

    # Post-agent nodes
    builder.add_node("response_aggregator", response_aggregator_node)
    builder.add_node("memory_update", memory_update_node)
    builder.add_node("summarization_check", summarization_check_node)
    builder.add_node("summarizer", summarizer_node)

    # ─── 2. Set entry point ──────────────────────────────
    builder.set_entry_point("orchestrator")

    # ─── 3. Orchestrator → Conditional Router ────────────
    builder.add_conditional_edges(
        "orchestrator",
        route_to_agent,
        {
            "chat_subgraph": "chat_subgraph",
            "crag_subgraph": "crag_subgraph",
            "blog_subgraph": "blog_subgraph",
            "travel_subgraph": "travel_subgraph",
            "academic_subgraph": "academic_subgraph",
        },
    )

    # ─── 4. All subgraphs → Response Aggregator ─────────
    builder.add_edge("chat_subgraph", "response_aggregator")
    builder.add_edge("crag_subgraph", "response_aggregator")
    builder.add_edge("blog_subgraph", "response_aggregator")
    builder.add_edge("travel_subgraph", "response_aggregator")
    builder.add_edge("academic_subgraph", "response_aggregator")

    # ─── 5. Response Aggregator → Memory Update ──────────
    builder.add_edge("response_aggregator", "memory_update")

    # ─── 6. Memory Update → Summarization Check ─────────
    builder.add_edge("memory_update", "summarization_check")

    # ─── 7. Summarization Check → Summarizer or END ─────
    builder.add_conditional_edges(
        "summarization_check",
        should_summarize,
        {
            "summarizer": "summarizer",
            "end": END,
        },
    )

    # ─── 8. Summarizer → END ────────────────────────────
    builder.add_edge("summarizer", END)

    # ─── 9. Compile ─────────────────────────────────────
    compiled_graph = builder.compile()
    print("[Graph] Main workflow compiled successfully")
    return compiled_graph


# ═══════════════════════════════════════════════════════════
#  Public API
# ═══════════════════════════════════════════════════════════

# Compile the graph once at import time
workflow = build_main_graph()


def run_agent(
    user_input: str,
    conversation_id: str,
    llm_provider: str = "openai",
    llm_model: str = None,
    tool_mode: str = "auto",
    summary: str = "",
    history_messages: list = None,
) -> dict:
    """
    Run the full agentic workflow for a single user turn.

    Args:
        user_input:       The user's message text
        conversation_id:  UUID of the conversation
        llm_provider:     'openai' or 'gemini'
        llm_model:        specific model name
        tool_mode:        'auto', 'manual', or 'none'
        summary:          existing conversation summary
        history_messages: list of LangChain messages for context

    Returns:
        dict with 'response', 'tool_calls', 'summary'
    """
    from langchain_core.messages import HumanMessage

    # Build initial messages list with history
    messages = []
    if history_messages:
        messages.extend(history_messages)
    messages.append(HumanMessage(content=user_input))

    # Build initial state
    initial_state = {
        "messages": messages,
        "conversation_id": conversation_id,
        "user_input": user_input,
        "intent": "",
        "agent_type": "",
        "agent_response": "",
        "tool_calls_log": [],
        "summary": summary,
        "llm_provider": llm_provider,
        "llm_model": llm_model or "",
        "tool_mode": tool_mode,
        "needs_summarization": False,
        "message_count": 0,
    }

    # Run the graph
    try:
        final_state = workflow.invoke(initial_state)

        return {
            "response": final_state.get("agent_response", "I apologize, I couldn't generate a response."),
            "tool_calls": final_state.get("tool_calls_log", []),
            "summary": final_state.get("summary", summary),
            "agent_type": final_state.get("agent_type", "chat"),
            "intent": final_state.get("intent", ""),
        }

    except Exception as e:
        print(f"[Graph] Error running workflow: {e}")
        import traceback
        traceback.print_exc()
        return {
            "response": f"I encountered an error while processing your request. Please try again.\n\nError: {str(e)}",
            "tool_calls": [],
            "summary": summary,
            "agent_type": "chat",
            "intent": "error",
        }
