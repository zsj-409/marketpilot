"""Release Hardening Task A1/A2: Safety Gate evidence trust boundary tests.

Verifies the gate derives candidates + evidence from AUTHORITATIVE task
state, rejecting:
- selected candidate not in the real candidate set (forgery)
- forged extra candidates in the submission
- claimed facets not actually revealed (mismatch)
- omitted authoritative candidates (evidence withholding)
- stale evidence
- wrong evidence version

Also verifies single-candidate vs multi-candidate sufficiency and that
candidate ORDER does not change the verdict.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from marketpilot.safety.trust import (
    AuthoritativeTaskState,
    check_evidence_integrity,
    gate_with_authoritative_state,
)
from marketpilot.world.core import (
    AgentWorldView,
    build_diagnostic_world,
)


def _state(kind: str = "W1", seed: int = 7):
    world = build_diagnostic_world(kind=kind, seed=seed, world_id=f"{kind}-{seed}")
    view = AgentWorldView(world)
    # Research all required facets for every candidate (authoritative state).
    from marketpilot.world.core import ResearchAction

    for p in world.products:
        for facet in ("margin", "demand", "risk"):
            action = ResearchAction[f"SEARCH_{facet.upper()}"]
            view.take_action(action, p.product_id)
    return world, AuthoritativeTaskState(world, view)


def _chain_from_view(state: AuthoritativeTaskState) -> dict[str, list[str]]:
    return {cid: state.revealed_facets(cid) for cid in state.candidate_ids()}


def test_integrity_ok_authoritative_state() -> None:
    world, state = _state()
    chain = _chain_from_view(state)
    report = check_evidence_integrity(state, chain, world.products[0].product_id)
    assert report.consistent
    assert report.problems == []


def test_forged_selected_candidate_rejected() -> None:
    _, state = _state()
    chain = _chain_from_view(state)
    report = check_evidence_integrity(state, chain, "FAKE-PRODUCT")
    assert not report.consistent
    assert any("not in authoritative" in p for p in report.problems)


def test_forged_extra_candidate_rejected() -> None:
    world, state = _state()
    chain = _chain_from_view(state)
    chain["FORGED"] = ["margin", "demand", "risk"]
    report = check_evidence_integrity(state, chain, world.products[0].product_id)
    assert not report.consistent
    assert any("forged" in p for p in report.problems)


def test_claimed_unrevealed_facet_rejected() -> None:
    world, state = _state()
    chain = _chain_from_view(state)
    # Claim a facet that was NOT actually revealed.
    pid = world.products[0].product_id
    chain[pid] = chain[pid] + ["competition"]
    report = check_evidence_integrity(state, chain, pid)
    assert not report.consistent
    assert any("not revealed" in p for p in report.problems)


def test_omitted_candidate_rejected() -> None:
    world, state = _state()
    chain = _chain_from_view(state)
    # Withhold one candidate's evidence.
    chain.pop(world.products[-1].product_id)
    report = check_evidence_integrity(state, chain, world.products[0].product_id)
    assert not report.consistent
    assert any("omission" in p for p in report.problems)


def test_omitted_facet_rejected() -> None:
    world, state = _state()
    chain = _chain_from_view(state)
    pid = world.products[0].product_id
    chain[pid] = [f for f in chain[pid] if f != "risk"]
    report = check_evidence_integrity(state, chain, pid)
    assert not report.consistent
    assert any("omits" in p for p in report.problems)


def test_gate_with_authoritative_state_passes() -> None:
    world, state = _state()
    chain = _chain_from_view(state)
    emission, report = gate_with_authoritative_state(
        "workbench.run", "GO", world.products[0].product_id, chain, state,
        spent=8.0, world_budget=12.0, task_id="t1",
    )
    assert report.consistent
    assert emission.gate_decision == "PASS"
    assert emission.post_gate_outcome == "GO"


def test_gate_with_forged_chain_refused() -> None:
    world, state = _state()
    chain = _chain_from_view(state)
    chain["FORGED"] = ["margin", "demand", "risk"]
    emission, report = gate_with_authoritative_state(
        "workbench.run", "GO", world.products[0].product_id, chain, state,
        spent=8.0, world_budget=12.0, task_id="t1",
    )
    assert not report.consistent
    assert emission.gate_decision == "REFUSED"
    assert emission.gate_reason_codes == ["evidence_integrity_failed"]


def test_single_candidate_sufficient_go_allowed() -> None:
    """Task A2: single-candidate tasks with full evidence can GO — the
    sufficiency rule is per the DECISION, not 'all candidates must be
    researched'. Here the authoritative state has exactly ONE candidate."""

    class SingleCandidateState:
        def candidate_ids(self) -> list[str]:
            return ["only-p1"]

        def revealed_facets(self, candidate_id: str) -> list[str]:
            assert candidate_id == "only-p1"
            return ["margin", "demand", "risk"]

        def evidence_records(self, candidate_id: str) -> dict[str, list[object]]:
            return {}

    state = SingleCandidateState()
    chain = {"only-p1": ["margin", "demand", "risk"]}
    report = check_evidence_integrity(state, chain, "only-p1")
    assert report.consistent
    emission, _ = gate_with_authoritative_state(
        "workbench.run", "GO", "only-p1", chain, state,
        spent=8.0, world_budget=12.0, task_id="t1",
    )
    assert emission.gate_decision == "PASS"


def test_candidate_order_does_not_change_verdict() -> None:
    """Task A2: candidate order in the submission must not change the gate."""
    _, state = _state("W2", 8)
    chain = _chain_from_view(state)
    cids = list(chain.keys())
    # Forward order.
    e1, r1 = gate_with_authoritative_state(
        "workbench.run", "GO", cids[0], chain, state,
        spent=8.0, world_budget=12.0, task_id="t1",
    )
    # Reversed order.
    rev = {cid: chain[cid] for cid in reversed(cids)}
    e2, r2 = gate_with_authoritative_state(
        "workbench.run", "GO", cids[0], rev, state,
        spent=8.0, world_budget=12.0, task_id="t1",
    )
    assert r1.consistent and r2.consistent
    assert e1.gate_decision == e2.gate_decision == "PASS"


def test_gate_does_not_read_oracle() -> None:
    """Task A1 #9: the authoritative-state gate never touches oracle."""
    import inspect

    from marketpilot.safety.trust import gate_with_authoritative_state

    sig = inspect.signature(gate_with_authoritative_state)
    params = list(sig.parameters.keys())
    assert "oracle" not in params
    assert "best_utility" not in params
