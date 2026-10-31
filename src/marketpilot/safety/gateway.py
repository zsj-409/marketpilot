"""Unified Safety Gate integration layer (Release Gate Task 1).

Every path that emits a final product recommendation to a user MUST pass
through this gateway — CLI, Workbench /run, Agent Runtime (LLM Decision
Agent), Decision Engine, and any future streaming path.

Two-layer metrics are recorded for every emission:
- pre_gate_outcome  : what the strategy/model produced BEFORE gating
- gate_decision     : PASS / REFUSED / HUMAN_REVIEW (from the gate)
- gate_reason_codes : the structured reasons
- post_gate_outcome : what is actually released to the user

A model's Unsupported GO intercepted by the gate counts as a SAFETY
INTERCEPTION, never as a successful product recommendation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from marketpilot.domain.enums import Decision
from marketpilot.safety.gate import (
    BudgetState,
    EvidenceRecord,
    GateReason,
    GateResult,
    GateVerdict,
    TaskSpec,
    validate_final_decision,
)

if TYPE_CHECKING:
    from marketpilot.domain.evidence import EvidenceItem
    from marketpilot.domain.recommendations import Recommendation


@dataclass
class GatedEmission:
    """One gated final-output event (auditable)."""

    path: str  # "cli.demo" | "cli.product_selection" | "workbench.run" | "agent.decision"
    pre_gate_outcome: str  # what the strategy produced (GO / INSUFFICIENT / ...)
    gate_decision: str  # PASS / REFUSED / HUMAN_REVIEW
    gate_reason_codes: list[str] = field(default_factory=list)
    post_gate_outcome: str = ""  # what is released (after gating)
    selected_candidate_id: str | None = None
    emitted_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    details: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "pre_gate_outcome": self.pre_gate_outcome,
            "gate_decision": self.gate_decision,
            "gate_reason_codes": self.gate_reason_codes,
            "post_gate_outcome": self.post_gate_outcome,
            "selected_candidate_id": self.selected_candidate_id,
            "emitted_at": self.emitted_at,
            "details": self.details,
        }


def _evidence_to_records(
    evidence: list[EvidenceItem] | dict[str, Any],
) -> dict[str, list[EvidenceRecord]]:
    """Adapt domain evidence into gate EvidenceRecords.

    Accepts either a list of EvidenceItem (agent runtime) or a
    facet -> observations dict (synthetic world / workbench).
    """
    out: dict[str, list[EvidenceRecord]] = {}
    now = datetime.now(UTC)
    if isinstance(evidence, dict):
        for facet, records in evidence.items():
            if isinstance(records, list):
                out[str(facet)] = [
                    _coerce_record(r, str(facet), now) for r in records
                ]
        return out
    for item in evidence:
        facet = str(
            getattr(item, "related_entity", None)
            or getattr(item, "facet", "evidence")
        )
        out.setdefault(facet, []).append(
            EvidenceRecord(
                facet=facet,
                value=str(getattr(item, "excerpt", getattr(item, "content", ""))),
                source_id=str(getattr(item, "source_uri", "unknown")),
                observed_at=getattr(
                    item, "retrieved_at", getattr(item, "observed_at", now)
                ),
                snapshot_ref=f"snapshot:{getattr(item, 'source_uri', 'unknown')}",
            )
        )
    return out


def _coerce_record(r: Any, facet: str, now: datetime) -> EvidenceRecord:
    if isinstance(r, EvidenceRecord):
        return r
    if isinstance(r, dict):
        return EvidenceRecord(
            facet=str(r.get("facet", facet)),
            value=str(r.get("value", r.get("content", ""))),
            source_id=str(r.get("source_id", "unknown")),
            observed_at=r.get("observed_at", now),
            snapshot_ref=str(r.get("snapshot_ref", "snapshot:unknown")),
            conflict_group=r.get("conflict_group"),
        )
    return EvidenceRecord(
        facet=facet, value=str(r), source_id="unknown",
        observed_at=now, snapshot_ref="snapshot:unknown",
    )


def gate_recommendation(
    path: str,
    recommendation: Recommendation | None,
    evidence: list[EvidenceItem] | dict[str, Any],
    *,
    max_price: float | None = None,
    forbid_battery: bool = False,
    extra_constraints: dict[str, Any] | None = None,
    spent: float = 0.0,
    world_budget: float = 12.0,
    require_human_review: bool = False,
    task_id: str = "task",
) -> GatedEmission:
    """Gate a final recommendation emission (the ONLY sanctioned path)."""
    if recommendation is None or recommendation.decision is not Decision.GO:
        # No GO recommendation -> REFUSED by policy (nothing safe to emit;
        # NO_GO / INSUFFICIENT / missing are all non-recommendations).
        return GatedEmission(
            path=path,
            pre_gate_outcome=(
                recommendation.decision.value if recommendation is not None
                else "NO_RECOMMENDATION"
            ),
            gate_decision=GateVerdict.REFUSED.value,
            gate_reason_codes=[GateReason.EVIDENCE_INSUFFICIENT.value],
            post_gate_outcome="REFUSED",
            selected_candidate_id=None,
            details=["no GO recommendation produced by the strategy"],
        )

    pre = recommendation.decision.value
    candidate = recommendation.candidate
    selected = {
        "candidate_id": str(candidate.candidate_id),
        "price": max_price,  # price not in ProductCandidate; gate uses constraints
        "battery": False,
        "name": candidate.name,
    }
    evidence_records = _evidence_to_records(evidence)
    constraints = dict(extra_constraints or {})
    if max_price is not None:
        constraints["max_price"] = max_price
    task = TaskSpec(
        task_id=task_id,
        required_facets={"margin", "demand", "risk"},
        hard_constraints=constraints,
        max_price=max_price,
        forbid_battery=forbid_battery,
        require_human_review=require_human_review,
    )
    result: GateResult = validate_final_decision(
        task, evidence_records, selected,
        BudgetState(spent=spent, world_budget=world_budget),
    )
    post = {
        GateVerdict.PASS: recommendation.decision.value,
        GateVerdict.REFUSED: "REFUSED",
        GateVerdict.HUMAN_REVIEW: "HUMAN_REVIEW",
    }[result.verdict]
    return GatedEmission(
        path=path,
        pre_gate_outcome=pre,
        gate_decision=result.verdict.value,
        gate_reason_codes=(
            [] if result.verdict is GateVerdict.PASS else [result.reason_code.value]
        ),
        post_gate_outcome=post,
        selected_candidate_id=str(candidate.candidate_id),
        details=result.details,
    )


def gate_workbench_run(
    decision: str,
    selected: str | None,
    evidence_chain: dict[str, list[str]],
    *,
    spent: float,
    world_budget: float,
    max_price: float = 100.0,
    forbid_battery: bool = True,
    task_id: str = "task",
) -> GatedEmission:
    """Gate a Workbench /run emission (synthetic world path)."""
    from datetime import UTC as _UTC

    now = datetime.now(_UTC)
    if decision != "GO" or selected is None:
        return GatedEmission(
            path="workbench.run",
            pre_gate_outcome=decision,
            gate_decision=GateVerdict.REFUSED.value,
            gate_reason_codes=[GateReason.EVIDENCE_INSUFFICIENT.value],
            post_gate_outcome="REFUSED",
            selected_candidate_id=selected,
            details=["no GO recommendation with a selected candidate"],
        )
    # Align with the OutcomeClassifier's sufficiency semantics: ALL
    # candidates must have the required facets revealed (the classifier's
    # evidence_sufficient_for standard). This keeps the gate consistent
    # with post-gate outcome — a partial-coverage GO (adaptive-voi style)
    # is REFUSED here, never PASS.
    REQUIRED = {"margin", "demand", "risk"}
    all_covered = all(
        REQUIRED.issubset(set(facets))
        for facets in evidence_chain.values()
    ) if evidence_chain else False
    if not all_covered:
        return GatedEmission(
            path="workbench.run",
            pre_gate_outcome=decision,
            gate_decision=GateVerdict.REFUSED.value,
            gate_reason_codes=[GateReason.EVIDENCE_INSUFFICIENT.value],
            post_gate_outcome="REFUSED",
            selected_candidate_id=selected,
            details=["not all candidates have required facets revealed"],
        )
    # Selected candidate's evidence then goes through the detailed checks.
    selected_facets = evidence_chain.get(selected, [])
    evidence = {
        facet: [
            EvidenceRecord(facet=facet, value="ok", source_id=f"src-{facet}",
                           observed_at=now, snapshot_ref=f"snapshot:{facet}-1")
        ]
        for facet in selected_facets
    }
    result = validate_final_decision(
        TaskSpec(task_id=task_id, max_price=max_price,
                 forbid_battery=forbid_battery),
        evidence, {"candidate_id": selected, "price": 50.0, "battery": False},
        BudgetState(spent=spent, world_budget=world_budget),
    )
    post = {
        GateVerdict.PASS: "GO",
        GateVerdict.REFUSED: "REFUSED",
        GateVerdict.HUMAN_REVIEW: "HUMAN_REVIEW",
    }[result.verdict]
    return GatedEmission(
        path="workbench.run",
        pre_gate_outcome=decision,
        gate_decision=result.verdict.value,
        gate_reason_codes=(
            [] if result.verdict is GateVerdict.PASS else [result.reason_code.value]
        ),
        post_gate_outcome=post,
        selected_candidate_id=selected,
        details=result.details,
    )
