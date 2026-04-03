"""
Academic Agent Subgraph — PLACEHOLDER.
Will be implemented later with academic research capabilities.
"""

from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage
from agents.state import AgentState


def academic_placeholder_node(state: AgentState) -> dict:
    """
    Placeholder node for the Academic Agent subgraph.
    """
    response = AIMessage(
        content=(
            "🚧 **Academic Agent — Under Development**\n\n"
            "The Academic Agent is currently being built. "
            "It will support:\n"
            "- Research paper summarization\n"
            "- Literature review assistance\n"
            "- Citation generation and management\n"
            "- Study planning and concept explanation\n\n"
            "For now, please use the general chat for your academic questions!"
        )
    )
    return {
        "messages": [response],
        "agent_response": response.content,
    }


def build_academic_subgraph():
    """Build and compile the Academic placeholder subgraph."""
    builder = StateGraph(AgentState)
    builder.add_node("academic_node", academic_placeholder_node)
    builder.set_entry_point("academic_node")
    builder.add_edge("academic_node", END)
    return builder.compile()


academic_subgraph = build_academic_subgraph()
