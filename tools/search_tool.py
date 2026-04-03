"""
DuckDuckGo web search tool.
"""

from langchain_community.tools import DuckDuckGoSearchRun


def get_search_tool():
    """Return a DuckDuckGo search tool instance."""
    return DuckDuckGoSearchRun(
        name="web_search",
        description=(
            "Search the web using DuckDuckGo. "
            "Useful for finding current information, news, facts, or any real-time data. "
            "Input should be a search query string."
        ),
    )
