"""Phase 5: Dream-RSI tests — replay coverage, unknown-action rejection,
promotion/rollback, and the recursive optimization loop (offline)."""

from pathlib import Path

from marketpilot.optimization.dream_rsi import (
    ExplorationTree,
    HistoricalReplaySimulator,
    ObservedStep,
    ParameterizedPolicy,
    PolicyRegistry,
    PolicyStatus,
    RecursiveOptimizationLoop,
    ReplayWorldArchive,
    TrajectoryRecord,
    _record_trajectory,
    policy_hash,
)
from marketpilot.policy.controller import (
    StopReason,
)
from marketpilot.world.core import AgentWorldView, WorldOracle, build_minimal_world


def test_policy_hash_is_deterministic() -> None:
    a = policy_hash({"weight_margin": 0.5})
    b = policy_hash({"weight_margin": 0.5})
    c = policy_hash({"weight_margin": 0.6})
    assert a == b
    assert a != c
    # Partial params merge with defaults deterministically.
    assert policy_hash({"voi_threshold": 0.05}) == policy_hash({"voi_threshold": 0.05})


def test_policy_never_reads_oracle() -> None:
    world = build_minimal_world(seed=7)
    policy = ParameterizedPolicy(name="p")
    view = AgentWorldView(world)
    result = policy.execute(view)
    assert result.selected_id is not None
    assert not hasattr(view, "ground_truth_for")


def test_exploration_tree_records_and_coverage() -> None:
    tree = ExplorationTree()
    tree.observe(
        "w1",
        ObservedStep(0, "margin", "s0", "s1", 1.5, "GO"),
    )
    tree.observe(
        "w1",
        ObservedStep(1, "demand", "s1", "s2", 1.0, "GO"),
    )
    assert tree.known_actions("w1", "s0") == ["margin"]
    assert tree.coverage("w1") == {"states": 2, "actions": 2}
    assert tree.coverage("w2") == {"states": 0, "actions": 0}


def test_archive_roundtrip(tmp_path: Path) -> None:
    world = build_minimal_world(seed=7)
    archive = ReplayWorldArchive(tmp_path)
    archive.register_world(world)
    policy = ParameterizedPolicy({"weight_margin": 0.55}, name="p")
    result = policy.execute(AgentWorldView(world))
    trajectory = _record_trajectory(world, policy, result)
    archive.record_trajectory(trajectory)
    reloaded = ReplayWorldArchive(tmp_path)
    assert len(reloaded.trajectories()) == 1
    assert reloaded.trajectories()[0].policy_hash == policy.hash
    assert world.world_id in reloaded.worlds()


def test_historical_replay_rejects_unknown_action(tmp_path: Path) -> None:
    world = build_minimal_world(seed=7)
    archive = ReplayWorldArchive(tmp_path)
    archive.register_world(world)
    policy = ParameterizedPolicy({"weight_margin": 0.6}, name="p")
    # Record a trajectory that includes an impossible action.
    trajectory = TrajectoryRecord(
        world_id=world.world_id,
        split=world.split.value,
        policy_hash=policy.hash,
        steps=[
            ObservedStep(0, "not-an-action", "s0", "s1", 1.0, "GO"),
        ],
        outcome="GO",
        total_cost=1.0,
    )
    archive.record_trajectory(trajectory)
    simulator = HistoricalReplaySimulator(archive)
    result, report = simulator.replay_policy(policy, world)
    # The unknown action must be rejected, never invented.
    assert report["rejected_actions"] == ["not-an-action"]
    assert report["coverage"] == 0.0
    # With no replayed evidence the decision is INSUFFICIENT (not a blind
    # GO): the replayed trajectory did not gather required evidence.
    assert result.decision == "INSUFFICIENT"
    assert result.stop_reason is StopReason.BUDGET_EXHAUSTED


def test_historical_replay_no_recorded_trajectory_is_refused(tmp_path: Path) -> None:
    world = build_minimal_world(seed=7)
    archive = ReplayWorldArchive(tmp_path)
    archive.register_world(world)
    policy = ParameterizedPolicy({"weight_margin": 0.6}, name="p")
    simulator = HistoricalReplaySimulator(archive)
    result, report = simulator.replay_policy(policy, world)
    assert report["coverage"] == 0.0
    assert result.stop_reason is StopReason.REFUSED


def test_replay_coverage_reported_explicitly(tmp_path: Path) -> None:
    world = build_minimal_world(seed=7)
    archive = ReplayWorldArchive(tmp_path)
    archive.register_world(world)
    policy = ParameterizedPolicy({"weight_margin": 0.55}, name="p")
    result = policy.execute(AgentWorldView(world))
    trajectory = _record_trajectory(world, policy, result)
    archive.record_trajectory(trajectory)
    simulator = HistoricalReplaySimulator(archive)
    _r, report = simulator.replay_policy(policy, world)
    assert report["coverage"] == 1.0
    # replay_hits counts only replayed (non-stop) actions.
    non_stop = [s for s in trajectory.steps if s.action != "stop"]
    assert report["replay_hits"] == len(non_stop)
    assert report["support_status"] == "SUPPORTED"


def test_registry_promotion_and_rollback() -> None:
    registry = PolicyRegistry()
    good = ParameterizedPolicy({"weight_margin": 0.6}, name="good")
    bad = ParameterizedPolicy({"weight_margin": 0.1}, name="bad")
    registry.propose(good)
    registry.mark_dream_evaluated(good.hash)
    registry.promote(good.hash)
    assert registry.status(good.hash) is PolicyStatus.PROMOTED
    registry.propose(bad)
    registry.rollback(bad.hash)
    assert registry.status(bad.hash) is PolicyStatus.ROLLED_BACK
    assert registry.active().name == "good"
    assert len(registry.history()) == 2


def test_recursive_loop_runs_three_rounds(tmp_path: Path) -> None:
    dev = build_minimal_world(seed=7)
    confirmation = build_minimal_world(seed=8)
    archive = ReplayWorldArchive(tmp_path)
    archive.register_world(dev)
    archive.register_world(confirmation)
    registry = PolicyRegistry()
    loop = RecursiveOptimizationLoop(archive, registry, rounds=3)
    summary = loop.run(dev, confirmation)
    assert summary["rounds"] == 3
    assert len(summary["round_log"]) == 3
    assert all("round" in entry for entry in summary["round_log"])
    # The promoted policy must be a concrete policy.
    assert registry.active() is not None


def test_loop_promotes_or_rolls_back_each_round(tmp_path: Path) -> None:
    dev = build_minimal_world(seed=7)
    confirmation = build_minimal_world(seed=8)
    archive = ReplayWorldArchive(tmp_path)
    archive.register_world(dev)
    archive.register_world(confirmation)
    registry = PolicyRegistry()
    loop = RecursiveOptimizationLoop(archive, registry, rounds=2)
    summary = loop.run(dev, confirmation)
    for entry in summary["round_log"]:
        assert entry["action"] in {"promote", "rollback"}


def test_dream_evaluator_penalizes_disagreement() -> None:
    from marketpilot.optimization.dream_rsi import DreamEvaluator
    from marketpilot.policy.controller import ControllerResult, StopReason

    evaluator = DreamEvaluator()
    policy = ParameterizedPolicy({"weight_margin": 0.6}, name="p")
    # Full coverage, same decision as recorded -> high score.
    report_agree = {
        "coverage": 1.0,
        "rejected_actions": [],
    }
    result_agree = ControllerResult(
        selected_id="x", stop_reason=StopReason.SUFFICIENT_EVIDENCE, decision="GO"
    )
    score_agree = evaluator.evaluate(policy, report_agree, result_agree, recorded_outcome="GO")
    assert score_agree == 1.0
    # Same coverage but a DIFFERENT decision than recorded -> penalized.
    result_disagree = ControllerResult(
        selected_id="y", stop_reason=StopReason.SUFFICIENT_EVIDENCE, decision="NO_GO"
    )
    score_disagree = evaluator.evaluate(
        policy, report_agree, result_disagree, recorded_outcome="GO"
    )
    assert score_disagree < score_agree
    # Rejected actions also penalized.
    report_rejected = {
        "coverage": 0.5,
        "rejected_actions": ["not-an-action"],
    }
    score_rejected = evaluator.evaluate(
        policy, report_rejected, result_agree, recorded_outcome="GO"
    )
    assert score_rejected < score_agree


def test_parameterized_policy_variant_changes_scoring() -> None:
    world = build_minimal_world(seed=7)
    base = ParameterizedPolicy(name="base")
    variant = ParameterizedPolicy({"weight_margin": 1.0, "weight_demand": 0.0}, name="variant")
    base_result = base.execute(AgentWorldView(world))
    variant_result = variant.execute(AgentWorldView(world))
    # Both should still pick the good product (margin-dominant scoring).
    oracle = WorldOracle(world)
    good = oracle.best_product_id()
    assert base_result.selected_id == good
    assert variant_result.selected_id == good
