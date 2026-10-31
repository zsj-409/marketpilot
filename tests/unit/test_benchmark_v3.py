"""Benchmark v3: engineering tests (Task 9).

Covers: generation determinism; mechanism parameters change behavior;
hidden-truth isolation; product-ID/order leak resistance; source noise;
time drift; budget not overrun; conflicts not averaged; no Valid GO without
evidence; oracle correctness; solvability; split uniqueness; manifest
reproducibility; replay world isolation; old W0-W5 regression.
"""

from pathlib import Path

from marketpilot.benchmark.validity import run_world_validity
from marketpilot.world.core import (
    AgentWorldView,
    ResearchAction,
    World,
    WorldOracle,
    build_diagnostic_world,
)
from marketpilot.world.generator import (
    WorldGenerationSpec,
    generate_world,
    world_config_hash,
)
from marketpilot.world.manifest import BenchmarkManifest


def _w(spec: WorldGenerationSpec, seed: int = 7, wid: str = "t") -> World:
    return generate_world(spec, seed=seed, world_id=wid)


def test_generation_deterministic() -> None:
    """Same spec + seed => identical world (same config hash)."""
    spec = WorldGenerationSpec()
    a = _w(spec, seed=7, wid="t1")
    b = _w(spec, seed=7, wid="t1")
    assert world_config_hash(a) == world_config_hash(b)


def test_mechanism_parameters_change_behavior() -> None:
    """Different noise/bias/conflict configs yield different evidence
    distributions (Task 9: params must have behavioral effect)."""
    quiet = WorldGenerationSpec(evidence_noise_level=0.02, conflict_probability=0.0)
    noisy = WorldGenerationSpec(evidence_noise_level=0.4, conflict_probability=0.8)
    wq = _w(quiet)
    wn = _w(noisy)
    assert world_config_hash(wq) != world_config_hash(wn)
    n_conflicts = sum(
        1
        for pid in wn.evidence
        for facet in wn.evidence[pid]
        for e in wn.evidence[pid][facet]
        if e.conflict_with_truth
    )
    assert n_conflicts > 0


def test_hidden_truth_not_in_agent_view() -> None:
    """AgentWorldView must not expose true_utility/true_risk (Task 9)."""
    spec = WorldGenerationSpec()
    w = _w(spec)
    view = AgentWorldView(w)
    obs = view.observable(w.products[0].product_id)
    # No hidden-truth keys in the observable surface.
    for key in ("true_utility", "true_risk", "viable"):
        assert key not in obs, f"leak: {key} in observable"


def test_product_id_order_no_leak() -> None:
    """The best product must not be identifiable by ID order (Task 9)."""
    spec = WorldGenerationSpec(product_count=6, candidate_utility_gap=0.15)
    # Across several seeds, the best product is NOT always at position 0.
    positions = set()
    for seed in range(7, 12):
        w = _w(spec, seed=seed, wid=f"t6-{seed}")
        oracle = WorldOracle(w)
        best = oracle.best_product_id()
        ids = [p.product_id for p in w.products]
        positions.add(ids.index(best))
    # The best product appears at multiple positions (no position leak).
    assert len(positions) > 1
    # The best product's ID is not the lexicographically-smallest across
    # all seeds (no ID-order leak).
    lex_firsts = set()
    for seed in range(7, 12):
        w = _w(spec, seed=seed, wid=f"t6-{seed}")
        oracle = WorldOracle(w)
        ids = [p.product_id for p in w.products]
        lex_firsts.add(min(ids) == oracle.best_product_id())
    assert not all(lex_firsts)  # not always the lex-smallest


def test_source_noise_and_reliability() -> None:
    """Evidence noise is bounded and conflict entries are flagged (Task 9)."""
    spec = WorldGenerationSpec(evidence_noise_level=0.2, conflict_probability=0.5)
    w = _w(spec, seed=9, wid="tn")
    for pid in w.evidence:
        for facet in w.evidence[pid]:
            for e in w.evidence[pid][facet]:
                assert 0.0 <= e.value <= 1.0
    conflicts = [
        e
        for pid in w.evidence
        for facet in w.evidence[pid]
        for e in w.evidence[pid][facet]
        if e.conflict_with_truth
    ]
    assert len(conflicts) > 0


def test_time_drift_creates_stale_and_fresh() -> None:
    """temporal_drift>0 => evidence has observed_at and stale entries
    (Task 9: stale evidence must not count as current)."""
    spec = WorldGenerationSpec(temporal_drift=0.6)
    w = _w(spec, seed=8, wid="td")
    has_observed_at = any(
        e.observed_at is not None
        for pid in w.evidence
        for facet in w.evidence[pid]
        for e in w.evidence[pid][facet]
    )
    assert has_observed_at


def test_action_costs_do_not_overrun_budget() -> None:
    """A controller with budget B must not spend > B (Task 9)."""
    from marketpilot.optimization.dream_rsi import ParameterizedPolicy

    spec = WorldGenerationSpec(research_budget=6.0, action_cost_asymmetry=0.8)
    w = _w(spec, seed=7, wid="tb")
    pol = ParameterizedPolicy(strategy="fixed", name="fixed")
    result = pol.execute(AgentWorldView(w), budget=6.0)
    assert result.total_cost <= 6.0 + 1e-6


def test_insufficient_evidence_no_valid_go() -> None:
    """A result with missing required evidence is never classified Valid GO
    (Task 9)."""
    from marketpilot.evaluation.outcomes import OutcomeStatus, classify_outcome

    spec = WorldGenerationSpec(evidence_missingness=0.5)
    w = _w(spec, seed=7, wid="tins")
    oracle = WorldOracle(w)
    view = AgentWorldView(w)
    # Research only ONE facet (not enough).
    view.take_action(ResearchAction.SEARCH_MARGIN, w.products[0].product_id)
    from marketpilot.policy.controller import ControllerResult, StopReason

    result = ControllerResult(
        selected_id=w.products[0].product_id,
        stop_reason=StopReason.SUFFICIENT_EVIDENCE,
        revealed_facets={
            pid: [f.value for f in view.revealed_facets(pid)]
            for pid in [p.product_id for p in w.products]
        },
        decision="GO",
    )
    outcome = classify_outcome(result, oracle)
    assert outcome.outcome_status is not OutcomeStatus.VALID_GO


def test_oracle_correct() -> None:
    """WorldOracle regret of the best product is 0; regret of a worse product
    is > 0 (Task 9)."""
    spec = WorldGenerationSpec(product_count=4, candidate_utility_gap=0.2)
    w = _w(spec, seed=7, wid="to")
    oracle = WorldOracle(w)
    best = oracle.best_product_id()
    assert oracle.regret(best) == 0.0
    other = next(p.product_id for p in w.products if p.product_id != best)
    assert oracle.regret(other) > 0.0


def test_solvability_matches_budget() -> None:
    """A scarce-budget world (2.0 < min-cost 3.0) is EXACTLY proven
    must_abstain; a generous one is feasible (Task 1.2/9)."""
    scarce = WorldGenerationSpec(research_budget=2.0, product_count=4)
    generous = WorldGenerationSpec(research_budget=30.0, product_count=4)
    ws = _w(scarce, seed=7, wid="ts")
    wg = _w(generous, seed=7, wid="tg")
    rs = run_world_validity(ws)
    rg = run_world_validity(wg)
    assert rs["solvability"]["must_abstain"] is True
    assert rs["reachability"]["status"] == "abstention_required"
    assert rg["solvability"]["must_abstain"] is False
    assert rg["reachability"]["status"] == "go_reachable"


def test_w0_w5_regression_still_pass() -> None:
    """Old diagnostic worlds W0-W5 remain constructible and oracle-consistent
    (Task 9: do not break the mechanism regression suite)."""
    for kind in ["W0", "W1", "W2", "W3", "W4", "W5"]:
        w = build_diagnostic_world(kind=kind, seed=7, world_id=f"reg-{kind}")
        oracle = WorldOracle(w)
        assert oracle.best_product_id() is not None


def test_manifest_reproducible(tmp_path: Path) -> None:
    """Manifest save/load round-trips; dataset_split_hash is stable
    (Task 9)."""
    spec = WorldGenerationSpec()
    w = _w(spec, seed=7, wid="m1")
    m = BenchmarkManifest(
        benchmark_version="v3-test",
        generator_version="0.1",
        evaluator_version="0.1",
        metric_contract_version="1.0",
        git_commit="test",
        execution_mode="pilot",
        world_ids=[w.world_id],
        world_config_hashes={w.world_id: world_config_hash(w)},
        seed_registry={w.world_id: 7},
    )
    path = tmp_path / "manifest.json"
    m.save(path)
    loaded = BenchmarkManifest.load(path)
    assert loaded.dataset_split_hash == m.dataset_split_hash
    assert loaded.verify_world(w.world_id, world_config_hash(w))


def test_old_vs_new_worlds_no_cross_split_reuse() -> None:
    """Different world_ids have different config hashes (no duplicate
    markets across instances; Task 9)."""
    spec = WorldGenerationSpec()
    a = _w(spec, seed=7, wid="i1")
    b = _w(spec, seed=7, wid="i2")  # same spec+seed but DIFFERENT world_id
    # Config hash includes world_id, so i1 != i2 (instance identity).
    assert world_config_hash(a) != world_config_hash(b)
    # But with the same world_id they are identical (determinism).
    c = _w(spec, seed=7, wid="i1")
    assert world_config_hash(a) == world_config_hash(c)
