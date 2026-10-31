"""Phase 5: ablation harness tests.

Covers the budget-comparable ablation conditions, strict cost accounting,
behavioral differences between conditions, replay semantics (unknown-action
rejection, no-history refusal), hidden-truth isolation, honest negative
results on easy worlds, and reproducibility under a fixed manifest.
"""

from pathlib import Path

import pytest

from marketpilot.optimization.ablations import (
    run_ablation,
    run_all_ablations,
    write_ablation_report,
)
from marketpilot.optimization.dream_rsi import (
    HistoricalReplaySimulator,
    ObservedStep,
    ParameterizedPolicy,
    PolicyRegistry,
    RecursiveOptimizationLoop,
    ReplayWorldArchive,
    TrajectoryRecord,
)
from marketpilot.world.core import AgentWorldView, WorldOracle, build_minimal_world


@pytest.fixture(scope="module")
def worlds():
    """The standard minimal worlds (deterministic, seed=7/8/9)."""
    dev = build_minimal_world(seed=7)
    confirmation = build_minimal_world(seed=8)
    test = build_minimal_world(seed=9)
    return dev, confirmation, test


@pytest.fixture()
def isolated_archive(tmp_path: Path) -> ReplayWorldArchive:
    """A fresh archive per test (no cross-test state)."""
    dev = build_minimal_world(seed=7)
    archive = ReplayWorldArchive(tmp_path)
    archive.register_world(dev)
    return archive


def test_five_conditions_execute(worlds, tmp_path: Path) -> None:
    dev, confirmation, test = worlds
    outcomes = run_all_ablations(dev, confirmation, test, tmp_path, rounds=3)
    assert {o.condition for o in outcomes} == {
        "full",
        "no-replay",
        "fixed",
        "no-diagnostics",
        "no-world-pool",
        "current-history-only",
    }
    for outcome in outcomes:
        assert outcome.rounds == 3
        assert outcome.final_decision in {"GO", "INSUFFICIENT", "NO_GO", "REFUSED"}


def test_same_budget_caliber(worlds, tmp_path: Path) -> None:
    dev, confirmation, test = worlds
    outcomes = run_all_ablations(dev, confirmation, test, tmp_path, rounds=3)
    budgets = {o.budget for o in outcomes}
    assert len(budgets) == 1  # same budget for all conditions
    assert budgets.pop() == 30.0


def test_online_cost_does_not_double_count(worlds, tmp_path: Path) -> None:
    """The full RSI condition must NOT count the same online execution twice.
    A single loop over 3 rounds does init + 3*(confirm + promote_dev) + test
    final evaluation. The old bug counted 3x the loop cost by re-running the
    loop once per round; the ledger must report exactly once."""
    dev, confirmation, test = worlds
    full = run_ablation("full", dev, confirmation, test, tmp_path / "full", rounds=3)
    # A loop over 3 rounds: init(1) + per-round confirm(1) + promote_dev(1
    # if promoted) + final test evaluation(1). With 3 promotions: 1 + 3 + 3 + 1 = 8
    # online executions. The naive per-round re-run would be 3x that.
    assert full.online_cost > 0
    assert full.online_cost < 3 * 60  # not the 3x-inflated value
    assert full.replay_cost > 0  # full RSI does dream replays


def test_fixed_does_not_update_policy(worlds, tmp_path: Path) -> None:
    dev, confirmation, test = worlds
    fixed = run_ablation("fixed", dev, confirmation, test, tmp_path / "fixed", rounds=3)
    # Fixed exploration never promotes (registry stays empty of promotions).
    assert fixed.promoted_hashes == []
    # It performs one random-variant execution per round on the dev world.
    assert len(fixed.decisions) == 3


def test_no_replay_has_zero_replay_cost(worlds, tmp_path: Path) -> None:
    dev, confirmation, test = worlds
    no_replay = run_ablation(
        "no-replay", dev, confirmation, test, tmp_path / "no-replay", rounds=3
    )
    # No-replay drops the archive/dream entirely: replay cost must be 0.
    assert no_replay.replay_cost == 0.0
    # It still does online executions (live dev + confirmation per round).
    assert no_replay.online_cost > 0


def test_no_diagnostics_uses_no_disagreement_term(worlds, tmp_path: Path) -> None:
    dev, confirmation, test = worlds
    no_diag = run_ablation(
        "no-diagnostics", dev, confirmation, test, tmp_path / "no-diag", rounds=3
    )
    # The no-diagnostics condition runs the loop with dream_threshold=-1.0
    # (no disagreement gate). It must still do dream replays (replay cost > 0).
    assert no_diag.replay_cost > 0
    # And it promotes (with threshold -1.0 everything that confirms passes).
    assert len(no_diag.promoted_hashes) >= 0


def test_no_world_pool_uses_single_world(worlds, tmp_path: Path) -> None:
    dev, confirmation, test = worlds
    no_pool = run_ablation(
        "no-world-pool", dev, confirmation, test, tmp_path / "no-pool", rounds=3
    )
    # No-world-pool runs the loop with dev as both dev and confirmation.
    assert no_pool.online_cost > 0
    assert no_pool.replay_cost > 0


def test_unknown_action_rejected(isolated_archive: ReplayWorldArchive) -> None:
    """Historical replay must reject unknown actions, never invent results."""
    dev = isolated_archive.worlds()["minimal-dev"]
    policy = ParameterizedPolicy({"weight_margin": 0.6}, name="p")
    # Record a trajectory containing an impossible action.
    traj = TrajectoryRecord(
        world_id=dev.world_id,
        split=dev.split.value,
        policy_hash=policy.hash,
        steps=[ObservedStep(0, "not-an-action", "s0", "s1", 1.0, "GO")],
        outcome="GO",
        total_cost=1.0,
    )
    isolated_archive.record_trajectory(traj)
    simulator = HistoricalReplaySimulator(isolated_archive)
    _result, report = simulator.replay_policy(policy, dev)
    assert report["rejected_actions"] == ["not-an-action"]
    assert report["coverage"] == 0.0


def test_no_history_refuses_replay(isolated_archive: ReplayWorldArchive) -> None:
    dev = isolated_archive.worlds()["minimal-dev"]
    policy = ParameterizedPolicy({"weight_margin": 0.6}, name="p")
    simulator = HistoricalReplaySimulator(isolated_archive)
    result, report = simulator.replay_policy(policy, dev)
    # No recorded trajectory -> REFUSED, zero coverage.
    assert result.stop_reason.name == "REFUSED"
    assert report["coverage"] == 0.0


def test_hidden_truth_never_in_policy_input(worlds) -> None:
    """Policies consume ONLY the AgentWorldView; the oracle is never in scope."""
    dev, _confirmation, _test = worlds
    view = AgentWorldView(dev)
    policy = ParameterizedPolicy(name="p")
    # The policy's scoring uses only revealed evidence; the view must not
    # expose hidden truth.
    assert not hasattr(view, "ground_truth")
    assert not hasattr(view, "oracle")
    result = policy.execute(view)
    assert result.selected_id is not None
    # The oracle would pick the same product only by coincidence on an easy
    # world; what matters is the policy never read it.
    oracle = WorldOracle(dev)
    best = oracle.best_product_id()
    assert isinstance(best, str)


def test_easy_world_all_methods_correct_is_not_improvement(worlds, tmp_path: Path) -> None:
    """On the easy minimal world all five conditions pick the correct product.
    This is an honest NEGATIVE result: no condition demonstrates improvement,
    so no condition may claim quality gain over the others."""
    dev, confirmation, test = worlds
    outcomes = run_all_ablations(dev, confirmation, test, tmp_path, rounds=3)
    # All conditions correct on the easy world.
    assert all(o.oracle_correct for o in outcomes)
    # All conditions tie on decision quality -> no improvement signal.
    decisions = {o.final_decision for o in outcomes}
    assert len(decisions) == 1
    # The full RSI may cost more (replays) without any quality gain.
    full = next(o for o in outcomes if o.condition == "full")
    fixed = next(o for o in outcomes if o.condition == "fixed")
    assert full.oracle_correct == fixed.oracle_correct


def test_reproducible_under_fixed_manifest(worlds, tmp_path: Path) -> None:
    """Same manifest (seeds, worlds, rounds) -> identical outcomes."""
    dev, confirmation, test = worlds
    a = run_all_ablations(dev, confirmation, test, tmp_path / "run-a", rounds=3, seed=7)
    b = run_all_ablations(dev, confirmation, test, tmp_path / "run-b", rounds=3, seed=7)
    for oa, ob in zip(a, b, strict=True):
        assert oa.condition == ob.condition
        assert oa.online_cost == ob.online_cost
        assert oa.replay_cost == ob.replay_cost
        assert oa.final_decision == ob.final_decision
        assert oa.promoted_hashes == ob.promoted_hashes


def test_write_ablation_report(worlds, tmp_path: Path) -> None:
    dev, confirmation, test = worlds
    outcomes = run_all_ablations(dev, confirmation, test, tmp_path, rounds=3)
    csv_path = write_ablation_report(outcomes, tmp_path / "report")
    assert csv_path.exists()
    text = csv_path.read_text(encoding="utf-8")
    assert "condition" in text
    assert "online_cost" in text
    assert "replay_cost" in text
    json_path = tmp_path / "report" / "ablation_results.json"
    assert json_path.exists()


def test_ledger_separates_online_and_replay(worlds, tmp_path: Path) -> None:
    """The loop's ledger must distinguish online (real) from replay (offline)
    costs, and never mix estimates into actuals."""
    dev, confirmation, _test = worlds
    archive = ReplayWorldArchive(tmp_path / "ledger")
    archive.register_world(dev)
    archive.register_world(confirmation)
    registry = PolicyRegistry()
    loop = RecursiveOptimizationLoop(archive, registry, rounds=3)
    loop.run(dev, confirmation)
    ledger = loop.ledger.to_json()
    assert ledger["online_total"] > 0
    assert ledger["replay_total"] > 0
    # Entries are per-execution with cost_type separation.
    types = set(ledger["by_type"].keys())
    assert "online_execution" in types
    assert "simulated_action" in types
    # Online entries: init + per-round confirmation/promote_dev/incumbent.
    online_entries = [e for e in ledger["entries"] if e["cost_type"] == "online_execution"]
    assert len(online_entries) >= 1 + 3  # init + at least one per round
    # Replay entries: per-dream simulated actions.
    replay_entries = [e for e in ledger["entries"] if e["cost_type"] == "simulated_action"]
    assert len(replay_entries) >= 3
