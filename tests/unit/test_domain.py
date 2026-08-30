"""Domain contract tests."""

from uuid import uuid4

import pydantic
import pytest

from marketpilot.domain.enums import Decision, TaskStatus
from marketpilot.domain.findings import Finding
from marketpilot.domain.goals import ResearchGoal
from marketpilot.domain.recommendations import ProductScore
from marketpilot.domain.tasks import TaskNode
from tests.conftest import add_valid_recommendation, make_evidence, make_task


def test_goal_is_normalized(goal: ResearchGoal) -> None:
    assert goal.market == "US"
    assert goal.category == "pet supplies"


def test_invalid_goal_constraint_is_rejected() -> None:
    with pytest.raises(pydantic.ValidationError):
        ResearchGoal(
            market="US",
            category="pet supplies",
            objective="Find products",
            constraints={"minimum_margin": 1.5},  # type: ignore[arg-type]
        )


def test_invalid_finding_confidence_is_rejected() -> None:
    with pytest.raises(pydantic.ValidationError):
        Finding(
            finding_id=uuid4(),
            run_id=uuid4(),
            task_id=uuid4(),
            claim="Invalid confidence",
            confidence=1.2,
            evidence_ids=frozenset({uuid4()}),
        )


def test_invalid_product_score_is_rejected() -> None:
    with pytest.raises(pydantic.ValidationError):
        ProductScore(
            demand=1.1,
            trend=0.5,
            estimated_margin=0.5,
            competition=0.5,
            customer_pain_opportunity=0.5,
            operational_complexity=0.5,
            regulatory_risk=0.5,
            overall_score=0.5,
        )


def test_state_rejects_missing_evidence(goal: ResearchGoal, run_id: str) -> None:
    from marketpilot.domain.state import ResearchState

    task = make_task(run_id)
    state = ResearchState(run_id=run_id, goal=goal, budget=goal.budget)
    state.add_task(task)
    finding = Finding(
        finding_id=uuid4(),
        run_id=run_id,
        task_id=task.task_id,
        claim="Unsupported",
        confidence=0.7,
        evidence_ids=frozenset({uuid4()}),
    )
    with pytest.raises(ValueError, match="missing evidence"):
        state.add_finding(finding)


def test_state_rejects_invalid_recommendation_references(goal: ResearchGoal, run_id: str) -> None:
    from marketpilot.domain.state import ResearchState

    task = make_task(run_id)
    state = ResearchState(run_id=run_id, goal=goal, budget=goal.budget)
    state.add_task(task)
    evidence = make_evidence(run_id, task.task_id)
    state.add_evidence(evidence)
    add_valid_recommendation(state, task, evidence)
    recommendation = state.recommendations[next(iter(state.recommendations))]
    invalid = recommendation.model_copy(
        update={
            "recommendation_id": uuid4(),
            "supporting_evidence": frozenset({uuid4()}),
            "decision": Decision.NO_GO,
        }
    )
    with pytest.raises(ValueError, match="missing objects"):
        state.add_recommendation(invalid)


def test_task_rejects_self_dependency(run_id: str) -> None:
    task_id = uuid4()
    with pytest.raises(pydantic.ValidationError):
        TaskNode(
            task_id=task_id,
            run_id=run_id,
            task_type=make_task(run_id).task_type,
            assigned_role=make_task(run_id).assigned_role,
            description="Invalid",
            dependencies=frozenset({task_id}),
            status=TaskStatus.PENDING,
        )
