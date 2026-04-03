"""
Summarization Check + Summarizer Node.
Checks if the conversation has grown beyond the threshold
and compresses older messages into a summary.
"""

from agents.state import AgentState
from llm.provider import get_llm
from database import models as db
from config import Config
from langchain_core.messages import SystemMessage, HumanMessage


SUMMARIZER_PROMPT = """You are a conversation summarizer. 
Condense the following conversation history into a concise summary that captures:
- Key topics discussed
- Important facts, decisions, or conclusions
- User preferences or context that should be remembered
- Any pending tasks or follow-ups

Keep the summary concise but comprehensive (2-4 paragraphs max).

Conversation to summarize:
{conversation_text}

Previous summary (if any):
{previous_summary}

Provide an updated, merged summary:"""


def summarization_check_node(state: AgentState) -> dict:
    """
    Check if messages exceed the threshold.
    Sets `needs_summarization` flag.
    """
    message_count = state.get("message_count", 0)
    threshold = Config.MAX_MESSAGES_BEFORE_SUMMARY

    needs_summarization = message_count > threshold

    return {"needs_summarization": needs_summarization}


def should_summarize(state: AgentState) -> str:
    """Conditional edge: route to summarizer or end."""
    if state.get("needs_summarization", False):
        return "summarizer"
    return "end"


def summarizer_node(state: AgentState) -> dict:
    """
    Compress older messages into a summary.
    Keeps the last N messages intact, summarizes the rest.
    """
    conversation_id = state.get("conversation_id", "")
    provider = state.get("llm_provider", "openai")
    model = state.get("llm_model", None)

    if not conversation_id:
        return {}

    try:
        # Get unsummarized messages
        unsummarized = db.get_unsummarized_messages(conversation_id)

        if len(unsummarized) <= Config.MESSAGES_TO_KEEP_AFTER_SUMMARY:
            return {"needs_summarization": False}

        # Messages to summarize (all except the last N)
        keep_count = Config.MESSAGES_TO_KEEP_AFTER_SUMMARY
        messages_to_summarize = unsummarized[:-keep_count]
        messages_to_keep = unsummarized[-keep_count:]

        if not messages_to_summarize:
            return {"needs_summarization": False}

        # Build conversation text for summarization
        conversation_text = ""
        for msg in messages_to_summarize:
            role = msg["role"].upper()
            content = msg["content"]
            conversation_text += f"{role}: {content}\n\n"

        # Get previous summary if exists
        existing_summary = db.get_summary(conversation_id)
        previous_summary = existing_summary["summary"] if existing_summary else "None"

        # Call LLM to summarize
        llm = get_llm(provider=provider, model=model, temperature=0.3)
        prompt = SUMMARIZER_PROMPT.format(
            conversation_text=conversation_text,
            previous_summary=previous_summary,
        )

        response = llm.invoke([
            SystemMessage(content="You are a precise conversation summarizer."),
            HumanMessage(content=prompt),
        ])

        new_summary = response.content

        # Mark old messages as summarized
        msg_ids = [m["id"] for m in messages_to_summarize]
        db.mark_messages_as_summarized(msg_ids)

        # Upsert summary in DB
        last_summarized_id = messages_to_summarize[-1]["id"]
        db.upsert_summary(
            conversation_id=conversation_id,
            summary=new_summary,
            summarized_up_to=last_summarized_id,
            message_count=len(msg_ids),
        )

        return {
            "summary": new_summary,
            "needs_summarization": False,
        }

    except Exception as e:
        print(f"[Summarizer] Error: {e}")
        return {"needs_summarization": False}
