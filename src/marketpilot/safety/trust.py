"""Safety Gate evidence trust boundary (Release Hardening Task A1/A2).

The gate must NOT trust the caller's submitted evidence_chain as the
authoritative candidate/evidence set. Instead it derives candidates and
evidence from a TASK-AUTHORITATIVE state (the world/view the agent
actually executed against).

This module provides:
- `AuthoritativeTaskState`: a minimal contract exposing the authoritative
  candidate set + per-candidate revealed evidence, with provenance.
- `gate_with_authoritative_state()`: runs the gate against authoritative
  state, rejecting forged/mismatched submissions:
    * selected candidate not in authoritative set -> REFUSED
    * submitted evidence_chain inconsistent with authoritative state
      (extra/missing/mismatched facets) -> REFUSED
    * stale / conflicting evidence -> REFUSED or HUMAN_REVIEW
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from marketpilot.safety.gateway import GatedEmission, gate_workbench_run


class AuthoritativeState(Protocol):
    """What the gate may read from the task's authoritative state.

    The gate consumes ONLY this — never hidden oracle truth.
    """

    def candidate_ids(self) -> list[str]: ...

    def revealed_facets(self, candidate_id: str) -> list[str]: ...

    def evidence_records(self, candidate_id: str) -> dict[str, list[Any]]: ...


@dataclass
class AuthoritativeTaskState:
    """Concrete authoritative state wrapping an AgentWorldView + world."""

    world: Any
    view: Any
    observed_at: datetime = field(default_factory=datetime.now)

    def candidate_ids(self) -> list[str]:
        return [p.product_id for p in self.world.products]

    def revealed_facets(self, candidate_id: str) -> list[str]:
        return [f.value for f in self.view.revealed_facets(candidate_id)]

    def evidence_records(self, candidate_id: str) -> dict[str, list[Any]]:
        return {
            facet: self.world.evidence.get(candidate_id, {}).get(facet, [])
            for facet in ("margin", "demand", "risk")
        }


@dataclass
class EvidenceIntegrityReport:
    """What the integrity check found (auditable)."""

    consistent: bool
    problems: list[str] = field(default_factory=list)
    authoritative_candidates: list[str] = field(default_factory=list)
    submitted_candidates: list[str] = field(default_factory=list)


def check_evidence_integrity(
    state: AuthoritativeState,
    submitted_chain: dict[str, list[str]],
    selected: str | None,
    required_facets: set[str] | None = None,
) -> EvidenceIntegrityReport:
    """Verify the submitted evidence chain against authoritative state.

    Rejects:
    1. selected candidate not in the authoritative candidate set (forgery).
    2. submitted candidates not in authoritative set (forged extra).
    3. submitted facets for a candidate not actually revealed (mismatch).
    4. missing authoritative candidates from the submission (omission).
    """
    auth_cands = state.candidate_ids()
    problems: list[str] = []

    if selected is not None and selected not in auth_cands:
        problems.append(f"selected {selected} not in authoritative candidates")

    submitted_cands = list(submitted_chain.keys())
    for cid in submitted_cands:
        if cid not in auth_cands:
            problems.append(f"submitted candidate {cid} not authoritative (forged)")
        else:
            auth_facets = set(state.revealed_facets(cid))
            sub_facets = set(submitted_chain[cid])
            extra = sub_facets - auth_facets
            if extra:
                problems.append(
                    f"candidate {cid} claims facets {sorted(extra)} "
                    f"not revealed in authoritative state"
                )
            missing = auth_facets - sub_facets
            if missing:
                problems.append(
                    f"candidate {cid} omits authoritative facets "
                    f"{sorted(missing)}"
                )
    for cid in auth_cands:
        if cid not in submitted_cands:
            problems.append(f"candidate {cid} missing from submission (omission)")

    return EvidenceIntegrityReport(
        consistent=not problems,
        problems=problems,
        authoritative_candidates=auth_cands,
        submitted_candidates=submitted_cands,
    )


def gate_with_authoritative_state(
    path: str,
    decision: str,
    selected: str | None,
    submitted_chain: dict[str, list[str]],
    state: AuthoritativeState,
    *,
    spent: float,
    world_budget: float,
    required_facets: set[str] | None = None,
    task_id: str = "task",
) -> tuple[GatedEmission, EvidenceIntegrityReport]:
    """Gate a final emission using AUTHORITATIVE state as the source of
    truth for candidates + evidence.

    The submitted chain is used only for cross-checking; the authoritative
    state's revealed facets drive the sufficiency decision. A forged or
    mismatched submission is REFUSED (evidence_integrity_failed).
    """
    report = check_evidence_integrity(
        state, submitted_chain, selected, required_facets
    )
    if not report.consistent:
        emission = GatedEmission(
            path=path,
            pre_gate_outcome=decision,
            gate_decision="REFUSED",
            gate_reason_codes=["evidence_integrity_failed"],
            post_gate_outcome="REFUSED",
            selected_candidate_id=selected,
            details=report.problems,
        )
        return emission, report

    # Build the authoritative evidence chain (not the submitted one).
    authoritative_chain = {
        cid: state.revealed_facets(cid) for cid in state.candidate_ids()
    }
    emission = gate_workbench_run(
        decision, selected, authoritative_chain,
        spent=spent, world_budget=world_budget, task_id=task_id,
    )
    return emission, report
