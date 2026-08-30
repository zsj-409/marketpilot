"""Shared deterministic test fixtures."""

from collections.abc import Iterator
from uuid import UUID, uuid4

import pytest

from marketpilot.domain.enums import (
    AgentRole,
    Decision,
    EvidenceSourceType,
    TaskStatus,
    TaskType,
)
from marketpilot.domain.evidence import EvidenceItem
from marketpilot.domain.findings import Finding
from marketpilot.domain.goals import ResearchGoal
from marketpilot.domain.recommendations import (
    ProductCandidate,
    ProductScore,
    Recommendation,
    RiskFlag,
)
from marketpilot.domain.state import ResearchState
from marketpilot.domain.tasks import TaskNode


@pytest.fixture
def goal() -> ResearchGoal:
    return ResearchGoal(
        market="us",
        category="Pet Supplies",
        objective="Find promising products",
    )


@pytest.fixture
def run_id() -> Iterator[str]:
    yield str(uuid4())


def make_task(
    run_id: str,
    task_id: UUID | None = None,
    task_type: TaskType = TaskType.MARKET_RESEARCH,
    dependencies: set[str] | None = None,
    status: TaskStatus = TaskStatus.PENDING,
) -> TaskNode:
    return TaskNode(
        task_id=task_id or uuid4(),
        run_id=run_id,
        task_type=task_type,
        assigned_role=AgentRole.MARKET_RESEARCH,
        description="Test task",
        dependencies=frozenset(dependencies or set()),
        status=status,
    )


def make_evidence(run_id: str, task_id: str) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=uuid4(),
        run_id=run_id,
        task_id=task_id,
        source_type=EvidenceSourceType.MOCK,
        source_uri="mock://test",
        content_hash="1234567890abcdef",
        excerpt="Deterministic observation",
        confidence=0.8,
    )


def make_state(goal: ResearchGoal, run_id: str) -> tuple[ResearchState, TaskNode, EvidenceItem]:
    task = make_task(run_id)
    state = ResearchState(run_id=run_id, goal=goal, budget=goal.budget)
    state.add_task(task)
    evidence = make_evidence(run_id, task.task_id)
    state.add_evidence(evidence)
    return state, task, evidence


def add_valid_recommendation(state: ResearchState, task: TaskNode, evidence: EvidenceItem) -> None:
    finding = Finding(
        finding_id=uuid4(),
        run_id=state.run_id,
        task_id=task.task_id,
        claim="Valid finding",
        confidence=0.8,
        evidence_ids=frozenset({evidence.evidence_id}),
    )
    state.add_finding(finding)
    candidate = ProductCandidate(
        candidate_id=uuid4(),
        run_id=state.run_id,
        name="Automatic pet feeder",
        category=state.goal.category,
        market=state.goal.market,
        provider="mock",
        provider_product_id="mock-1",
    )
    state.add_candidate(candidate)
    risk = RiskFlag(
        risk_id=uuid4(),
        run_id=state.run_id,
        label="Competition",
        severity=0.4,
        rationale="Medium-high competition",
        evidence_ids=frozenset({evidence.evidence_id}),
    )
    state.add_risk_flag(risk)
    recommendation = Recommendation(
        recommendation_id=uuid4(),
        run_id=state.run_id,
        candidate=candidate,
        scores=ProductScore(
            demand=0.8,
            trend=0.7,
            estimated_margin=0.6,
            competition=0.6,
            customer_pain_opportunity=0.7,
            operational_complexity=0.5,
            regulatory_risk=0.2,
            overall_score=0.7,
        ),
        findings=frozenset({finding.finding_id}),
        supporting_evidence=frozenset({evidence.evidence_id}),
        risk_flags=frozenset({risk.risk_id}),
        decision=Decision.WATCH,
        confidence=0.75,
        rationale="Valid test recommendation",
    )
    state.add_recommendation(recommendation)
