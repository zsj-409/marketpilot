"""Research domain model tests."""

from uuid import uuid4

from marketpilot.research.models import (
    ResearchBudget,
    RetrievalStatus,
    SourceRecord,
    SourceSnapshot,
    SourceType,
)


def test_source_and_snapshot_are_distinct() -> None:
    source_id = uuid4()
    source = SourceRecord(
        source_id=source_id,
        source_type=SourceType.WEB_PAGE,
        url="https://example.com/a",
        canonical_url="https://example.com/a",
        domain="example.com",
    )
    snapshot = SourceSnapshot(
        snapshot_id=uuid4(),
        source_id=source_id,
        retrieval_id=uuid4(),
        normalized_text="normalized",
        content_hash="abcdef1234567890",
    )
    assert snapshot.source_id == source.source_id
    assert snapshot.snapshot_id != source.source_id


def test_disabled_budget_limits_are_explicit() -> None:
    budget = ResearchBudget()
    assert budget.max_search_queries is None
    assert budget.max_page_fetches is None


def test_retrieval_status_is_typed() -> None:
    assert RetrievalStatus.SUCCESS.value == "SUCCESS"
    assert RetrievalStatus.REPLAY_MISS.value == "REPLAY_MISS"
