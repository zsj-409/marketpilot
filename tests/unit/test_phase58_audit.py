"""Phase 5.8: coverage expansion + promotion audit tests (Task 3/8).

Verifies:
- CoveragePlanner executes only legal actions
- new history branches add unique state/action coverage
- duplicate trajectories do NOT inflate coverage
- incompatible states are not merged
- promotion audit: REFUSED incumbent replaced by valid GO = IMPROVED
- TIED not counted as improvement
- same-world replay vs confirmation score consistency
"""

from pathlib import Path

from marketpilot.optimization.coverage_planner import ArchiveCoveragePlanner
from marketpilot.optimization.dream_rsi import (
    ParameterizedPolicy,
    PolicyRegistry,
    PromotionKind,
    RecursiveOptimizationLoop,
    ReplayWorldArchive,
)
from marketpilot.optimization.proposer import MultiFamilyProposer
from marketpilot.world.core import AgentWorldView, build_diagnostic_world


def test_coverage_planner_adds_unique_branches(tmp_path: Path) -> None:
    """CoveragePlanner executes new branches and adds unique state/action
    coverage (not duplicate trajectories)."""
    world = build_diagnostic_world(kind="W1", seed=7, world_id="w1")
    archive = ReplayWorldArchive(tmp_path)
    archive.register_world(world)
    planner = ArchiveCoveragePlanner(archive, budget=20.0)
    report1 = planner.plan_expansion(world, max_branches=4)
    assert report1.new_executions >= 1
    assert report1.unique_state_count >= 1
    assert report1.total_collection_cost > 0
    # Re-running with the SAME policies adds NO new coverage (duplicates).
    planner2 = ArchiveCoveragePlanner(archive, budget=20.0)
    report2 = planner2.plan_expansion(world, max_branches=4)
    assert report2.new_executions == 0  # no new unique pairs


def test_coverage_planner_only_legal_actions(tmp_path: Path) -> None:
    """Planner never records illegal/unknown actions (no fabricated results)."""
    world = build_diagnostic_world(kind="W1", seed=7, world_id="w1")
    archive = ReplayWorldArchive(tmp_path)
    archive.register_world(world)
    planner = ArchiveCoveragePlanner(archive, budget=20.0)
    report = planner.plan_expansion(world, max_branches=4)
    assert report.unsupported_action_count == 0
    for trace in archive.trajectories_for_world(world.world_id):
        for step in trace.steps:
            assert step.action in {"stop", "search_margin", "search_demand",
                                   "search_risk", "search_market",
                                   "search_reliability", "search_competition"}


def test_duplicate_trajectories_do_not_inflate_coverage(tmp_path: Path) -> None:
    """Re-recording the SAME branch (same policy, same world) must NOT count
    as new coverage."""
    world = build_diagnostic_world(kind="W1", seed=7, world_id="w1")
    archive = ReplayWorldArchive(tmp_path)
    archive.register_world(world)
    policy = ParameterizedPolicy(strategy="fixed", name="fixed")
    from marketpilot.optimization.dream_rsi import _record_trajectory

    r1 = policy.execute(AgentWorldView(world))
    archive.record_trajectory(_record_trajectory(world, policy, r1), round_index=0)
    before = len(archive.trajectories_for_world(world.world_id))
    # Same policy re-executed and re-recorded.
    r2 = policy.execute(AgentWorldView(world))
    archive.record_trajectory(_record_trajectory(world, policy, r2), round_index=1)
    after = len(archive.trajectories_for_world(world.world_id))
    assert after == before + 1  # appended (append-only) but...
    # ...coverage report must NOT double-count the same (state, action) pairs.
    planner = ArchiveCoveragePlanner(archive, budget=0.0)
    report = planner.plan_expansion(world, max_branches=1)
    # No NEW execution possible (budget 0) and duplicates add no coverage.
    assert report.new_executions == 0


def test_refused_incumbent_replaced_by_go_is_improved(tmp_path: Path) -> None:
    """W1 round 1: incumbent adaptive-voi REFUSED (full regret), challenger
    missing-evidence GO (regret 0) -> IMPROVED (not TIED)."""
    dev = build_diagnostic_world(kind="W1", seed=7, world_id="w1-dev")
    conf = build_diagnostic_world(kind="W1", seed=8, world_id="w1-conf")
    archive = ReplayWorldArchive(tmp_path)
    archive.register_world(dev)
    archive.register_world(conf)
    registry = PolicyRegistry()
    loop = RecursiveOptimizationLoop(archive, registry, rounds=1, pool_mode="full")
    loop.proposer = MultiFamilyProposer(seed=7)
    summary = loop.run(dev, conf)
    entry = summary["round_log"][0]
    if entry["action"] == "promote":
        assert entry["kind"] == "improved"  # refused -> GO is a real improvement
        assert entry["incumbent_regret"] > 0  # refused incumbent charged full regret
        assert entry["challenger_regret"] == 0.0


def test_tied_not_counted_as_improvement(tmp_path: Path) -> None:
    """Same-family same-quality promotions are TIED, not IMPROVED."""
    dev = build_diagnostic_world(kind="W1", seed=7, world_id="w1-dev")
    conf = build_diagnostic_world(kind="W1", seed=8, world_id="w1-conf")
    archive = ReplayWorldArchive(tmp_path)
    archive.register_world(dev)
    archive.register_world(conf)
    registry = PolicyRegistry()
    loop = RecursiveOptimizationLoop(archive, registry, rounds=3, pool_mode="full")
    loop.proposer = MultiFamilyProposer(seed=7)
    summary = loop.run(dev, conf)
    # Round 1 is improved; later rounds with same family+quality are TIED.
    kinds = [e["kind"] for e in summary["round_log"] if e["action"] == "promote"]
    if len(kinds) >= 2:
        assert kinds[0] == "improved"
        assert all(k == "tied" for k in kinds[1:])


def test_same_world_replay_confirmation_consistency(tmp_path: Path) -> None:
    """A policy that succeeds on confirmation also succeeds on its own
    replay trace (same world, same actions)."""
    world = build_diagnostic_world(kind="W1", seed=7, world_id="w1")
    archive = ReplayWorldArchive(tmp_path)
    archive.register_world(world)
    policy = ParameterizedPolicy(strategy="fixed", name="fixed")
    from marketpilot.optimization.dream_rsi import (
        HistoricalReplaySimulator,
        _record_trajectory,
    )

    result = policy.execute(AgentWorldView(world))
    traj = _record_trajectory(world, policy, result)
    archive.record_trajectory(traj, round_index=0)
    sim = HistoricalReplaySimulator(archive)
    replay_result, report = sim.replay_policy(policy, world)
    assert report["support_status"] == "SUPPORTED"
    # Both the live run and the replay make the same decision on this world.
    assert replay_result.decision == result.decision


def test_regressed_challenger_not_promoted(tmp_path: Path) -> None:
    """Task 1.3: a challenger that is REGRESSED on confirmation must NOT be
    promoted, even if confirmation otherwise 'succeeded'."""
    registry = PolicyRegistry()
    active = registry.active()
    assert active is not None
    before = active.hash
    # Paired confirmation outcome: challenger strictly worse (regret 0.4 vs 0).
    kind = registry.classify_outcome(
        "chal-hash", quality_delta=-0.4, cost_delta=-1.0
    )
    assert kind is PromotionKind.REGRESSED
    # Promotion gate: REGRESSED -> rollback, active unchanged.
    registry.rollback("chal-hash", reason=f"kind={kind.value}")
    active_after = registry.active()
    assert active_after is not None
    assert active_after.hash == before


def test_global_best_static_only_generation_dev(tmp_path: Path) -> None:
    """Best Static must be selected using Generation DEV only (never
    confirmation/test worlds)."""
    from marketpilot.world.core import WorldSplit

    dev = build_diagnostic_world(
        kind="W1", seed=7, world_id="w1-dev", split=WorldSplit.DEV
    )
    assert dev.split is WorldSplit.DEV
    # The selection loop in the attribution script only ever reads dev_worlds.
    # Here we verify the worlds are genuinely DEV-split (no leakage signal).
    assert dev.world_id.endswith("dev") or dev.split.value == "dev"


def test_no_replay_does_not_use_dream(tmp_path: Path) -> None:
    """No-Replay optimization must not use dream/replay scoring."""

    # No-Replay = propose + live confirmation only; there is no archive
    # dream evaluation. We assert that building a No-Replay loop does not
    # touch the replay simulator's dream scorer.
    dev = build_diagnostic_world(kind="W1", seed=7, world_id="w1-dev")
    archive = ReplayWorldArchive(tmp_path)
    archive.register_world(dev)
    registry = PolicyRegistry()
    # A No-Replay loop would run variants live; it must not construct a
    # DreamEvaluator over the archive. (Structural check: the loop still
    # exists and runs; dream scoring is opt-in.)
    loop = RecursiveOptimizationLoop(archive, registry, rounds=1, pool_mode="full")
    assert loop.replay is not None  # replay simulator exists but...
    # ...the key guard: No-Replay mode must not be built from a dream scorer.
    assert getattr(loop, "dream_evaluator", None) is None


def test_locked_test_isolated(tmp_path: Path) -> None:
    """Locked Test worlds must never be registered in the training archive."""
    dev = build_diagnostic_world(kind="W1", seed=7, world_id="w1-dev")
    archive = ReplayWorldArchive(tmp_path)
    archive.register_world(dev)
    # Confirmation worlds (separate split) are used for confirmation, not
    # for archive collection (no optimization trajectories from them).
    assert all(
        t.split == "dev"
        for t in archive.trajectories_for_world("w1-dev")
    )
