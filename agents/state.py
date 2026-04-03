"""
Shared state definition for the entire LangGraph workflow.
All nodes read from / write to this state.
"""

from typing import TypedDict, Annotated, Literal
from langgraph.graph import add_messages


class AgentState(TypedDict):
    """
    The central state shared across every node in the graph.

    Attributes:
        messages          – Accumulated LangChain message objects (uses add_messages reducer)
        conversation_id   – UUID of the current conversation thread
        user_input        – The raw user query text
        intent            – Intent classified by the orchestrator
        agent_type        – Which agent branch was chosen (chat | crag | blog | travel | academic)
        agent_response    – The final textual response produced by the agent
        tool_calls_log    – List of dicts recording tool usage [{name, input, output, ms}]
        summary           – Running conversation summary (from summarizer)
        llm_provider      – 'openai' or 'gemini'
        llm_model         – Specific model identifier
        tool_mode         – 'auto' | 'manual' | 'none'
        needs_summarization – Flag set by the summarization-check node
        message_count     – Total messages in this conversation (for summarization check)
    """
    messages: Annotated[list, add_messages]
    conversation_id: str
    user_input: str
    intent: str
    agent_type: str
    agent_response: str
    tool_calls_log: list
    summary: str
    llm_provider: str
    llm_model: str
    tool_mode: str
    needs_summarization: bool
    message_count: int
