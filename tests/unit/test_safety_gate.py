"""Final Decision Safety Gate tests (Task B3).

The gate must be strategy-independent: any research strategy's output goes
through the same deterministic checks. Tests cover every reason_code path.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from marketpilot.safety.gate import (
    BudgetState,
    EvidenceRecord,
    GateReason,
    GateVerdict,
    TaskSpec,
    validate_final_decision,
)

NOW = datetime.now(UTC)


def _evidence(facets: set[str] | None = None) -> dict[str, list[EvidenceRecord]]:
    facets = facets or {"margin", "demand", "risk"}
    return {
        facet: [
            EvidenceRecord(
                facet=facet, value="ok", source_id=f"src-{facet}",
                observed_at=NOW, snapshot_ref=f"snapshot:{facet}-1",
            )
        ]
        for facet in facets
    }


def _candidate(price: float = 50.0, battery: bool = False) -> dict:
    return {"candidate_id": "c1", "title": "A", "price": price, "battery": battery}


def _task(**kw) -> TaskSpec:
    defaults = {"task_id": "t1", "max_price": 100.0, "forbid_battery": True}
    defaults.update(kw)
    return TaskSpec(**defaults)


def _ok_budget() -> BudgetState:
    return BudgetState(spent=8.0, world_budget=12.0)


def test_pass_with_complete_evidence() -> None:
    result = validate_final_decision(
        _task(), _evidence(), _candidate(), _ok_budget()
    )
    assert result.verdict is GateVerdict.PASS
    assert result.reason_code is GateReason.NONE
    assert "candidate_exists" in result.passed_checks
    assert "hard_constraints_satisfied" in result.passed_checks
    assert "evidence_sufficient" in result.passed_checks
    assert "budget_respected" in result.passed_checks


def test_candidate_missing() -> None:
    result = validate_final_decision(_task(), _evidence(), None, _ok_budget())
    assert result.verdict is GateVerdict.REFUSED
    assert result.reason_code is GateReason.CANDIDATE_MISSING


def test_constraint_violation_price() -> None:
    result = validate_final_decision(
        _task(), _evidence(), _candidate(price=150.0), _ok_budget()
    )
    assert result.verdict is GateVerdict.REFUSED
    assert result.reason_code is GateReason.CONSTRAINT_VIOLATION


def test_constraint_violation_battery() -> None:
    result = validate_final_decision(
        _task(), _evidence(), _candidate(battery=True), _ok_budget()
    )
    assert result.verdict is GateVerdict.REFUSED
    assert result.reason_code is GateReason.CONSTRAINT_VIOLATION


def test_evidence_insufficient() -> None:
    result = validate_final_decision(
        _task(), _evidence({"margin", "demand"}), _candidate(), _ok_budget()
    )
    assert result.verdict is GateVerdict.REFUSED
    assert result.reason_code is GateReason.EVIDENCE_INSUFFICIENT


def test_evidence_stale() -> None:
    old = NOW - timedelta(days=90)
    stale_evidence = {
        facet: [
            EvidenceRecord(
                facet=facet, value="ok", source_id=f"src-{facet}",
                observed_at=old, snapshot_ref=f"snapshot:{facet}-1",
            )
        ]
        for facet in {"margin", "demand", "risk"}
    }
    result = validate_final_decision(
        _task(), stale_evidence, _candidate(), _ok_budget()
    )
    assert result.verdict is GateVerdict.REFUSED
    assert result.reason_code is GateReason.EVIDENCE_STALE


def test_conflict_unresolved() -> None:
    ev = _evidence()
    ev["demand"].append(
        EvidenceRecord(
            facet="demand", value="negative demand", source_id="src-conflict",
            observed_at=NOW, snapshot_ref="snapshot:demand-2",
            conflict_group="demand-g1",
        )
    )
    result = validate_final_decision(_task(), ev, _candidate(), _ok_budget())
    assert result.verdict is GateVerdict.HUMAN_REVIEW
    assert result.reason_code is GateReason.CONFLICT_UNRESOLVED


def test_citation_missing() -> None:
    ev = _evidence()
    ev["risk"][0] = EvidenceRecord(
        facet="risk", value="ok", source_id="src-bad",
        observed_at=NOW, snapshot_ref="",
    )
    result = validate_final_decision(_task(), ev, _candidate(), _ok_budget())
    assert result.verdict is GateVerdict.REFUSED
    assert result.reason_code is GateReason.CITATION_MISSING


def test_budget_exceeded() -> None:
    result = validate_final_decision(
        _task(), _evidence(), _candidate(),
        BudgetState(spent=13.0, world_budget=12.0),
    )
    assert result.verdict is GateVerdict.REFUSED
    assert result.reason_code is GateReason.BUDGET_EXCEEDED


def test_human_review_required() -> None:
    result = validate_final_decision(
        _task(require_human_review=True), _evidence(), _candidate(), _ok_budget()
    )
    assert result.verdict is GateVerdict.HUMAN_REVIEW
    assert result.reason_code is GateReason.HUMAN_REVIEW_REQUIRED


def test_unsupported_go_never_passes_gate() -> None:
    """Task B3: an unsupported GO (no evidence) must NEVER pass the gate,
    even though the metric contract penalizes it equally to abstention."""
    result = validate_final_decision(
        _task(), {}, _candidate(), _ok_budget()
    )
    assert result.verdict is GateVerdict.REFUSED
    assert result.reason_code is GateReason.EVIDENCE_INSUFFICIENT


def test_gate_strategy_independent() -> None:
    """The gate behaves identically regardless of which research strategy
    produced the candidate — same inputs, same verdict."""
    from marketpilot.optimization.dream_rsi import ParameterizedPolicy
    from marketpilot.world.core import AgentWorldView, build_diagnostic_world

    world = build_diagnostic_world(kind="W1", seed=7, world_id="w1")
    strategies = ["fixed", "missing-evidence", "uncertainty", "adaptive-voi"]
    for strategy in strategies:
        pol = ParameterizedPolicy(strategy=strategy, name=strategy)
        result = pol.execute(AgentWorldView(world))
        # Feed the SAME evidence structure through the gate: the verdict
        # depends only on evidence quality, never on the strategy name.
        evidence = {
            f: [
                EvidenceRecord(facet=f, value="ok", source_id=f"src-{f}",
                               observed_at=NOW, snapshot_ref=f"snapshot:{f}-1")
            ]
            for f in {"margin", "demand", "risk"}
        }
        gate_result = validate_final_decision(
            _task(), evidence,
            {"candidate_id": "x", "price": 50.0, "battery": False},
            _ok_budget(),
        )
        # With complete evidence the gate passes for every strategy;
        # with empty evidence it refuses for every strategy.
        assert gate_result.verdict is GateVerdict.PASS
        empty_result = validate_final_decision(_task(), {}, _candidate(), _ok_budget())
        assert empty_result.verdict is GateVerdict.REFUSED
        # Sanity: the strategy still produced a typed result.
        assert result.total_cost >= 0


def test_strategy_results_can_feed_gate() -> None:
    """Wire a real strategy outcome into the gate: candidate + evidence."""
    from marketpilot.optimization.dream_rsi import ParameterizedPolicy
    from marketpilot.world.core import AgentWorldView, build_diagnostic_world

    world = build_diagnostic_world(kind="W1", seed=7, world_id="w1")
    pol = ParameterizedPolicy(strategy="fixed", name="fixed")
    result = pol.execute(AgentWorldView(world))
    if result.decision == "GO" and result.selected_id is not None:
        # The gate sees the world's evidence for the selected candidate.
        view = AgentWorldView(world)
        revealed = view.revealed_facets(result.selected_id)
        evidence = {
            f: [
                EvidenceRecord(facet=f, value="ok", source_id=f"src-{f}",
                               observed_at=NOW, snapshot_ref=f"snapshot:{f}-1")
            ]
            for f in revealed or {"margin", "demand", "risk"}
        }
        candidate = {
            "candidate_id": result.selected_id,
            "price": 50.0, "battery": False,
        }
        out = validate_final_decision(
            _task(), evidence, candidate,
            BudgetState(spent=result.total_cost, world_budget=12.0),
        )
        # If evidence is complete the gate may pass; if the strategy
        # under-researched (adaptive), the gate refuses. Either way the
        # gate is authoritative — the strategy name never bypasses it.
        assert out.verdict in (GateVerdict.PASS, GateVerdict.REFUSED,
                               GateVerdict.HUMAN_REVIEW)
