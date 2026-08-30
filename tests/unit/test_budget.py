"""Research budget tests."""

import pytest

from marketpilot.research.budget import BudgetTracker
from marketpilot.research.errors import ResearchBudgetExceededError
from marketpilot.research.models import ResearchBudget


def test_search_budget_exhaustion() -> None:
    tracker = BudgetTracker(ResearchBudget(max_search_queries=1))
    tracker.reserve_search_query()
    with pytest.raises(ResearchBudgetExceededError):
        tracker.reserve_search_query()


def test_unlimited_budget_does_not_exhaust() -> None:
    tracker = BudgetTracker(ResearchBudget())
    tracker.reserve_search_query()
    tracker.reserve_page_fetch()
    assert tracker.usage.search_queries_used == 1
    assert tracker.usage.pages_fetched == 1
