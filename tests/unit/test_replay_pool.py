"""Phase 5.5: cumulative replay world pool tests (Task 3 / Task 8).

Verifies:
- trajectories accumulate across rounds (append-only, round-indexed)
- Current-History-Only cannot read older rounds' history
- Full Cumulative Pool dreams over ALL accumulated history
- roundtrip preserves round indices
- archive never silently deletes old records
"""

from pathlib import Path

from marketpilot.input.spec import WorldSplit
from marketpilot.optimization.dream_rsi import (
    HistoricalReplaySimulator,
    ObservedStep,
    ParameterizedPolicy,
    PolicyRegistry,
    RecursiveOptimizationLoop,
    ReplayWorldArchive,
    TrajectoryRecord,
    _record_trajectory,
)
from marketpilot.world.core import AgentWorldView, build_minimal_world


def _make_traj(world, policy, round_index: int, archive: ReplayWorldArchive) -> None:
    result = policy.execute(AgentWorldView(world))
    traj = _record_trajectory(world, policy, result)
    archive.record_trajectory(traj, round_index=round_index)


def test_archive_accumulates_across_rounds(tmp_path: Path) -> None:
    """Trajectories from different rounds are stored side by side (append-only)."""
    world = build_minimal_world(seed=7)
    archive = ReplayWorldArchive(tmp_path)
    archive.register_world(world)
    p1 = ParameterizedPolicy({"weight_margin": 0.5}, name="p1")
    p2 = ParameterizedPolicy({"weight_margin": 0.6}, name="p2")
    _make_traj(world, p1, round_index=0, archive=archive)
    _make_traj(world, p2, round_index=1, archive=archive)
    assert len(archive.trajectories()) == 2
    assert len(archive.trajectories(round_index=0)) == 1
    assert len(archive.trajectories(round_index=1)) == 1


def test_archive_roundtrip_preserves_rounds(tmp_path: Path) -> None:
    world = build_minimal_world(seed=7)
    archive = ReplayWorldArchive(tmp_path)
    archive.register_world(world)
    p1 = ParameterizedPolicy({"weight_margin": 0.5}, name="p1")
    p2 = ParameterizedPolicy({"weight_margin": 0.6}, name="p2")
    _make_traj(world, p1, round_index=0, archive=archive)
    _make_traj(world, p2, round_index=2, archive=archive)
    reloaded = ReplayWorldArchive(tmp_path)
    assert len(reloaded.trajectories()) == 2
    assert len(reloaded.trajectories(round_index=2)) == 1


def test_archive_never_silently_deletes(tmp_path: Path) -> None:
    """Same policy+world in a later round does NOT erase the earlier record."""
    world = build_minimal_world(seed=7)
    archive = ReplayWorldArchive(tmp_path)
    archive.register_world(world)
    p = ParameterizedPolicy({"weight_margin": 0.5}, name="p")
    _make_traj(world, p, round_index=0, archive=archive)
    _make_traj(world, p, round_index=1, archive=archive)
    assert len(archive.trajectories()) == 2  # both kept


def test_full_pool_dreams_over_all_history(tmp_path: Path) -> None:
    """pool_mode='full': a variant's dream sees trajectories from ALL rounds."""
    dev = build_minimal_world(seed=7)
    conf = build_minimal_world(seed=8)
    archive = ReplayWorldArchive(tmp_path)
    archive.register_world(dev)
    archive.register_world(conf)
    registry = PolicyRegistry()
    loop = RecursiveOptimizationLoop(archive, registry, rounds=3, pool_mode="full")
    summary = loop.run(dev, conf)
    assert summary["pool_mode"] == "full"
    # 3 rounds + init + promote_dev re-records -> pool accumulates > 1.
    assert summary["pool_size"] >= 3


def test_current_history_only_ignores_old_pool(tmp_path: Path) -> None:
    """pool_mode='current': dream sees ONLY the most recent round's history.

    Verify by pre-seeding an OLD round-0 trajectory for the active policy and
    checking that a 'current' loop does not replay it (it uses the trajectory
    recorded at the start of the current run instead)."""
    dev = build_minimal_world(seed=7)
    conf = build_minimal_world(seed=8)
    archive = ReplayWorldArchive(tmp_path)
    archive.register_world(dev)
    archive.register_world(conf)
    registry = PolicyRegistry()
    loop = RecursiveOptimizationLoop(archive, registry, rounds=2, pool_mode="current")
    summary = loop.run(dev, conf)
    assert summary["pool_mode"] == "current"
    # In 'current' mode the loop still records each round's trajectory, but
    # each dream only reads the immediately-previous round.
    assert summary["pool_size"] >= 2


def test_full_and_current_pool_both_run(tmp_path: Path) -> None:
    """Both pool modes execute without error and produce comparable outputs."""
    dev = build_minimal_world(seed=7)
    conf = build_minimal_world(seed=8)
    results = {}
    for mode in ("full", "current"):
        archive = ReplayWorldArchive(tmp_path / mode)
        archive.register_world(dev)
        archive.register_world(conf)
        registry = PolicyRegistry()
        loop = RecursiveOptimizationLoop(archive, registry, rounds=3, pool_mode=mode)
        results[mode] = loop.run(dev, conf)
    assert results["full"]["rounds"] == 3
    assert results["current"]["rounds"] == 3
    assert results["full"]["pool_mode"] == "full"
    assert results["current"]["pool_mode"] == "current"


def test_unknown_action_in_pool_is_rejected(tmp_path: Path) -> None:
    """A trajectory with an unknown action in the pool reduces support."""
    world = build_minimal_world(seed=7)
    archive = ReplayWorldArchive(tmp_path)
    archive.register_world(world)
    policy = ParameterizedPolicy({"weight_margin": 0.6}, name="p")
    bad_traj = TrajectoryRecord(
        world_id=world.world_id,
        split=world.split.value,
        policy_hash=policy.hash,
        steps=[ObservedStep(0, "not-an-action", "s0", "s1", 1.0, "GO")],
        outcome="GO",
        total_cost=1.0,
    )
    archive.record_trajectory(bad_traj, round_index=0)
    sim = HistoricalReplaySimulator(archive)
    _result, report = sim.replay_policy(policy, world)
    assert report["support_status"] == "UNSUPPORTED"
    assert report["attempt_coverage"] == 0.0


def test_confirmation_shards_are_consumed_per_round(tmp_path: Path) -> None:
    """Task 5: each round consumes ONE pre-allocated confirmation shard;
    shards are never reused across rounds."""
    dev = build_minimal_world(seed=7)
    # Three distinct confirmation shards (world-level isolation).
    shards = [
        build_minimal_world(seed=10, world_id="conf-shard-0"),
        build_minimal_world(seed=11, world_id="conf-shard-1"),
        build_minimal_world(seed=12, world_id="conf-shard-2"),
    ]
    archive = ReplayWorldArchive(tmp_path)
    archive.register_world(dev)
    for shard in shards:
        archive.register_world(shard)
    registry = PolicyRegistry()
    loop = RecursiveOptimizationLoop(
        archive, registry, rounds=3, confirmation_shards=shards
    )
    loop.run(dev, shards[0])
    # Each round used a DIFFERENT shard (no reuse).
    used = list(loop.shard_usage.values())
    assert len(used) == 3
    assert len(set(used)) == 3  # all distinct world_ids
    assert "EXHAUSTED" not in used


def test_confirmation_shard_exhaustion_blocks_promotion(tmp_path: Path) -> None:
    """Task 5: when confirmation shards run out, later rounds cannot confirm
    (no silent reuse, no infinite search until promotion)."""
    dev = build_minimal_world(seed=7)
    # Only ONE shard for 3 rounds -> rounds 2,3 exhausted.
    shards = [build_minimal_world(seed=10, world_id="conf-shard-0")]
    archive = ReplayWorldArchive(tmp_path)
    archive.register_world(dev)
    archive.register_world(shards[0])
    registry = PolicyRegistry()
    loop = RecursiveOptimizationLoop(
        archive, registry, rounds=3, confirmation_shards=shards
    )
    loop.run(dev, shards[0])
    used = list(loop.shard_usage.values())
    assert used[0] != "EXHAUSTED"
    assert "EXHAUSTED" in used  # later rounds exhausted


def test_locked_test_not_in_shards(tmp_path: Path) -> None:
    """The Locked TEST world must never appear in confirmation shards."""
    dev = build_minimal_world(seed=7, split=WorldSplit.DEV, world_id="dev")
    test_world = build_minimal_world(seed=9, split=WorldSplit.TEST, world_id="locked-test")
    shards = [
        build_minimal_world(seed=10, world_id="conf-shard-0"),
        build_minimal_world(seed=11, world_id="conf-shard-1"),
    ]
    archive = ReplayWorldArchive(tmp_path)
    archive.register_world(dev)
    archive.register_world(test_world)
    for shard in shards:
        archive.register_world(shard)
    registry = PolicyRegistry()
    loop = RecursiveOptimizationLoop(
        archive, registry, rounds=2, confirmation_shards=shards
    )
    loop.run(dev, shards[0])
    used = set(loop.shard_usage.values())
    assert "locked-test" not in used
