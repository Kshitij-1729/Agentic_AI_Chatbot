"""
CRAG (Corrective Retrieval-Augmented Generation) Subgraph — PLACEHOLDER.
Will be implemented later with document retrieval and fact-checking capabilities.
"""

from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage
from agents.state import AgentState


def crag_placeholder_node(state: AgentState) -> dict:
    """
    Placeholder node for the CRAG subgraph.
    Returns a message indicating the feature is under development.
    """
    response = AIMessage(
        content=(
            "🚧 **CRAG Agent — Under Development**\n\n"
            "The Corrective Retrieval-Augmented Generation agent is currently being built. "
            "It will support:\n"
            "- Document retrieval from knowledge bases\n"
            "- Fact-checking and correction of retrieved information\n"
            "- Grounded, citation-backed responses\n\n"
            "For now, please use the general chat for your query. "
            "I'll do my best to help!"
        )
    )
    return {
        "messages": [response],
        "agent_response": response.content,
    }


def build_crag_subgraph():
    """Build and compile the CRAG placeholder subgraph."""
    builder = StateGraph(AgentState)
    builder.add_node("crag_node", crag_placeholder_node)
    builder.set_entry_point("crag_node")
    builder.add_edge("crag_node", END)
    return builder.compile()


crag_subgraph = build_crag_subgraph()
