"""Research budget tracking."""

import time

from marketpilot.research.errors import ResearchBudgetExceededError
from marketpilot.research.models import ResearchBudget, ResearchBudgetUsage


class BudgetTracker:
    """Centralized research budget accounting."""

    def __init__(self, budget: ResearchBudget | None = None) -> None:
        self.budget = budget or ResearchBudget()
        self.usage = ResearchBudgetUsage()
        self._started = time.monotonic()

    def _check(self, current: int, limit: int | None, label: str) -> None:
        if limit is not None and current >= limit:
            raise ResearchBudgetExceededError(f"research budget exhausted: {label}")

    def reserve_search_query(self) -> None:
        self._check(
            self.usage.search_queries_used, self.budget.max_search_queries, "search queries"
        )
        self.usage = self.usage.model_copy(
            update={"search_queries_used": self.usage.search_queries_used + 1}
        )

    def reserve_page_fetch(self) -> None:
        self._check(self.usage.pages_fetched, self.budget.max_page_fetches, "page fetches")
        self.usage = self.usage.model_copy(update={"pages_fetched": self.usage.pages_fetched + 1})

    def reserve_source(self) -> None:
        self._check(self.usage.sources_accepted, self.budget.max_sources, "sources")
        self.usage = self.usage.model_copy(
            update={"sources_accepted": self.usage.sources_accepted + 1}
        )

    def record_tool_call(self, latency_ms: int) -> None:
        self._check(
            self.usage.tool_latency_ms,
            self.budget.max_total_tool_latency_ms,
            "tool latency",
        )
        self.usage = self.usage.model_copy(
            update={"tool_latency_ms": self.usage.tool_latency_ms + latency_ms}
        )
        duration = time.monotonic() - self._started
        if (
            self.budget.max_research_duration_seconds is not None
            and duration >= self.budget.max_research_duration_seconds
        ):
            raise ResearchBudgetExceededError("research budget exhausted: duration")

    def record_duplicate(self, near: bool = False) -> None:
        if near:
            self.usage = self.usage.model_copy(
                update={"near_duplicates_detected": self.usage.near_duplicates_detected + 1}
            )
        else:
            self.usage = self.usage.model_copy(
                update={"duplicates_removed": self.usage.duplicates_removed + 1}
            )

    def record_rejected_source(self) -> None:
        self.usage = self.usage.model_copy(
            update={"sources_rejected": self.usage.sources_rejected + 1}
        )
