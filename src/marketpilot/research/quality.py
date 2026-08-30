"""Deterministic source-quality signals."""

from datetime import UTC, datetime
from urllib.parse import urlsplit

from marketpilot.research.models import (
    SourceClass,
    SourceQualitySignals,
    SourceRecord,
    SourceSnapshot,
)


def compute_source_quality_signals(
    source: SourceRecord,
    snapshot: SourceSnapshot | None,
    duplicate: bool,
    near_duplicate: bool,
) -> SourceQualitySignals:
    """Compute explainable quality signals from a source and its snapshot."""

    parsed = urlsplit(source.canonical_url)
    freshness_days: int | None = None
    if source.published_at is not None:
        freshness_days = max((datetime.now(UTC) - source.published_at).days, 0)
    return SourceQualitySignals(
        source_type=source.source_type,
        source_class=SourceClass.UNKNOWN,
        domain=source.domain,
        published_date_available=source.published_at is not None,
        author_available=source.author is not None,
        freshness_days=freshness_days,
        retrieval_complete=snapshot is not None,
        duplicate=duplicate,
        near_duplicate=near_duplicate,
        content_length=len(snapshot.normalized_text) if snapshot is not None else 0,
        https=parsed.scheme == "https",
        structured_metadata_available=bool(source.metadata),
    )
