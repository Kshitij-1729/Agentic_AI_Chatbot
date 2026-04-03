"""
Tavily search tool for comprehensive web research.
"""

from langchain_community.tools.tavily_search import TavilySearchResults
from config import Config


def get_tavily_tool():
    """Return a Tavily search tool instance."""
    return TavilySearchResults(
        name="tavily_search",
        description=(
            "Search the web using Tavily API for comprehensive, accurate results. "
            "Useful for in-depth research, getting multiple sources, and finding detailed information. "
            "Input should be a search query string."
        ),
        max_results=5,
        api_key=Config.TAVILY_API_KEY,
    )
