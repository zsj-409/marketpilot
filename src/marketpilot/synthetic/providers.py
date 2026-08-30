"""Synthetic research providers backed by the generated dataset."""

import json
from datetime import UTC, datetime
from pathlib import Path

from marketpilot.research.canonicalization import canonicalize_url, content_hash
from marketpilot.research.models import RetrievedPage, SearchResult
from marketpilot.research.normalization import normalize_text
from marketpilot.research.providers.retrieval import PageRetriever
from marketpilot.research.providers.search import SearchProvider

FACET_KEYWORDS: dict[str, tuple[str, ...]] = {
    "broad": ("overview", "compare", "market"),
    "constraints": ("constraint", "eligible", "required", "compatible"),
    "performance": ("performance", "capability", "throughput"),
    "price": ("price", "cost", "margin"),
    "reliability": ("reliability", "maintenance", "durability"),
    "downside": ("failure", "downside", "defect", "risk"),
    "uncertainty": ("uncertain", "gap", "missing"),
    "distractor": ("lifestyle", "brand", "unrelated"),
}


class SyntheticSearchProvider(SearchProvider):
    """Search synthetic source documents without exposing latent ground truth."""

    def __init__(self, sources: list[dict[str, object]]) -> None:
        self._sources = sources

    async def search(self, query: str, limit: int) -> list[SearchResult]:
        query_terms = set(query.lower().split())
        scored: list[tuple[int, dict[str, object]]] = []
        for source in self._sources:
            text = str(source.get("text", ""))
            title = str(source.get("title", ""))
            score = sum(term in text.lower() or term in title.lower() for term in query_terms)
            scored.append((score, source))
        scored.sort(key=lambda item: item[0], reverse=True)
        results: list[SearchResult] = []
        for rank, (_, source) in enumerate(scored[:limit], start=1):
            results.append(
                SearchResult(
                    title=str(source.get("title", "Synthetic source")),
                    url=str(source.get("url", "")),
                    snippet=str(source.get("text", ""))[:800],
                    rank=rank,
                    metadata={"category": str(source.get("category", ""))},
                )
            )
        return results


class SyntheticSearchProviderV2(SearchProvider):
    """Facet-aware deterministic retrieval over a frozen evidence corpus.

    Retrieval depends only on the query and the corpus. It never receives a
    policy name, branch label, hidden utility, or expected winner.
    """

    def __init__(self, sources: list[dict[str, object]]) -> None:
        self._sources = sources

    async def search(self, query: str, limit: int) -> list[SearchResult]:
        query_terms = set(query.lower().split())
        scored: list[tuple[float, dict[str, object], list[str]]] = []
        for source in self._sources:
            text = str(source.get("text", "")).lower()
            title = str(source.get("title", "")).lower()
            evidence_facets = source.get("evidence_facets")
            facets = (
                [str(facet) for facet in evidence_facets]
                if isinstance(evidence_facets, list)
                else []
            )
            lexical = sum(term in text or term in title for term in query_terms)
            facet_score = sum(
                2.0
                for facet in facets
                for keyword in FACET_KEYWORDS.get(facet, ())
                if keyword in query
            )
            scored.append((lexical + facet_score, source, facets))
        scored.sort(key=lambda item: item[0], reverse=True)
        results: list[SearchResult] = []
        for rank, (_, source, facets) in enumerate(scored[:limit], start=1):
            results.append(
                SearchResult(
                    title=str(source.get("title", "Synthetic source")),
                    url=str(source.get("url", "")),
                    snippet=str(source.get("text", ""))[:1200],
                    rank=rank,
                    metadata={
                        "category": str(source.get("category", "")),
                        "evidence_facets": facets,
                    },
                )
            )
        return results


class SyntheticPageRetriever(PageRetriever):
    """Retrieve synthetic source documents keyed by URL."""

    def __init__(self, sources: list[dict[str, object]]) -> None:
        self._sources = {str(source.get("url", "")): source for source in sources}

    async def retrieve(self, url: str) -> RetrievedPage:
        canonical = canonicalize_url(url)
        source = self._sources.get(url) or self._sources.get(canonical)
        if source is None:
            source = {"title": "Synthetic page", "text": "No content found."}
        text = normalize_text(str(source.get("text", "")))
        return RetrievedPage(
            url=url,
            canonical_url=canonical,
            title=str(source.get("title", "Synthetic page")),
            normalized_text=text,
            published_at=None,
            retrieved_at=datetime.now(UTC),
            content_type="text/html",
            content_hash=content_hash(text),
            metadata={"provider": "synthetic"},
        )


def load_synthetic_providers(
    dataset_dir: Path,
) -> tuple[SyntheticSearchProvider, SyntheticPageRetriever]:
    sources = [
        dict(json.loads(line))
        for line in (dataset_dir / "sources.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return SyntheticSearchProvider(sources), SyntheticPageRetriever(sources)


def load_synthetic_providers_v2(
    dataset_dir: Path,
) -> tuple[SyntheticSearchProviderV2, SyntheticPageRetriever]:
    sources = [
        dict(json.loads(line))
        for line in (dataset_dir / "sources_v2.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return SyntheticSearchProviderV2(sources), SyntheticPageRetriever(sources)
