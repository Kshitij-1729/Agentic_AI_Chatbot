"""
Travel Agent Subgraph — PLACEHOLDER.
Will be implemented later with travel planning capabilities.
"""

from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage
from agents.state import AgentState


def travel_placeholder_node(state: AgentState) -> dict:
    """
    Placeholder node for the Travel Agent subgraph.
    """
    response = AIMessage(
        content=(
            "🚧 **Travel Agent — Under Development**\n\n"
            "The Travel Agent is currently being built. "
            "It will support:\n"
            "- Personalized travel itinerary creation\n"
            "- Destination research and recommendations\n"
            "- Flight and hotel suggestions\n"
            "- Budget planning and travel tips\n\n"
            "For now, please use the general chat for your travel questions!"
        )
    )
    return {
        "messages": [response],
        "agent_response": response.content,
    }


def build_travel_subgraph():
    """Build and compile the Travel placeholder subgraph."""
    builder = StateGraph(AgentState)
    builder.add_node("travel_node", travel_placeholder_node)
    builder.set_entry_point("travel_node")
    builder.add_edge("travel_node", END)
    return builder.compile()


travel_subgraph = build_travel_subgraph()
