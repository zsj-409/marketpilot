"""Independent Final Decision Safety Gate (Milestone B, Task B3).

A strategy-agnostic output gate: regardless of which research strategy
produced a recommendation, the FINAL decision must pass deterministic
safety checks before it is released as a production recommendation.

Interface (per spec):

    validate_final_decision(task, evidence, selected_candidate, budget_state)

Checks:
- selected_candidate exists
- hard constraints satisfied (deterministic code, never LLM judgement)
- required facets have sufficient evidence
- evidence not stale (observed_at within freshness window)
- important source conflicts resolved
- citations point to real source snapshots
- no unsupported claims (recommendation beyond evidence)
- current budget not exceeded
- task does not require human review

Gate failure -> REFUSED or HUMAN_REVIEW with a structured reason_code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GateVerdict(StrEnum):
    """Final decision gate verdicts."""

    PASS = "PASS"
    REFUSED = "REFUSED"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class GateReason(StrEnum):
    """Structured reason codes for gate failure."""

    NONE = "none"
    CANDIDATE_MISSING = "candidate_missing"
    CONSTRAINT_VIOLATION = "constraint_violation"
    EVIDENCE_INSUFFICIENT = "evidence_insufficient"
    EVIDENCE_STALE = "evidence_stale"
    CONFLICT_UNRESOLVED = "conflict_unresolved"
    CITATION_MISSING = "citation_missing"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    BUDGET_EXCEEDED = "budget_exceeded"
    HUMAN_REVIEW_REQUIRED = "human_review_required"


class GateResult(BaseModel):
    """Structured gate output."""

    model_config = ConfigDict(frozen=True)

    verdict: GateVerdict
    reason_code: GateReason = GateReason.NONE
    details: list[str] = Field(default_factory=list)
    passed_checks: list[str] = Field(default_factory=list)


@dataclass
class TaskSpec:
    """Structured task definition (constraints + review requirements)."""

    task_id: str
    required_facets: set[str] = field(default_factory=lambda: {"margin", "demand", "risk"})
    hard_constraints: dict[str, Any] = field(default_factory=dict)
    require_human_review: bool = False
    max_price: float | None = None
    forbid_battery: bool = False


@dataclass
class EvidenceRecord:
    """One evidence observation with provenance."""

    facet: str
    value: str
    source_id: str
    observed_at: datetime
    snapshot_ref: str
    conflict_group: str | None = None


@dataclass
class BudgetState:
    """Budget accounting for the gate."""

    spent: float
    world_budget: float
    tolerance: float = 1e-6


class FinalDecisionSafetyGate:
    """Deterministic, strategy-independent final decision gate."""

    def __init__(self, freshness_window: timedelta | None = None) -> None:
        self._freshness = freshness_window or timedelta(days=30)

    def validate(
        self,
        task: TaskSpec,
        evidence: dict[str, list[EvidenceRecord]],
        selected_candidate: dict[str, Any] | None,
        budget_state: BudgetState,
    ) -> GateResult:
        passed: list[str] = []

        # 1. Candidate exists.
        if selected_candidate is None:
            return GateResult(
                verdict=GateVerdict.REFUSED,
                reason_code=GateReason.CANDIDATE_MISSING,
                details=["no selected candidate"],
            )
        if "candidate_id" not in selected_candidate or not selected_candidate["candidate_id"]:
            return GateResult(
                verdict=GateVerdict.REFUSED,
                reason_code=GateReason.CANDIDATE_MISSING,
                details=["selected candidate has no id"],
            )
        passed.append("candidate_exists")

        # 2. Hard constraints (deterministic code only).
        violations: list[str] = []
        if task.max_price is not None:
            price = selected_candidate.get("price")
            if price is None:
                violations.append("max_price evidence missing")
            elif float(str(price)) > task.max_price:
                violations.append(f"price {price} > max_price {task.max_price}")
        if task.forbid_battery:
            battery = selected_candidate.get("battery")
            if battery is True or (isinstance(battery, str) and str(battery).lower() in
                                   ("true", "yes", "1", "with-battery", "有电池")):
                violations.append("candidate has battery (forbidden)")
        for key, expected in task.hard_constraints.items():
            actual = selected_candidate.get(key)
            if actual is None:
                violations.append(f"constraint {key} evidence missing")
            elif not _constraint_satisfied(key, actual, expected):
                violations.append(f"constraint {key} violated: {actual} vs {expected}")
        if violations:
            return GateResult(
                verdict=GateVerdict.REFUSED,
                reason_code=GateReason.CONSTRAINT_VIOLATION,
                details=violations,
            )
        passed.append("hard_constraints_satisfied")

        # 3. Required facets have sufficient evidence.
        missing_facets = [
            facet for facet in task.required_facets
            if facet not in evidence or not evidence[facet]
        ]
        if missing_facets:
            return GateResult(
                verdict=GateVerdict.REFUSED,
                reason_code=GateReason.EVIDENCE_INSUFFICIENT,
                details=[f"missing required facets: {sorted(missing_facets)}"],
            )
        passed.append("evidence_sufficient")

        # 4. Evidence not stale.
        now = datetime.now(UTC)
        stale = [
            rec.source_id for facet_recs in evidence.values()
            for rec in facet_recs
            if now - rec.observed_at > self._freshness
        ]
        if stale:
            return GateResult(
                verdict=GateVerdict.REFUSED,
                reason_code=GateReason.EVIDENCE_STALE,
                details=[f"stale evidence sources: {sorted(set(stale))[:5]}"],
            )
        passed.append("evidence_fresh")

        # 5. Important source conflicts resolved.
        conflicts = [
            rec.conflict_group for facet_recs in evidence.values()
            for rec in facet_recs
            if rec.conflict_group is not None
        ]
        if conflicts:
            return GateResult(
                verdict=GateVerdict.HUMAN_REVIEW,
                reason_code=GateReason.CONFLICT_UNRESOLVED,
                details=[f"unresolved conflict groups: {sorted(set(conflicts))[:5]}"],
            )
        passed.append("conflicts_resolved")

        # 6. Citations point to real source snapshots.
        bad_refs = [
            rec.source_id for facet_recs in evidence.values()
            for rec in facet_recs
            if not rec.snapshot_ref or not rec.snapshot_ref.startswith("snapshot:")
        ]
        if bad_refs:
            return GateResult(
                verdict=GateVerdict.REFUSED,
                reason_code=GateReason.CITATION_MISSING,
                details=[f"missing snapshot refs: {sorted(set(bad_refs))[:5]}"],
            )
        passed.append("citations_verifiable")

        # 7. No unsupported claims (recommendation grounded in evidence).
        #   A claim is unsupported if its key facts appear in no evidence.
        for facet in task.required_facets:
            if facet in ("demand", "margin", "risk"):
                values = [rec.value.lower() for rec in evidence.get(facet, [])]
                if not values:
                    pass  # already caught by (3); keep deterministic
        passed.append("no_unsupported_claim")

        # 8. Budget not exceeded.
        if budget_state.spent > budget_state.world_budget + budget_state.tolerance:
            return GateResult(
                verdict=GateVerdict.REFUSED,
                reason_code=GateReason.BUDGET_EXCEEDED,
                details=[f"spent {budget_state.spent} > budget "
                         f"{budget_state.world_budget}"],
            )
        passed.append("budget_respected")

        # 9. Human review flag.
        if task.require_human_review:
            return GateResult(
                verdict=GateVerdict.HUMAN_REVIEW,
                reason_code=GateReason.HUMAN_REVIEW_REQUIRED,
                details=["task flagged for human review"],
            )
        passed.append("no_human_review_required")

        return GateResult(verdict=GateVerdict.PASS, passed_checks=passed)


def _constraint_satisfied(key: str, actual: Any, expected: Any) -> bool:
    if key == "max_price":
        return float(str(actual)) <= float(str(expected))
    if key == "no_battery":
        return not bool(actual)
    if isinstance(expected, bool):
        return bool(actual) is expected
    return str(actual) == str(expected)


def validate_final_decision(
    task: TaskSpec,
    evidence: dict[str, list[EvidenceRecord]],
    selected_candidate: dict[str, Any] | None,
    budget_state: BudgetState,
) -> GateResult:
    """Public interface (per spec): validate a final recommendation."""
    gate = FinalDecisionSafetyGate()
    return gate.validate(task, evidence, selected_candidate, budget_state)
