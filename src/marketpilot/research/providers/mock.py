"""Deterministic mock research providers."""

from datetime import UTC, datetime

from marketpilot.research.canonicalization import canonicalize_url, content_hash
from marketpilot.research.models import RetrievedPage, SearchResult
from marketpilot.research.normalization import normalize_text
from marketpilot.research.providers.retrieval import PageRetriever
from marketpilot.research.providers.search import SearchProvider


class MockSearchProvider(SearchProvider):
    """Return deterministic search results for offline tests and demos."""

    def __init__(self, results: list[SearchResult] | None = None) -> None:
        self._results = results or []

    async def search(self, query: str, limit: int) -> list[SearchResult]:
        return self._results[:limit]


class MockPageRetriever(PageRetriever):
    """Return deterministic normalized pages keyed by canonical URL."""

    def __init__(self, pages: dict[str, RetrievedPage] | None = None) -> None:
        self._pages = pages or {}

    async def retrieve(self, url: str) -> RetrievedPage:
        canonical = canonicalize_url(url)
        page = self._pages.get(canonical)
        if page is None:
            return RetrievedPage(
                url=url,
                canonical_url=canonical,
                title="Mock page",
                normalized_text=normalize_text(
                    "Deterministic mock page content for offline research."
                ),
                published_at=datetime(2026, 1, 1, tzinfo=UTC),
                retrieved_at=datetime.now(UTC),
                content_type="text/html",
                content_hash=content_hash(
                    normalize_text("Deterministic mock page content for offline research.")
                ),
                metadata={"provider": "mock"},
            )
        return page.model_copy(update={"url": url})


def build_mock_research_providers() -> tuple[MockSearchProvider, MockPageRetriever]:
    """Build a small deterministic research fixture."""

    urls = [
        "https://example.com/pet-feeders",
        "https://example.com/syndicated-pet-feeders",
        "https://example.com/reviews/pet-feeders",
    ]
    results = [
        SearchResult(
            title="Automatic pet feeder demand trends",
            url=urls[0],
            snippet="Search demand for automatic pet feeders is rising.",
            rank=1,
            published_at=datetime(2026, 1, 10, tzinfo=UTC),
        ),
        SearchResult(
            title="Syndicated pet feeder demand",
            url=urls[1],
            snippet="Search demand for automatic pet feeders is rising.",
            rank=2,
        ),
        SearchResult(
            title="Pet feeder customer reviews",
            url=urls[2],
            snippet="Recurring complaints about battery reliability.",
            rank=3,
        ),
    ]
    pages = {
        canonicalize_url(urls[0]): RetrievedPage(
            url=urls[0],
            canonical_url=canonicalize_url(urls[0]),
            title="Automatic pet feeder demand trends",
            normalized_text=normalize_text(
                "Automatic pet feeder search demand is moderately rising. "
                "Battery reliability is a recurring customer complaint."
            ),
            published_at=datetime(2026, 1, 10, tzinfo=UTC),
            retrieved_at=datetime.now(UTC),
            content_type="text/html",
            content_hash=content_hash(
                normalize_text(
                    "Automatic pet feeder search demand is moderately rising. "
                    "Battery reliability is a recurring customer complaint."
                )
            ),
        ),
        canonicalize_url(urls[1]): RetrievedPage(
            url=urls[1],
            canonical_url=canonicalize_url(urls[1]),
            title="Syndicated pet feeder demand",
            normalized_text=normalize_text(
                "Automatic pet feeder search demand is moderately rising. "
                "Battery reliability is a recurring customer complaint."
            ),
            published_at=None,
            retrieved_at=datetime.now(UTC),
            content_type="text/html",
            content_hash=content_hash(
                normalize_text(
                    "Automatic pet feeder search demand is moderately rising. "
                    "Battery reliability is a recurring customer complaint."
                )
            ),
        ),
        canonicalize_url(urls[2]): RetrievedPage(
            url=urls[2],
            canonical_url=canonicalize_url(urls[2]),
            title="Pet feeder customer reviews",
            normalized_text=normalize_text(
                "Customers report that battery reliability and app connectivity are pain points."
            ),
            published_at=datetime(2025, 11, 1, tzinfo=UTC),
            retrieved_at=datetime.now(UTC),
            content_type="text/html",
            content_hash=content_hash(
                normalize_text(
                    "Customers report that battery reliability and app "
                    "connectivity are pain points."
                )
            ),
        ),
    }
    return MockSearchProvider(results), MockPageRetriever(pages)
