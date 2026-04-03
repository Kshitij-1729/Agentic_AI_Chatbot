"""
Memory Update Node — persists the conversation turn to MySQL
and records tool call logs.
"""

from agents.state import AgentState
from database import models as db
from config import Config


def memory_update_node(state: AgentState) -> dict:
    """
    Store the current turn's user message and assistant response in MySQL.
    Also persist tool call logs if any.
    """
    conversation_id = state.get("conversation_id", "")
    user_input = state.get("user_input", "")
    agent_response = state.get("agent_response", "")
    tool_calls_log = state.get("tool_calls_log", [])

    if not conversation_id:
        return {"message_count": 0}

    try:
        # Store user message
        user_msg_id = db.add_message(
            conversation_id=conversation_id,
            role="user",
            content=user_input,
        )

        # Store assistant response
        assistant_msg_id = db.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=agent_response,
        )

        # Store tool calls
        for tc in tool_calls_log:
            db.log_tool_call(
                conversation_id=conversation_id,
                tool_name=tc.get("name", ""),
                tool_input=tc.get("input", ""),
                tool_output=tc.get("output", ""),
                execution_time_ms=tc.get("execution_time_ms", 0),
                message_id=assistant_msg_id,
                status=tc.get("status", "success"),
            )

        # Get current message count for summarization check
        message_count = db.count_messages(conversation_id)

        # Log agent execution
        db.log_agent_execution(
            conversation_id=conversation_id,
            agent_type=state.get("agent_type", "chat"),
            node_name="memory_update",
            input_summary=user_input[:200],
            output_summary=agent_response[:200],
            message_id=assistant_msg_id,
        )

    except Exception as e:
        print(f"[MemoryNode] Error persisting: {e}")
        message_count = 0

    return {
        "message_count": message_count,
        "tool_calls_log": [],  # Clear after persisting
    }
