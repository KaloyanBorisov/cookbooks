"""This module provides example tools for web scraping and search functionality.

It includes a basic Tavily search function (as an example)

These tools are intended as free examples to get started. For production use,
consider implementing more robust and specialized tools tailored to your needs.
"""

from typing import Any, Callable, List

from langchain_tavily import TavilySearch

search = TavilySearch(max_results=5)

TOOLS: List[Callable[..., Any]] = [search]
