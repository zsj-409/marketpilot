"""Web search provider adapters."""

from abc import ABC, abstractmethod

import httpx

from marketpilot.research.errors import SearchProviderError
from marketpilot.research.models import SearchResult


class SearchProvider(ABC):
    """Provider-neutral web search interface."""

    @abstractmethod
    async def search(self, query: str, limit: int) -> list[SearchResult]:
        """Return normalized search results for a query."""


class TavilySearchProvider(SearchProvider):
    """Tavily search API adapter."""

    def __init__(
        self,
        api_key: str,
        timeout_seconds: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._timeout = timeout_seconds
        self._transport = transport

    async def search(self, query: str, limit: int) -> list[SearchResult]:
        payload = {
            "api_key": self._api_key,
            "query": query,
            "max_results": limit,
            "include_raw_content": False,
        }
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise SearchProviderError(f"Tavily search failed: {exc}") from exc

        results: list[SearchResult] = []
        for index, item in enumerate(data.get("results", []), start=1):
            results.append(
                SearchResult(
                    title=str(item.get("title", "")),
                    url=str(item.get("url", "")),
                    snippet=str(item.get("content", "")),
                    rank=index,
                    metadata={"provider": "tavily"},
                )
            )
        return results
