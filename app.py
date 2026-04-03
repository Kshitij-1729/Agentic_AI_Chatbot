"""
Flask Application — REST API for the Agentic Chatbot.

Endpoints:
  POST   /api/chat                         — Send message, get response
  GET    /api/conversations                — List all conversations
  POST   /api/conversations                — Create new conversation
  GET    /api/conversations/<id>           — Get conversation + messages
  DELETE /api/conversations/<id>           — Delete conversation
  PUT    /api/conversations/<id>/title     — Rename conversation
  PUT    /api/conversations/<id>/settings  — Update LLM/tool settings
  GET    /api/providers                    — List available LLM providers
  GET    /api/health                       — Health check
"""

import os
import traceback
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from config import Config
from database.connection import DatabaseConnection
from database import models as db
from llm.provider import list_providers

app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates",
)
app.config["SECRET_KEY"] = Config.SECRET_KEY
CORS(app)


# ═══════════════════════════════════════════════════════════
#  Database initialisation
# ═══════════════════════════════════════════════════════════

def init_database():
    """Initialize connection pool and apply schema."""
    try:
        DatabaseConnection.initialize_pool()
        schema_path = os.path.join(os.path.dirname(__file__), "database", "schema.sql")
        DatabaseConnection.run_schema(schema_path)
        print("[App] Database initialised")
    except Exception as e:
        print(f"[App] Database init warning: {e}")
        print("[App] Continuing without database — set up MySQL and restart")


# ═══════════════════════════════════════════════════════════
#  Page routes
# ═══════════════════════════════════════════════════════════

@app.route("/")
def index():
    """Serve the main chat UI."""
    return render_template("index.html")


# ═══════════════════════════════════════════════════════════
#  Chat API
# ═══════════════════════════════════════════════════════════

@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Process a user message through the agentic workflow.

    Body JSON:
      {
        "message": "...",
        "conversation_id": "...",     (optional — creates new if missing)
        "llm_provider": "openai",     (optional)
        "llm_model": "gpt-4o",       (optional)
        "tool_mode": "auto"           (optional)
      }
    """
    data = request.get_json(force=True)
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "Message cannot be empty"}), 400

    conversation_id = data.get("conversation_id", "")
    llm_provider = data.get("llm_provider", Config.DEFAULT_LLM_PROVIDER)
    llm_model = data.get("llm_model", "")
    tool_mode = data.get("tool_mode", "auto")

    try:
        # Create conversation if needed
        if not conversation_id:
            conversation_id = db.create_conversation(
                title=user_message[:80],
                llm_provider=llm_provider,
                llm_model=llm_model or (Config.DEFAULT_OPENAI_MODEL if llm_provider == "openai" else Config.DEFAULT_GEMINI_MODEL),
                tool_mode=tool_mode,
            )
        else:
            # Update settings if changed
            db.update_conversation_settings(
                conversation_id,
                llm_provider=llm_provider,
                llm_model=llm_model,
                tool_mode=tool_mode,
            )

        # Load conversation context
        summary_data = db.get_summary(conversation_id)
        summary = summary_data["summary"] if summary_data else ""

        # Load recent messages as LangChain objects
        recent_msgs = db.get_recent_messages(conversation_id, count=10)
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

        history_messages = []
        for msg in recent_msgs:
            if msg["role"] == "user":
                history_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                history_messages.append(AIMessage(content=msg["content"]))
            elif msg["role"] == "system":
                history_messages.append(SystemMessage(content=msg["content"]))

        # Run the agentic workflow
        from agents.graph import run_agent

        result = run_agent(
            user_input=user_message,
            conversation_id=conversation_id,
            llm_provider=llm_provider,
            llm_model=llm_model,
            tool_mode=tool_mode,
            summary=summary,
            history_messages=history_messages,
        )

        return jsonify({
            "response": result["response"],
            "conversation_id": conversation_id,
            "tool_calls": result.get("tool_calls", []),
            "agent_type": result.get("agent_type", "chat"),
            "intent": result.get("intent", ""),
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "error": str(e),
            "response": "I encountered an error. Please try again.",
            "conversation_id": conversation_id,
        }), 500


# ═══════════════════════════════════════════════════════════
#  Conversations CRUD
# ═══════════════════════════════════════════════════════════

@app.route("/api/conversations", methods=["GET"])
def get_conversations():
    """List all conversations."""
    try:
        conversations = db.list_conversations()
        # Serialise datetimes
        for c in conversations:
            for key in ("created_at", "updated_at"):
                if c.get(key):
                    c[key] = c[key].isoformat()
        return jsonify(conversations)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/conversations", methods=["POST"])
def create_conversation():
    """Create a new conversation thread."""
    data = request.get_json(force=True) if request.is_json else {}
    try:
        conv_id = db.create_conversation(
            title=data.get("title", "New Chat"),
            llm_provider=data.get("llm_provider", Config.DEFAULT_LLM_PROVIDER),
            llm_model=data.get("llm_model", Config.DEFAULT_OPENAI_MODEL),
            tool_mode=data.get("tool_mode", "auto"),
        )
        return jsonify({"conversation_id": conv_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/conversations/<conversation_id>", methods=["GET"])
def get_conversation(conversation_id):
    """Get a conversation with its messages."""
    try:
        conv = db.get_conversation(conversation_id)
        if not conv:
            return jsonify({"error": "Conversation not found"}), 404

        messages = db.get_messages(conversation_id)
        summary = db.get_summary(conversation_id)

        # Serialise datetimes
        for key in ("created_at", "updated_at"):
            if conv.get(key):
                conv[key] = conv[key].isoformat()
        for m in messages:
            if m.get("created_at"):
                m["created_at"] = m["created_at"].isoformat()

        conv["messages"] = messages
        conv["summary"] = summary["summary"] if summary else None

        return jsonify(conv)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/conversations/<conversation_id>", methods=["DELETE"])
def delete_conversation(conversation_id):
    """Delete a conversation and all related data."""
    try:
        db.delete_conversation(conversation_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/conversations/<conversation_id>/title", methods=["PUT"])
def update_title(conversation_id):
    """Rename a conversation."""
    data = request.get_json(force=True)
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "Title cannot be empty"}), 400
    try:
        db.update_conversation_title(conversation_id, title)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/conversations/<conversation_id>/settings", methods=["PUT"])
def update_settings(conversation_id):
    """Update LLM provider, model, or tool mode for a conversation."""
    data = request.get_json(force=True)
    try:
        db.update_conversation_settings(conversation_id, **data)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════
#  Providers & Health
# ═══════════════════════════════════════════════════════════

@app.route("/api/providers", methods=["GET"])
def get_providers():
    """Return available LLM providers and models."""
    return jsonify(list_providers())


@app.route("/api/health", methods=["GET"])
def health():
    """Health check."""
    return jsonify({
        "status": "healthy",
        "version": "1.0.0",
    })


# ═══════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    init_database()
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=Config.FLASK_DEBUG,
    )
