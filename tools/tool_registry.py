"""
Central tool registry — returns a list of all available tools.
"""

from tools.search_tool import get_search_tool
from tools.stock_tool import get_stock_price
from tools.tavily_tool import get_tavily_tool
from tools.rag_tool import rag_qa_tool
from tools.vectorless_rag_tool import vectorless_rag_tool

def get_all_tools() -> list:
    """Return every tool the chat agent can use."""
    tools = [
        get_search_tool(),
        get_stock_price,          # Already a @tool-decorated function
        get_tavily_tool(),
        rag_qa_tool,
        vectorless_rag_tool,
    ]
    return tools


def get_tool_names() -> list[str]:
    """Return names of all registered tools (for UI display)."""
    return [t.name for t in get_all_tools()]
