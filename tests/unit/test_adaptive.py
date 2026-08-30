"""Adaptive planner tests."""

from uuid import uuid4

from marketpilot.domain.goals import ResearchGoal
from marketpilot.domain.state import ResearchState
from marketpilot.orchestration.adaptive import AdaptiveResearchPlanner


def test_adaptive_planner_returns_bounded_followups() -> None:
    goal = ResearchGoal(market="US", category="pet supplies", objective="Find products")
    state = ResearchState(run_id=uuid4(), goal=goal, budget=goal.budget)
    planner = AdaptiveResearchPlanner(max_followup_tasks=3)
    followups = planner.plan_followups(state)
    assert len(followups) <= 3
    assert all(task.run_id == state.run_id for task in followups)
