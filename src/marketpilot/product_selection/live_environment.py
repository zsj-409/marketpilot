"""Live research environment wiring for closed-loop product selection."""

from typing import Any
from uuid import UUID

from marketpilot.config import MarketPilotSettings
from marketpilot.llm.errors import LLMAuthenticationError
from marketpilot.product_selection.workers import ResearchEnvironment
from marketpilot.research.providers.retrieval import HTTPPageRetriever
from marketpilot.research.providers.search import TavilySearchProvider


class LiveResearchEnvironment(ResearchEnvironment):
    """Closed-loop environment backed by real search and page retrieval."""

    def __init__(
        self,
        search: TavilySearchProvider,
        retrieval: HTTPPageRetriever,
    ) -> None:
        self._search = search
        self._retrieval = retrieval
        self._candidates: list[dict[str, Any]] = []
        self._evidence: dict[UUID, dict[str, list[str]]] = {}

    def candidates(self) -> list[dict[str, Any]]:
        return self._candidates

    def evidence(self, candidate_id: UUID) -> dict[str, list[str]]:
        return self._evidence.get(candidate_id, {})

    def add_evidence(self, candidate_id: UUID, facet: str, observation: str) -> None:
        self._evidence.setdefault(candidate_id, {}).setdefault(facet, []).append(observation)

    async def seed(self, query: str, limit: int) -> None:
        results = await self._search.search(query, limit)
        for index, result in enumerate(results):
            candidate_id = _stable_candidate_id(query, index)
            self._candidates.append(
                {
                    "candidate_id": str(candidate_id),
                    "title": result.title,
                    "price": None,
                    "battery": None,
                }
            )
            page = await self._retrieval.retrieve(result.url)
            self.add_evidence(candidate_id, "demand", page.normalized_text[:500])


def build_live_research_environment(
    settings: MarketPilotSettings,
) -> LiveResearchEnvironment:
    key = settings.search_api_key.get_secret_value() if settings.search_api_key else None
    if key is None:
        raise LLMAuthenticationError("search API key is not configured")
    search = TavilySearchProvider(
        api_key=key,
        timeout_seconds=settings.retrieval_timeout_seconds,
    )
    retrieval = HTTPPageRetriever(
        timeout_seconds=settings.retrieval_timeout_seconds,
        max_bytes=settings.max_page_bytes,
    )
    return LiveResearchEnvironment(search, retrieval)


def _stable_candidate_id(query: str, index: int) -> UUID:
    from uuid import NAMESPACE_URL, uuid5

    return uuid5(NAMESPACE_URL, f"marketpilot:live-candidate:{query}:{index}")
