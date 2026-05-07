"""
web_search.py — DuckDuckGo + Brave Search Tool for Friday v3
AI-VIBE-CLI-PYTHON | Kazi Musharraf
"""
import httpx
import json
from typing import Optional
from pydantic import BaseModel
from rich.console import Console
from rich.table import Table

console = Console()


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    source: str


class WebSearchTool:
    """Search the web and return structured results."""

    name = "web_search"
    description = "Search the web for current information, documentation, or news"

    def __init__(self, brave_api_key: Optional[str] = None):
        self.brave_api_key = brave_api_key

    async def execute(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """
        Execute a web search and return structured results.
        Falls back to DuckDuckGo if no Brave API key provided.
        """
        if self.brave_api_key:
            return await self._brave_search(query, max_results)
        return await self._ddg_search(query, max_results)

    async def _brave_search(self, query: str, max_results: int) -> list[SearchResult]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"Accept": "application/json", "X-Subscription-Token": self.brave_api_key},
                params={"q": query, "count": max_results, "text_decorations": False},
                timeout=10.0
            )
            data = response.json()
            results = []
            for item in data.get("web", {}).get("results", [])[:max_results]:
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("description", ""),
                    source="brave"
                ))
            return results

    async def _ddg_search(self, query: str, max_results: int) -> list[SearchResult]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.duckduckgo.com/",
                data={"q": query, "format": "json", "no_redirect": "1"},
                timeout=10.0
            )
            data = response.json()
            results = []
            for item in data.get("RelatedTopics", [])[:max_results]:
                if "Text" in item:
                    results.append(SearchResult(
                        title=item.get("Text", "")[:60],
                        url=item.get("FirstURL", ""),
                        snippet=item.get("Text", ""),
                        source="duckduckgo"
                    ))
            return results

    def render_results(self, results: list[SearchResult]) -> None:
        """Render search results as a rich table."""
        table = Table(title="Web Search Results", show_header=True, header_style="bold cyan")
        table.add_column("Title", style="bold white", max_width=40)
        table.add_column("Snippet", max_width=60)
        table.add_column("URL", style="dim blue", max_width=40)

        for r in results:
            table.add_row(r.title, r.snippet[:100] + "...", r.url)

        console.print(table)
