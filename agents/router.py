"""
Conditional Router — routes the workflow to the correct agent subgraph
based on the intent determined by the Orchestrator.
"""

from agents.state import AgentState


def route_to_agent(state: AgentState) -> str:
    """
    Conditional edge function: returns the node name to route to.
    Maps agent_type → subgraph node name.
    """
    agent_type = state.get("agent_type", "chat")

    route_map = {
        "chat": "chat_subgraph",
        "crag": "crag_subgraph",
        "blog": "blog_subgraph",
        "travel": "travel_subgraph",
        "academic": "academic_subgraph",
    }

    return route_map.get(agent_type, "chat_subgraph")
