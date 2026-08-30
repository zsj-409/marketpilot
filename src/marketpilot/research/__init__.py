"""Provider-neutral research environment, provenance, and replay."""

from marketpilot.research.budget import BudgetTracker
from marketpilot.research.canonicalization import (
    canonicalize_url,
    content_hash,
    request_hash,
)
from marketpilot.research.dedup import DeduplicationResult, SourceDeduplicator
from marketpilot.research.errors import (
    ContentTooLargeError,
    InvalidSourceURLError,
    ReplayMissError,
    ResearchBudgetExceededError,
    ResearchError,
    RetrievalHTTPError,
    RetrievalTimeoutError,
    SearchProviderError,
    UnsupportedContentTypeError,
)
from marketpilot.research.models import (
    ResearchBudget,
    ResearchBudgetUsage,
    RetrievalRecord,
    RetrievalStatus,
    SourceClass,
    SourceQualitySignals,
    SourceRecord,
    SourceSnapshot,
    SourceType,
)
from marketpilot.research.quality import compute_source_quality_signals
from marketpilot.research.replay import ReplayStore
from marketpilot.research.store import ResearchStore

__all__ = [
    "BudgetTracker",
    "ContentTooLargeError",
    "DeduplicationResult",
    "InvalidSourceURLError",
    "ReplayMissError",
    "ReplayStore",
    "ResearchBudget",
    "ResearchBudgetExceededError",
    "ResearchBudgetUsage",
    "ResearchError",
    "ResearchStore",
    "RetrievalHTTPError",
    "RetrievalRecord",
    "RetrievalStatus",
    "RetrievalTimeoutError",
    "SearchProviderError",
    "SourceClass",
    "SourceDeduplicator",
    "SourceQualitySignals",
    "SourceRecord",
    "SourceSnapshot",
    "SourceType",
    "UnsupportedContentTypeError",
    "canonicalize_url",
    "compute_source_quality_signals",
    "content_hash",
    "request_hash",
]
