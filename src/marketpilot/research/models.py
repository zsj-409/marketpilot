"""Typed source, retrieval, snapshot, budget, and quality models."""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SourceType(StrEnum):
    """Logical category of a research source."""

    WEB_PAGE = "WEB_PAGE"
    SEARCH_RESULT = "SEARCH_RESULT"
    PRODUCT_CATALOG = "PRODUCT_CATALOG"
    REVIEW_FEED = "REVIEW_FEED"
    MARKET_SIGNAL = "MARKET_SIGNAL"
    COMMUNITY = "COMMUNITY"
    UNKNOWN = "UNKNOWN"


class SourceClass(StrEnum):
    """Transparent source-authority classification."""

    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    COMMUNITY = "COMMUNITY"
    MARKETPLACE = "MARKETPLACE"
    UNKNOWN = "UNKNOWN"


class RetrievalStatus(StrEnum):
    """Structured outcome of one retrieval attempt."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    HTTP_ERROR = "HTTP_ERROR"
    UNSUPPORTED_CONTENT = "UNSUPPORTED_CONTENT"
    TOO_LARGE = "TOO_LARGE"
    INVALID_URL = "INVALID_URL"
    REPLAY_MISS = "REPLAY_MISS"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"


class SourceRecord(BaseModel):
    """A logical, provider-neutral source identity."""

    model_config = ConfigDict(frozen=True)

    source_id: UUID
    source_type: SourceType
    url: str = Field(min_length=3, max_length=2048)
    canonical_url: str = Field(min_length=3, max_length=2048)
    domain: str = Field(min_length=1, max_length=300)
    title: str | None = Field(default=None, max_length=1000)
    author: str | None = Field(default=None, max_length=500)
    published_at: datetime | None = None
    first_seen_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, object] = Field(default_factory=dict)


class RetrievalRecord(BaseModel):
    """One attempt to retrieve a source."""

    model_config = ConfigDict(frozen=True)

    retrieval_id: UUID
    source_id: UUID
    run_id: UUID
    task_id: UUID
    tool_call_id: UUID | None = None
    requested_key: str = Field(min_length=1, max_length=2048)
    request_hash: str = Field(min_length=8, max_length=128)
    status: RetrievalStatus
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    latency_ms: int = Field(default=0, ge=0)
    provider: str = Field(min_length=1, max_length=100)
    content_hash: str | None = Field(default=None, max_length=128)
    error_category: str | None = Field(default=None, max_length=100)


class SourceSnapshot(BaseModel):
    """Immutable normalized content observed at one point in time."""

    model_config = ConfigDict(frozen=True)

    snapshot_id: UUID
    source_id: UUID
    retrieval_id: UUID
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    normalized_text: str = Field(min_length=1, max_length=200000)
    content_hash: str = Field(min_length=8, max_length=128)
    title: str | None = Field(default=None, max_length=1000)
    published_at: datetime | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class SourceQualitySignals(BaseModel):
    """Deterministic, inspectable source-quality signals."""

    model_config = ConfigDict(frozen=True)

    source_type: SourceType
    source_class: SourceClass
    domain: str
    published_date_available: bool
    author_available: bool
    freshness_days: int | None = Field(default=None, ge=0)
    retrieval_complete: bool
    duplicate: bool
    near_duplicate: bool
    content_length: int = Field(ge=0)
    https: bool
    structured_metadata_available: bool


class SearchResult(BaseModel):
    """Normalized discovery metadata for one search hit."""

    model_config = ConfigDict(frozen=True)

    title: str = Field(min_length=1, max_length=1000)
    url: str = Field(min_length=3, max_length=2048)
    snippet: str = Field(min_length=0, max_length=2000)
    rank: int = Field(ge=1)
    published_at: datetime | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class RetrievedPage(BaseModel):
    """Normalized document returned by page retrieval."""

    model_config = ConfigDict(frozen=True)

    url: str = Field(min_length=3, max_length=2048)
    canonical_url: str = Field(min_length=3, max_length=2048)
    title: str | None = Field(default=None, max_length=1000)
    normalized_text: str = Field(min_length=1, max_length=200000)
    published_at: datetime | None = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    content_type: str = Field(min_length=1, max_length=200)
    content_hash: str = Field(min_length=8, max_length=128)
    metadata: dict[str, object] = Field(default_factory=dict)


class ResearchBudget(BaseModel):
    """Optional run-level research limits."""

    model_config = ConfigDict(frozen=True)

    max_search_queries: int | None = Field(default=None, gt=0)
    max_page_fetches: int | None = Field(default=None, gt=0)
    max_sources: int | None = Field(default=None, gt=0)
    max_tool_calls: int | None = Field(default=None, gt=0)
    max_total_tool_latency_ms: int | None = Field(default=None, gt=0)
    max_llm_tokens: int | None = Field(default=None, gt=0)
    max_estimated_cost: float | None = Field(default=None, gt=0)
    max_research_duration_seconds: int | None = Field(default=None, gt=0)


class ResearchBudgetUsage(BaseModel):
    """Accumulated research budget usage."""

    model_config = ConfigDict(frozen=True)

    search_queries_used: int = Field(default=0, ge=0)
    pages_fetched: int = Field(default=0, ge=0)
    sources_accepted: int = Field(default=0, ge=0)
    sources_rejected: int = Field(default=0, ge=0)
    duplicates_removed: int = Field(default=0, ge=0)
    near_duplicates_detected: int = Field(default=0, ge=0)
    tool_latency_ms: int = Field(default=0, ge=0)
    llm_tokens: int = Field(default=0, ge=0)
    estimated_cost: float = Field(default=0.0, ge=0)
