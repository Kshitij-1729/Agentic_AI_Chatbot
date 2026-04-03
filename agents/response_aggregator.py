"""
Response Aggregator Node — extracts the final response from
whichever agent subgraph ran, and places it in `agent_response`.
"""

from agents.state import AgentState


def response_aggregator_node(state: AgentState) -> dict:
    """
    After an agent subgraph finishes, the last AI message in `messages`
    is the agent's final answer. Extract it into `agent_response`.
    """
    messages = state.get("messages", [])
    agent_response = ""

    # Walk backward to find the last AIMessage
    for msg in reversed(messages):
        if hasattr(msg, "type") and msg.type == "ai":
            # Skip messages that are pure tool-call requests (no content)
            if msg.content:
                agent_response = msg.content
                break

    return {"agent_response": agent_response}
