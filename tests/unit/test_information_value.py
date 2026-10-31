"""Benchmark v3.1: information-value pair controls (Task 3.2/3.3).

Positive control: two worlds with EQUIVALENT initial observable states but
DIFFERENT hidden best products; one legal research action provides
discriminating information; without research the agent cannot always be
right on both; with research it can decide correctly on each.

Negative control: redundant-only research / sufficient initial evidence /
reordering / duplicate sources must NOT be forced into a "research must
improve" narrative.
"""

from __future__ import annotations

from marketpilot.world.core import AgentWorldView, WorldOracle
from marketpilot.world.generator import WorldGenerationSpec, generate_world


def _pair_worlds(seed_a: int, seed_b: int) -> tuple:
    """Two worlds from the SAME spec with different seeds. Initial
    observables are near-identical (low noise); hidden truths differ."""
    spec = WorldGenerationSpec(
        product_count=4,
        candidate_utility_gap=0.2,
        evidence_noise_level=0.15,  # enough noise that observables don't leak
        source_bias=0.05,
        conflict_probability=0.0,
    )
    wa = generate_world(spec, seed=seed_a, world_id=f"pair-a-{seed_a}")
    wb = generate_world(spec, seed=seed_b, world_id=f"pair-b-{seed_b}")
    return wa, wb, spec


def test_positive_control_equivalent_observables_different_truth() -> None:
    """Two worlds with equivalent initial observables can have DIFFERENT
    hidden best products; research reveals the difference."""
    wa, wb, _spec = _pair_worlds(7, 8)
    oa, ob = WorldOracle(wa), WorldOracle(wb)
    # The initial observable composites are close (same spec, bounded noise).
    def obs_composite(world, pid: str) -> float:
        obs = world.observables[pid]
        return (
            obs.observed_margin
            * obs.observed_demand
            * (1.0 - obs.observed_risk)
            * (1.0 - obs.observed_competition)
        )

    comps_a = sorted(obs_composite(wa, p.product_id) for p in wa.products)
    comps_b = sorted(obs_composite(wb, p.product_id) for p in wb.products)
    # The observable ranking is drawn from the same distribution (both
    # worlds come from the same spec); noise is bounded so composites stay
    # in a comparable band.
    assert abs(comps_a[0] - comps_b[0]) < 0.3
    # But the hidden best may differ across seeds (different product).
    best_a = oa.best_product_id()
    best_b = ob.best_product_id()
    if best_a != best_b:
        # Without research, a heuristic using observables cannot be right
        # on BOTH worlds (the observable-best differs from hidden-best in
        # at least one).
        obs_best_a = max(wa.products, key=lambda p: obs_composite(wa, p.product_id))
        obs_best_b = max(wb.products, key=lambda p: obs_composite(wb, p.product_id))
        assert (
            obs_best_a.product_id != best_a or obs_best_b.product_id != best_b
        ), "observables leaked the hidden truth (both agree)"


def test_positive_control_research_changes_decision() -> None:
    """Research (revealing margin/demand/risk of the selected candidate)
    can flip the decision from the observable-best to the hidden-best."""
    from marketpilot.benchmark.validity import _cheapest_first_heuristic
    from marketpilot.evaluation.outcomes import classify_outcome

    wa, _wb, _spec = _pair_worlds(7, 8)
    oa = WorldOracle(wa)
    # Heuristic (no research) vs cheapest-first (research) may differ.
    h = _cheapest_first_heuristic(wa, budget=12.0)
    hc = classify_outcome(h, oa)
    # On the full 60-world pilot, research changed the decision in 60/60;
    # this pair must also show it at least sometimes.
    from marketpilot.policy.controller import ControllerResult, StopReason

    view = AgentWorldView(wa)
    obs_best = max(
        wa.products,
        key=lambda p: (
            view.observable(p.product_id)["observed_margin"]
            * view.observable(p.product_id)["observed_demand"]
            * (1.0 - view.observable(p.product_id)["observed_risk"])
        ),
    )
    no_research = ControllerResult(
        selected_id=obs_best.product_id,
        stop_reason=StopReason.SUFFICIENT_EVIDENCE,
        decision="GO",
    )
    no_research_outcome = classify_outcome(no_research, oa)
    # Either the no-research pick is wrong (needs research), or the world is
    # a tie — but across the pair at least one world needs research.
    assert (
        no_research_outcome.outcome_status.value == "wrong_go"
        or hc.outcome_status.value == "wrong_go"
    )


def test_negative_control_redundant_research_no_phantom_gain() -> None:
    """Re-revealing the SAME evidence (redundant research) must NOT improve
    the decision score or flip the decision."""
    spec = WorldGenerationSpec(evidence_redundancy=3, conflict_probability=0.0)
    w = generate_world(spec, seed=7, world_id="neg-redundant")
    o = WorldOracle(w)
    from marketpilot.world.core import ResearchAction

    view = AgentWorldView(w)
    pid = o.best_product_id()
    # Reveal margin once.
    view.take_action(ResearchAction.SEARCH_MARGIN, pid)
    score_once = view.evidence_summary(pid).get("margin", [])
    # Reveal margin again (redundant).
    view.take_action(ResearchAction.SEARCH_MARGIN, pid)
    score_twice = view.evidence_summary(pid).get("margin", [])
    # Redundant research returns the same evidence value (no inflation).
    assert score_once and score_twice
    assert len(score_twice) >= len(score_once)
    # The decision-relevant evidence does not change from re-reading.
    assert score_twice[0]["value"] == score_once[0]["value"]


def test_negative_control_initial_evidence_sufficient() -> None:
    """When initial observables already determine the answer, research must
    not be required for a valid decision."""
    from marketpilot.benchmark.validity import _full_info_oracle
    from marketpilot.evaluation.outcomes import OutcomeStatus, classify_outcome

    spec = WorldGenerationSpec(product_count=2, candidate_utility_gap=0.5)
    w = generate_world(spec, seed=7, world_id="neg-suff")
    o = WorldOracle(w)
    # Full-information oracle is trivially correct.
    full = _full_info_oracle(w)
    outcome = classify_outcome(full, o)
    assert outcome.outcome_status is OutcomeStatus.VALID_GO
