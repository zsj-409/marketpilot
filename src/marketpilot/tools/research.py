"""Research tools that route through the existing tool protocol."""

from datetime import UTC, datetime
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, uuid4, uuid5

from marketpilot.domain.enums import EvidenceSourceType, ToolResultStatus
from marketpilot.research.canonicalization import canonicalize_url
from marketpilot.research.errors import (
    ReplayMissError,
    ResearchBudgetExceededError,
)
from marketpilot.research.models import (
    RetrievalRecord,
    RetrievalStatus,
    RetrievedPage,
    SearchResult,
    SourceRecord,
    SourceSnapshot,
    SourceType,
)
from marketpilot.research.providers.retrieval import PageRetriever
from marketpilot.research.providers.search import SearchProvider
from marketpilot.research.replay import ReplayStore
from marketpilot.tools.base import (
    ToolArguments,
    ToolContext,
    ToolMetadata,
    ToolOutput,
)
from marketpilot.tools.errors import ToolError


def _domain(url: str) -> str:
    return urlsplit(url).hostname or "unknown"


def _source_record(run_id: str, result_or_page: SearchResult | RetrievedPage) -> SourceRecord:
    canonical = canonicalize_url(
        result_or_page.canonical_url
        if isinstance(result_or_page, RetrievedPage)
        else result_or_page.url
    )
    url = (
        result_or_page.canonical_url
        if isinstance(result_or_page, RetrievedPage)
        else result_or_page.url
    )
    return SourceRecord(
        source_id=uuid5(NAMESPACE_URL, f"marketpilot:source:{run_id}:{canonical}"),
        source_type=SourceType.WEB_PAGE,
        url=url,
        canonical_url=canonical,
        domain=_domain(canonical),
        title=result_or_page.title,
        published_at=result_or_page.published_at,
        metadata={"provider": "research"},
    )


class WebSearchTool:
    """Provider-neutral web search tool."""

    def __init__(self, provider: SearchProvider, max_results: int = 5) -> None:
        self._provider = provider
        self._max_results = max_results
        self._metadata = ToolMetadata(
            name="web_search",
            description="Search the web and return normalized discovery results.",
            version="1.0.0",
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            risk_level="medium",
            timeout_seconds=15,
            retry_policy="exponential",
        )

    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata

    async def execute(self, arguments: ToolArguments, context: ToolContext) -> ToolOutput:
        query = arguments.query
        if query is None:
            raise ToolError(ToolResultStatus.INVALID_INPUT, "missing query")
        if context.budget is not None:
            try:
                context.budget.reserve_search_query()
            except ResearchBudgetExceededError as exc:
                raise ToolError(ToolResultStatus.BUDGET_EXHAUSTED, str(exc)) from exc

        request_key = ReplayStore.key(["web_search", query, str(self._max_results)])
        if context.research_mode == "replay":
            if context.replay_store is None:
                raise ToolError(ToolResultStatus.REPLAY_MISS, "replay store not configured")
            try:
                payload = context.replay_store.lookup(request_key)
            except ReplayMissError as exc:
                raise ToolError(ToolResultStatus.REPLAY_MISS, str(exc)) from exc
            return ToolOutput.model_validate(payload["output"])

        results = await self._provider.search(query, self._max_results)
        store = context.research_store
        if store is not None:
            dedup = context.deduplicator
            accepted: list[SearchResult] = []
            for result in results:
                source = _source_record(str(context.run_id), result)
                if dedup is not None:
                    check = dedup.check(source.canonical_url, source.title or "")
                    if check.duplicate or check.near_duplicate:
                        if context.budget is not None:
                            context.budget.record_duplicate(near=check.near_duplicate)
                        continue
                    dedup.record(str(source.source_id), source.canonical_url, source.title or "")
                if context.budget is not None:
                    try:
                        context.budget.reserve_source()
                    except ResearchBudgetExceededError as exc:
                        raise ToolError(ToolResultStatus.BUDGET_EXHAUSTED, str(exc)) from exc
                store.add_source(source)
                accepted.append(result)
            summary_results = accepted
        else:
            summary_results = results

        first = summary_results[0] if summary_results else None
        observation = (
            "\n".join(
                f"{item.rank}. {item.title}\n{item.url}\n{item.snippet}" for item in summary_results
            )
            or "no new unique sources (all results were duplicates)"
        )
        output = ToolOutput(
            summary=f"search returned {len(summary_results)} results",
            source_uri=first.url if first else f"search://{query}",
            observation=observation,
            confidence=0.75,
            evidence_source_type=EvidenceSourceType.SEARCH_RESULT,
        )
        if context.replay_store is not None and context.research_mode != "replay":
            context.replay_store.record(request_key, {"output": output.model_dump(mode="json")})
        return output


class FetchPageTool:
    """Provider-neutral page retrieval tool."""

    def __init__(self, retriever: PageRetriever) -> None:
        self._retriever = retriever
        self._metadata = ToolMetadata(
            name="fetch_page",
            description="Fetch and normalize one web page.",
            version="1.0.0",
            input_schema={
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
            risk_level="medium",
            timeout_seconds=15,
            retry_policy="exponential",
        )

    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata

    async def execute(self, arguments: ToolArguments, context: ToolContext) -> ToolOutput:
        url = arguments.url
        if url is None:
            raise ToolError(ToolResultStatus.INVALID_INPUT, "missing url")
        if context.budget is not None:
            try:
                context.budget.reserve_page_fetch()
            except ResearchBudgetExceededError as exc:
                raise ToolError(ToolResultStatus.BUDGET_EXHAUSTED, str(exc)) from exc

        request_key = ReplayStore.key(["fetch_page", url])
        if context.research_mode == "replay":
            if context.replay_store is None:
                raise ToolError(ToolResultStatus.REPLAY_MISS, "replay store not configured")
            try:
                payload = context.replay_store.lookup(request_key)
            except ReplayMissError as exc:
                raise ToolError(ToolResultStatus.REPLAY_MISS, str(exc)) from exc
            return ToolOutput.model_validate(payload["output"])

        started = datetime.now(UTC)
        page = await self._retriever.retrieve(url)
        store = context.research_store
        source = _source_record(str(context.run_id), page)
        snapshot_id = uuid5(NAMESPACE_URL, f"marketpilot:snapshot:{context.run_id!s}:{url}")
        retrieval_id = uuid4()
        retrieval = RetrievalRecord(
            retrieval_id=retrieval_id,
            source_id=source.source_id,
            run_id=context.run_id,
            task_id=context.task_id,
            requested_key=url,
            request_hash=request_key,
            status=RetrievalStatus.SUCCESS,
            started_at=started,
            completed_at=datetime.now(UTC),
            latency_ms=0,
            provider="research",
            content_hash=page.content_hash,
        )
        snapshot = SourceSnapshot(
            snapshot_id=snapshot_id,
            source_id=source.source_id,
            retrieval_id=retrieval_id,
            normalized_text=page.normalized_text,
            content_hash=page.content_hash,
            title=page.title,
            published_at=page.published_at,
        )
        if store is not None:
            store.add_source(source)
            store.add_retrieval(retrieval)
            store.add_snapshot(snapshot)
            if context.deduplicator is not None:
                check = context.deduplicator.check(source.canonical_url, page.normalized_text)
                if check.duplicate or check.near_duplicate:
                    if context.budget is not None:
                        context.budget.record_duplicate(near=check.near_duplicate)
                else:
                    context.deduplicator.record(
                        str(source.source_id), source.canonical_url, page.normalized_text
                    )

        output = ToolOutput(
            summary=page.title or page.url,
            source_uri=page.url,
            observation=page.normalized_text[:4000],
            confidence=0.85,
            source_id=source.source_id,
            snapshot_id=snapshot_id,
            evidence_source_type=EvidenceSourceType.WEB_PAGE,
        )
        if context.replay_store is not None and context.research_mode != "replay":
            context.replay_store.record(request_key, {"output": output.model_dump(mode="json")})
        return output
