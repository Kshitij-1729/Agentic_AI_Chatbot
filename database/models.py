"""
Database CRUD operations for conversations, messages, summaries, and tool calls.
"""

import uuid
from datetime import datetime
from typing import Optional
from database.connection import DatabaseConnection as DB


# ================================================================
#  CONVERSATIONS
# ================================================================

def create_conversation(
    title: str = "New Chat",
    llm_provider: str = "openai",
    llm_model: str = "gpt-4o",
    tool_mode: str = "auto",
) -> str:
    """Create a new conversation and return its UUID."""
    conv_id = str(uuid.uuid4())
    DB.execute_query(
        """
        INSERT INTO conversations (id, title, llm_provider, llm_model, tool_mode)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (conv_id, title, llm_provider, llm_model, tool_mode),
        fetch=False,
    )
    return conv_id


def get_conversation(conversation_id: str) -> Optional[dict]:
    """Get a single conversation by ID."""
    rows = DB.execute_query(
        "SELECT * FROM conversations WHERE id = %s",
        (conversation_id,),
    )
    return rows[0] if rows else None


def list_conversations(include_archived: bool = False) -> list:
    """List conversations ordered by most recent activity."""
    if include_archived:
        query = "SELECT * FROM conversations ORDER BY updated_at DESC"
        params = None
    else:
        query = "SELECT * FROM conversations WHERE is_archived = 0 ORDER BY updated_at DESC"
        params = None
    return DB.execute_query(query, params)


def update_conversation_title(conversation_id: str, title: str):
    """Rename a conversation."""
    DB.execute_query(
        "UPDATE conversations SET title = %s WHERE id = %s",
        (title, conversation_id),
        fetch=False,
    )


def update_conversation_settings(conversation_id: str, **kwargs):
    """Update llm_provider, llm_model, or tool_mode."""
    allowed = {"llm_provider", "llm_model", "tool_mode"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    set_clause = ", ".join(f"{k} = %s" for k in updates)
    values = list(updates.values()) + [conversation_id]
    DB.execute_query(
        f"UPDATE conversations SET {set_clause} WHERE id = %s",
        tuple(values),
        fetch=False,
    )


def delete_conversation(conversation_id: str):
    """Delete a conversation and all related data (cascade)."""
    DB.execute_query(
        "DELETE FROM conversations WHERE id = %s",
        (conversation_id,),
        fetch=False,
    )


# ================================================================
#  MESSAGES
# ================================================================

def add_message(
    conversation_id: str,
    role: str,
    content: str,
    token_count: int = 0,
) -> int:
    """Insert a message and return its ID."""
    msg_id = DB.execute_query(
        """
        INSERT INTO messages (conversation_id, role, content, token_count)
        VALUES (%s, %s, %s, %s)
        """,
        (conversation_id, role, content, token_count),
        fetch=False,
    )
    # Touch the conversation's updated_at
    DB.execute_query(
        "UPDATE conversations SET updated_at = NOW() WHERE id = %s",
        (conversation_id,),
        fetch=False,
    )
    return msg_id


def get_messages(conversation_id: str, limit: int = 50) -> list:
    """Retrieve messages for a conversation ordered chronologically."""
    return DB.execute_query(
        """
        SELECT * FROM messages
        WHERE conversation_id = %s
        ORDER BY created_at ASC
        LIMIT %s
        """,
        (conversation_id, limit),
    )


def get_recent_messages(conversation_id: str, count: int = 10) -> list:
    """Get the N most recent messages (for context window)."""
    rows = DB.execute_query(
        """
        SELECT * FROM messages
        WHERE conversation_id = %s
        ORDER BY created_at DESC
        LIMIT %s
        """,
        (conversation_id, count),
    )
    return list(reversed(rows))


def get_unsummarized_messages(conversation_id: str) -> list:
    """Get messages not yet included in any summary."""
    return DB.execute_query(
        """
        SELECT * FROM messages
        WHERE conversation_id = %s AND is_summarized = 0
        ORDER BY created_at ASC
        """,
        (conversation_id,),
    )


def mark_messages_as_summarized(message_ids: list):
    """Flag messages as summarized."""
    if not message_ids:
        return
    placeholders = ",".join(["%s"] * len(message_ids))
    DB.execute_query(
        f"UPDATE messages SET is_summarized = 1 WHERE id IN ({placeholders})",
        tuple(message_ids),
        fetch=False,
    )


def count_messages(conversation_id: str) -> int:
    """Count total messages in a conversation."""
    rows = DB.execute_query(
        "SELECT COUNT(*) as cnt FROM messages WHERE conversation_id = %s",
        (conversation_id,),
    )
    return rows[0]["cnt"] if rows else 0


# ================================================================
#  SUMMARIES
# ================================================================

def upsert_summary(conversation_id: str, summary: str, summarized_up_to: int, message_count: int):
    """Insert or update a conversation summary."""
    DB.execute_query(
        """
        INSERT INTO conversation_summaries
            (conversation_id, summary, summarized_up_to, message_count)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            summary = VALUES(summary),
            summarized_up_to = VALUES(summarized_up_to),
            message_count = VALUES(message_count),
            updated_at = NOW()
        """,
        (conversation_id, summary, summarized_up_to, message_count),
        fetch=False,
    )


def get_summary(conversation_id: str) -> Optional[dict]:
    """Get the latest summary for a conversation."""
    rows = DB.execute_query(
        "SELECT * FROM conversation_summaries WHERE conversation_id = %s",
        (conversation_id,),
    )
    return rows[0] if rows else None


# ================================================================
#  TOOL CALLS
# ================================================================

def log_tool_call(
    conversation_id: str,
    tool_name: str,
    tool_input: str = "",
    tool_output: str = "",
    execution_time_ms: int = 0,
    message_id: int = None,
    status: str = "success",
) -> int:
    """Record a tool invocation."""
    return DB.execute_query(
        """
        INSERT INTO tool_calls
            (message_id, conversation_id, tool_name, tool_input, tool_output, execution_time_ms, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (message_id, conversation_id, tool_name, tool_input, tool_output, execution_time_ms, status),
        fetch=False,
    )


# ================================================================
#  AGENT LOGS
# ================================================================

def log_agent_execution(
    conversation_id: str,
    agent_type: str,
    node_name: str = None,
    input_summary: str = None,
    output_summary: str = None,
    execution_time_ms: int = 0,
    message_id: int = None,
) -> int:
    """Record an agent node execution for debugging / auditing."""
    return DB.execute_query(
        """
        INSERT INTO agent_logs
            (conversation_id, message_id, agent_type, node_name, input_summary, output_summary, execution_time_ms)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (conversation_id, message_id, agent_type, node_name, input_summary, output_summary, execution_time_ms),
        fetch=False,
    )

# ================================================================
#  UPLOADED FILES
# ================================================================

def add_uploaded_file(file_name: str, file_path: str, file_size: int) -> int:
    """Record an uploaded file."""
    return DB.execute_query(
        """
        INSERT INTO uploaded_files (file_name, file_path, file_size)
        VALUES (%s, %s, %s)
        """,
        (file_name, file_path, file_size),
        fetch=False,
    )

def get_uploaded_file_by_name(file_name: str) -> Optional[dict]:
    """Retrieve an uploaded file by its name."""
    rows = DB.execute_query(
        "SELECT * FROM uploaded_files WHERE file_name = %s",
        (file_name,)
    )
    return rows[0] if rows else None

def list_uploaded_files() -> list:
    """Get a list of all uploaded files, ordered newest first."""
    return DB.execute_query(
        "SELECT * FROM uploaded_files ORDER BY uploaded_at DESC"
    )
