"""Persistence metadata tests."""

from marketpilot.persistence.models import Base


def test_logical_tables_exist() -> None:
    expected = {
        "research_runs",
        "research_tasks",
        "agent_events",
        "tool_calls",
        "sources",
        "evidence_items",
        "findings",
        "product_candidates",
        "product_scores",
        "risk_flags",
        "recommendations",
        "memories",
        "evaluations",
    }
    assert expected.issubset(set(Base.metadata.tables))
