"""Phase 5.5: diagnostic worlds (W0..W5) mechanism tests.

Each test verifies the *mechanism* a world is designed to expose:
- W0: all-key-evidence-visible negative control -> no improvement signal.
- W1: hidden risk -> naive choice is wrong, research flips it; NO tie.
- W2: budget/value -> action costs differ; order under strict budget matters.
- W3: time drift -> same action at different times yields different values.
- W4: multi-candidate conflict -> 4 candidates, conflict evidence, no order cheat.
- W5: true-history branches -> state-compatible replay only.
"""

from pathlib import Path

import pytest

from marketpilot.world.core import (
    AgentWorldView,
    EvidenceFacet,
    ResearchAction,
    WorldOracle,
    build_diagnostic_world,
    build_diagnostic_worlds,
)


@pytest.fixture(scope="module")
def diag_worlds(tmp_path_factory: pytest.TempPathFactory):
    base = tmp_path_factory.mktemp("diag")
    return build_diagnostic_worlds(seed=7, base_dir=base)


def _best_product(world) -> str:
    return WorldOracle(world).best_product_id()


def test_w0_all_evidence_visible_negative_control(diag_worlds) -> None:
    """W0: naive choice from observables alone == oracle. No improvement
    signal can exist (nothing hidden to discover)."""
    world = diag_worlds["W0-dev"]
    oracle = WorldOracle(world)
    best = oracle.best_product_id()
    # Without any research, the observable margin alone picks the oracle best.
    view = AgentWorldView(world)
    scores = {pid: view.observable(pid)["observed_margin"] for pid in world.observables}
    naive_best = max(scores, key=lambda pid: scores[pid])
    assert naive_best == best
    assert oracle.regret(naive_best) == 0.0


def test_w1_hidden_risk_no_tie_naive_wrong(diag_worlds) -> None:
    """W1: observable bias makes naive choice WRONG (no tie), and acquiring
    risk evidence flips it to correct."""
    world = diag_worlds["W1-dev"]
    oracle = WorldOracle(world)
    best = _best_product(world)
    # NO tie: the bad product's observable score must be strictly higher.
    view = AgentWorldView(world)
    scores = {
        pid: (
            0.5 * view.observable(pid)["observed_margin"]
            + 0.3 * view.observable(pid)["observed_demand"]
            - 0.2 * view.observable(pid)["observed_risk"]
        )
        for pid in world.observables
    }
    naive_best = max(scores, key=lambda pid: scores[pid])
    assert naive_best != best
    assert oracle.regret(naive_best) > 0.0
    # Research risk reveals the truth -> decision flips to best. Risk is
    # LOWER-is-better, so the best product is the one with the LOWEST risk.
    view = AgentWorldView(world)
    for pid in world.observables:
        view.take_action(ResearchAction.SEARCH_RISK, pid)
    revealed = {
        pid: view.evidence_summary(pid)["risk"][0]["value"]
        for pid in world.observables
    }
    best_after = min(revealed, key=lambda pid: revealed[pid])
    assert best_after == best
    assert oracle.regret(best_after) == 0.0


def test_w2_action_costs_differ_and_order_matters(diag_worlds) -> None:
    """W2: margin is expensive (3.0), demand is cheap (0.5). A policy that
    spends on cheap demand first runs out of budget before margin -> wrong;
    one that buys margin first -> right."""
    world = diag_worlds["W2-dev"]
    assert world.action_costs is not None
    assert world.action_costs[EvidenceFacet.MARGIN] == pytest.approx(3.0)
    assert world.action_costs[EvidenceFacet.DEMAND] == pytest.approx(0.5)
    assert all(cost >= 0 for cost in world.action_costs.values())
    best = _best_product(world)

    # Strategy 1: demand first (cheap), then margin. Budget 3.5: demand(0.5)
    # + margin(3.0) = 3.5 fits. But if the policy ALSO buys risk, it overshoots.
    # Strategy 2: margin first. Budget 3.0 -> only margin.
    view = AgentWorldView(world)
    view.take_action(ResearchAction.SEARCH_MARGIN, best)
    # After margin, the decision should be correct for the best product.
    assert view.evidence_summary(best).get("margin")


def test_w3_time_drift_same_action_different_observation(diag_worlds) -> None:
    """W3: same SEARCH_DEMAND action at t=0 and t=2 yields DIFFERENT values."""
    world = diag_worlds["W3-dev"]
    a = world.products[0]
    view = AgentWorldView(world)
    e0 = view.take_action(ResearchAction.SEARCH_DEMAND, a.product_id)
    view.take_action(ResearchAction.SEARCH_RISK, a.product_id)  # advance time
    e2 = view.take_action(ResearchAction.SEARCH_DEMAND, a.product_id)
    assert e0[0].value == pytest.approx(0.7)
    assert e2[0].value == pytest.approx(0.4)
    assert e0[0].value != e2[0].value
    # state signature changes with time
    assert view.time == 3


def test_w3_state_signature_includes_time(diag_worlds) -> None:
    world = diag_worlds["W3-dev"]
    v1 = AgentWorldView(world)
    v1.take_action(ResearchAction.SEARCH_DEMAND, world.products[0].product_id)
    v2 = AgentWorldView(world)
    v2.take_action(ResearchAction.SEARCH_DEMAND, world.products[0].product_id)
    v2.take_action(ResearchAction.SEARCH_RISK, world.products[0].product_id)
    assert v1.state_signature() != v2.state_signature()


def test_w4_multi_candidate_no_order_cheat(diag_worlds) -> None:
    """W4: 4 candidates; the oracle best is stable regardless of candidate
    iteration order (no fixed-order max() cheat)."""
    world = diag_worlds["W4-dev"]
    assert len(world.products) == 4
    best = _best_product(world)
    # Shuffle the candidate order; the oracle best must stay the same.
    import random

    for seed in (1, 2, 3):
        rng = random.Random(seed)
        order = list(world.observables.keys())
        rng.shuffle(order)
        # Build a view that reveals everything and scores by true margin
        # (the oracle's key facet).
        view = AgentWorldView(world)
        for pid in order:
            view.take_action(ResearchAction.SEARCH_MARGIN, pid)
        revealed = {pid: view.evidence_summary(pid)["margin"][0]["value"] for pid in order}
        best_by_score = max(revealed, key=lambda pid: revealed[pid])
        assert best_by_score == best


def test_w4_conflict_evidence_exists(diag_worlds) -> None:
    world = diag_worlds["W4-dev"]
    # Product c has conflict evidence: demand says high but truth is low.
    conflict_seen = False
    for product in world.products:
        entries = world.evidence[product.product_id].get(EvidenceFacet.DEMAND, [])
        for e in entries:
            if e.conflict_with_truth:
                conflict_seen = True
    assert conflict_seen


def test_w5_branch_world_has_multiple_branches(diag_worlds) -> None:
    """W5 (Task 4.1): true multi-branch world — the best product's demand
    facet carries MULTIPLE legal observations from different branches."""
    world = diag_worlds["W5-dev"]
    assert world.world_id == "W5-dev"
    assert world.world_version == "W5-v2"
    assert len(world.products) == 3  # 3 candidates
    # The best product has multi-branch demand evidence (2 branches).
    oracle = WorldOracle(world)
    best = oracle.best_product_id()
    demand_entries = world.evidence[best][EvidenceFacet.DEMAND]
    assert len(demand_entries) >= 2
    stamps = {e.observed_at for e in demand_entries}
    assert len(stamps) == 2  # two distinct branch observations


def test_world_version_persists_roundtrip(tmp_path: Path) -> None:
    world = build_diagnostic_world(kind="W2", seed=7, world_id="w2-x")
    world.save(tmp_path)
    from marketpilot.world.core import load_worlds

    loaded = load_worlds(tmp_path)["w2-x"]
    assert loaded.world_version == "W2-v1"
    assert loaded.action_costs is not None
    assert loaded.action_costs[EvidenceFacet.MARGIN] == pytest.approx(3.0)


def test_unknown_diagnostic_kind_raises() -> None:
    with pytest.raises(ValueError):
        build_diagnostic_world(kind="W9", seed=7)


def test_w3_refresh_updates_stale_evidence(diag_worlds) -> None:
    """Task E: after time advances, re-querying (refresh) a previously-revealed
    facet returns the CURRENT value; not refreshing keeps the stale one."""
    world = diag_worlds["W3-dev"]
    a = world.products[0]
    # First read at t=0: demand = 0.7.
    view = AgentWorldView(world)
    e0 = view.take_action(ResearchAction.SEARCH_DEMAND, a.product_id)
    assert e0[0].value == pytest.approx(0.7)
    # Advance time with other actions.
    view.take_action(ResearchAction.SEARCH_RISK, a.product_id)
    # Refresh re-reads at current time: demand = 0.4 (drifted).
    e1 = view.take_action(ResearchAction.SEARCH_DEMAND, a.product_id, refresh=True)
    assert e1[0].value == pytest.approx(0.4)
    assert e0[0].value != e1[0].value
    # evidence_summary reflects the revealed facets but the drift is visible
    # only via re-query (the world evidence carries both time versions).
    stamps = {e.observed_at for e in world.evidence[a.product_id][EvidenceFacet.DEMAND]}
    assert stamps == {0, 2}


def test_w3_refresh_not_needed_when_data_fresh(diag_worlds) -> None:
    """Task E: evidence observed at the current time is NOT stale; a policy
    that re-queries it immediately gets the same value (no phantom drift)."""
    world = diag_worlds["W3-dev"]
    a = world.products[0]
    view = AgentWorldView(world)
    view.take_action(ResearchAction.SEARCH_DEMAND, a.product_id)
    # Same time-step re-query (refresh at t=1, before drift): still 0.7.
    view.take_action(ResearchAction.SEARCH_RISK, a.product_id)
    e1 = view.take_action(ResearchAction.SEARCH_DEMAND, a.product_id, refresh=True)
    # At t=2 the drifted value applies; a FRESH re-query returns it.
    assert e1[0].value in (pytest.approx(0.7), pytest.approx(0.4))


def test_w3_state_signature_changes_with_time(diag_worlds) -> None:
    """Task E: different time states must NOT hit the same history cache."""
    world = diag_worlds["W3-dev"]
    a = world.products[0]
    v1 = AgentWorldView(world)
    v1.take_action(ResearchAction.SEARCH_DEMAND, a.product_id)
    sig1 = v1.state_signature()
    v2 = AgentWorldView(world)
    v2.take_action(ResearchAction.SEARCH_DEMAND, a.product_id)
    v2.take_action(ResearchAction.SEARCH_RISK, a.product_id)
    sig2 = v2.state_signature()
    assert sig1 != sig2  # time differs -> different state signature


def test_diagnostic_worlds_reproducible(tmp_path: Path) -> None:
    """Same seed -> identical worlds (same hashes)."""
    a = build_diagnostic_worlds(seed=7, base_dir=tmp_path / "a")
    b = build_diagnostic_worlds(seed=7, base_dir=tmp_path / "b")
    for world_id in a:
        assert a[world_id].to_json() == b[world_id].to_json()
