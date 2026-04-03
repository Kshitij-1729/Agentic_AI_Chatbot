"""
Blog Agent Subgraph — PLACEHOLDER.
Will be implemented later with blog/article generation capabilities.
"""

from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage
from agents.state import AgentState


def blog_placeholder_node(state: AgentState) -> dict:
    """
    Placeholder node for the Blog Agent subgraph.
    """
    response = AIMessage(
        content=(
            "🚧 **Blog Agent — Under Development**\n\n"
            "The Blog Agent is currently being built. "
            "It will support:\n"
            "- Blog post generation with SEO optimization\n"
            "- Article writing with custom tone and style\n"
            "- Content ideation and outline creation\n"
            "- Multi-format content (listicles, how-tos, opinion pieces)\n\n"
            "For now, please use the general chat for your content needs!"
        )
    )
    return {
        "messages": [response],
        "agent_response": response.content,
    }


def build_blog_subgraph():
    """Build and compile the Blog placeholder subgraph."""
    builder = StateGraph(AgentState)
    builder.add_node("blog_node", blog_placeholder_node)
    builder.set_entry_point("blog_node")
    builder.add_edge("blog_node", END)
    return builder.compile()


blog_subgraph = build_blog_subgraph()
