"""
Orchestrator Node — the entry brain of the workflow.
Understands the user query, classifies intent, and decides
which agent branch should handle it.
"""

from agents.state import AgentState
from llm.provider import get_llm

ORCHESTRATOR_SYSTEM_PROMPT = """You are an intelligent orchestrator for a multi-agent chatbot system.

Your job is to analyze the user's query and determine which specialized agent should handle it.

Available agents:
1. **chat** — General conversation, Q&A, reasoning, calculations, coding help, tool usage (search, stock prices). This is the DEFAULT for most queries.
2. **crag** — Corrective Retrieval-Augmented Generation. For queries that need document retrieval and fact-checking against knowledge bases. (Currently under development)
3. **blog** — Blog content generation, article writing, content creation tasks. (Currently under development)
4. **travel** — Travel planning, itineraries, destination info, flight/hotel recommendations. (Currently under development)
5. **academic** — Academic research, paper summaries, study help, citation assistance. (Currently under development)

IMPORTANT RULES:
- Since agents 2-5 (crag, blog, travel, academic) are still under development, route ALL queries to "chat" for now.
- In the future, you will route to specialized agents when they are ready.
- Respond with ONLY the agent name (one word): chat, crag, blog, travel, or academic

User query: {user_input}
"""


def orchestrator_node(state: AgentState) -> dict:
    """
    Analyze user intent and decide the target agent.
    Currently routes everything to 'chat' since other agents are placeholders.
    """
    user_input = state.get("user_input", "")
    provider = state.get("llm_provider", "openai")
    model = state.get("llm_model", None)

    try:
        llm = get_llm(provider=provider, model=model, temperature=0.0)
        prompt = ORCHESTRATOR_SYSTEM_PROMPT.format(user_input=user_input)

        from langchain_core.messages import SystemMessage, HumanMessage
        response = llm.invoke([
            SystemMessage(content=prompt),
            HumanMessage(content=user_input),
        ])

        agent_type = response.content.strip().lower()

        # Validate agent type
        valid_agents = {"chat", "crag", "blog", "travel", "academic"}
        if agent_type not in valid_agents:
            agent_type = "chat"

    except Exception as e:
        print(f"[Orchestrator] Error: {e}")
        agent_type = "chat"

    return {
        "intent": agent_type,
        "agent_type": agent_type,
    }
