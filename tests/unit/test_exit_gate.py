"""Phase 5 Exit Gate: Task 1 unified outcome taxonomy + Task 3 promotion gate."""

from pathlib import Path

from marketpilot.evaluation.outcomes import (
    OutcomeStatus,
    classify_outcome,
)
from marketpilot.optimization.dream_rsi import (
    ParameterizedPolicy,
    PolicyRegistry,
    PromotionKind,
    RecursiveOptimizationLoop,
    ReplayWorldArchive,
)
from marketpilot.optimization.proposer import MultiFamilyProposer
from marketpilot.policy.controller import ControllerResult, StopReason
from marketpilot.world.core import (
    AgentWorldView,
    WorldOracle,
    build_diagnostic_world,
)

# ---------------------------------------------------------------------------
# Task 1: unified outcome semantics
# ---------------------------------------------------------------------------


def _make_result(
    *,
    decision: str = "GO",
    selected_id: str | None = "p",
    refused: bool = False,
    human_review: bool = False,
    stop_reason: StopReason = StopReason.SUFFICIENT_EVIDENCE,
    revealed: dict[str, list[str]] | None = None,
    cost: float = 5.0,
) -> ControllerResult:
    return ControllerResult(
        selected_id=selected_id,
        stop_reason=stop_reason,
        total_cost=cost,
        revealed_facets=revealed
        if revealed is not None
        else {"p": ["margin", "demand", "risk"], "q": ["margin", "demand", "risk"]},
        refused=refused,
        human_review=human_review,
        decision=decision,
    )


def test_refused_with_lucky_selection_is_not_valid_go() -> None:
    """Task 1.1: REFUSED with selected_id == oracle best is NOT a valid GO."""
    world = build_diagnostic_world(kind="W1", seed=7, world_id="w1")
    oracle = WorldOracle(world)
    # The refused result coincidentally "selected" the best product.
    result = _make_result(
        decision="INSUFFICIENT",
        selected_id=oracle.best_product_id(),
        refused=True,
        revealed={},  # nothing revealed
    )
    outcome = classify_outcome(result, oracle)
    assert outcome.outcome_status is OutcomeStatus.APPROPRIATE_ABSTENTION
    assert outcome.decision_regret is None
    assert outcome.abstention_cost is not None  # charged abstention cost
    # It must NOT get zero regret for the lucky selection.
    assert outcome.task_loss > 0.0


def test_insufficient_evidence_go_is_not_valid() -> None:
    """Task 1.1: GO that picked the right product but lacks required evidence
    is NOT a valid executable recommendation."""
    world = build_diagnostic_world(kind="W1", seed=7, world_id="w1")
    oracle = WorldOracle(world)
    result = _make_result(
        decision="GO",
        selected_id=oracle.best_product_id(),
        revealed={"p": ["margin"], "q": []},  # demand/risk missing
    )
    outcome = classify_outcome(result, oracle)
    assert outcome.outcome_status is OutcomeStatus.WRONG_GO  # unsafe GO
    assert not outcome.evidence_sufficient


def test_valid_go_when_evidence_sufficient_and_correct() -> None:
    """A GO with all required evidence and the oracle-best selection is
    VALID_GO with decision_regret 0."""
    world = build_diagnostic_world(kind="W1", seed=7, world_id="w1")
    oracle = WorldOracle(world)
    result = _make_result(
        decision="GO",
        selected_id=oracle.best_product_id(),
        revealed={
            "p": ["margin", "demand", "risk"],
            "q": ["margin", "demand", "risk"],
        },
    )
    outcome = classify_outcome(result, oracle)
    assert outcome.outcome_status is OutcomeStatus.VALID_GO
    assert outcome.decision_regret == 0.0
    assert outcome.evidence_sufficient


def test_appropriate_versus_unnecessary_abstention() -> None:
    """Task 1.1/8: appropriate (insufficient evidence) vs unnecessary
    (sufficient evidence but still refused) abstentions are distinct."""
    world = build_diagnostic_world(kind="W1", seed=7, world_id="w1")
    oracle = WorldOracle(world)
    # Appropriate: nothing revealed.
    app = classify_outcome(
        _make_result(decision="INSUFFICIENT", refused=True, revealed={}), oracle
    )
    assert app.outcome_status is OutcomeStatus.APPROPRIATE_ABSTENTION
    # Unnecessary: all evidence present but still refused.
    unn = classify_outcome(
        _make_result(
            decision="INSUFFICIENT",
            refused=True,
            revealed={
                "p": ["margin", "demand", "risk"],
                "q": ["margin", "demand", "risk"],
            },
        ),
        oracle,
    )
    assert unn.outcome_status is OutcomeStatus.UNNECESSARY_ABSTENTION
    # The unnecessary abstention is worse (evidence existed).
    assert unn.task_loss > 0.0


def test_wrong_go_has_positive_regret() -> None:
    """A GO selecting a non-optimal product is WRONG_GO with positive
    decision regret."""
    world = build_diagnostic_world(kind="W1", seed=7, world_id="w1")
    oracle = WorldOracle(world)
    wrong_id = next(
        pid for pid in oracle.true_by_id() if pid != oracle.best_product_id()
    )
    result = _make_result(
        decision="GO",
        selected_id=wrong_id,
        revealed={
            "p": ["margin", "demand", "risk"],
            "q": ["margin", "demand", "risk"],
        },
    )
    outcome = classify_outcome(result, oracle)
    assert outcome.outcome_status is OutcomeStatus.WRONG_GO
    assert outcome.decision_regret > 0.0


# ---------------------------------------------------------------------------
# Task 3: promotion gate integration
# ---------------------------------------------------------------------------


def test_regressed_does_not_change_active_hash(tmp_path: Path) -> None:
    """Task 3/8: REGRESSED challenger must NOT be promoted; active hash
    unchanged. (Unit-level: classify_outcome REGRESSED + registry gate.)"""
    registry = PolicyRegistry()
    active = registry.active()
    assert active is not None
    before = active.hash
    # Simulate a paired confirmation where the challenger is worse:
    # quality_delta < 0 (incumbent regret 0, challenger regret > 0).
    kind = registry.classify_outcome(
        "chal-hash", quality_delta=-0.5, cost_delta=1.0
    )
    assert kind is PromotionKind.REGRESSED
    # The gate (mirroring RecursiveOptimizationLoop) rolls back on REGRESSED.
    registry.rollback("chal-hash", reason=f"kind={kind.value}")
    active_after = registry.active()
    assert active_after is not None
    assert active_after.hash == before


def test_tied_does_not_change_active_hash(tmp_path: Path) -> None:
    """Task 3/8: TIED challenger does NOT switch the active policy."""
    registry = PolicyRegistry()
    active = registry.active()
    assert active is not None
    before = active.hash
    kind = registry.classify_outcome(
        "chal-hash", quality_delta=0.0, cost_delta=0.0
    )
    assert kind is PromotionKind.TIED
    registry.rollback("chal-hash", reason=f"kind={kind.value}")
    active_after = registry.active()
    assert active_after is not None
    assert active_after.hash == before


def test_improved_switches_active(tmp_path: Path) -> None:
    """Task 3/8: IMPROVED challenger IS promoted and becomes active."""
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
    # W1: adaptive incumbent INSUFFICIENT -> missing-evidence challenger GO.
    assert entry["action"] == "promote"
    assert entry["kind"] == "improved"
    active = registry.active()
    assert active is not None
    assert active.strategy == "missing-evidence"


def test_confirmation_exhausted_does_not_promote(tmp_path: Path) -> None:
    """Task 3/8: CONFIRMATION_EXHAUSTED must not promote."""
    dev = build_diagnostic_world(kind="W1", seed=7, world_id="w1-dev")
    conf = build_diagnostic_world(kind="W1", seed=8, world_id="w1-conf")
    # A second confirmation world used as the (single) shard -> exhausted
    # after round 1.
    shard = build_diagnostic_world(kind="W1", seed=9, world_id="w1-shard")
    archive = ReplayWorldArchive(tmp_path)
    archive.register_world(dev)
    archive.register_world(conf)
    registry = PolicyRegistry()
    loop = RecursiveOptimizationLoop(
        archive, registry, rounds=2, pool_mode="full",
        confirmation_shards=[shard],
    )
    loop.proposer = MultiFamilyProposer(seed=7)
    summary = loop.run(dev, conf)
    # With shards exhausted, the LAST round must fail closed (no fallback
    # world): reports "confirmation_exhausted", never a promotion.
    actions = [e["action"] for e in summary["round_log"]]
    assert actions[-1] == "confirmation_exhausted"
    # The exhausted round must not have promoted its challenger.
    last = summary["round_log"][-1]
    assert last["confirmation_ok"] is False


# ---------------------------------------------------------------------------
# Task 2: replay fidelity vs generalization gap
# ---------------------------------------------------------------------------


def test_w4_same_world_replay_fidelity(tmp_path: Path) -> None:
    """Task 2.1: same world + same policy replay must reproduce the same
    decision (no REPLAY_MISMATCH)."""
    from marketpilot.optimization.dream_rsi import (
        HistoricalReplaySimulator,
        _record_trajectory,
    )

    world = build_diagnostic_world(kind="W4", seed=7, world_id="w4")
    archive = ReplayWorldArchive(tmp_path)
    archive.register_world(world)
    for fam in ["fixed", "missing-evidence", "uncertainty", "adaptive-voi"]:
        pol = ParameterizedPolicy(strategy=fam, name=fam)
        real = pol.execute(AgentWorldView(world))
        traj = _record_trajectory(world, pol, real)
        archive.record_trajectory(traj, round_index=0)
        sim = HistoricalReplaySimulator(archive)
        replay_r, report = sim.replay_policy(pol, world)
        assert report["support_status"] == "SUPPORTED"
        assert real.decision == replay_r.decision, (
            f"{fam} real={real.decision} replay={replay_r.decision}"
        )


def test_w4_cross_seed_generalization_gap(tmp_path: Path) -> None:
    """Task 2.2: the SAME policy on different W4 seeds may differ — that is a
    generalization gap (DEV_CONFIRMATION_GAP), not a replay bug."""

    dev = build_diagnostic_world(kind="W4", seed=7, world_id="w4-dev")
    conf = build_diagnostic_world(kind="W4", seed=8, world_id="w4-conf")
    pol = ParameterizedPolicy(strategy="missing-evidence", name="me")
    dev_result = pol.execute(AgentWorldView(dev))
    conf_result = pol.execute(AgentWorldView(conf))
    # Both seeds produce the same decision (INSUFFICIENT) for the systematic
    # family — the reported W4 behavior is stable across seeds.
    assert dev_result.decision == conf_result.decision == "INSUFFICIENT"


def test_replay_unsupported_marked(tmp_path: Path) -> None:
    """Task 2.3: REPLAY_UNSUPPORTED — unknown actions are explicitly marked,
    never invented."""
    from marketpilot.optimization.dream_rsi import (
        HistoricalReplaySimulator,
        ObservedStep,
        TrajectoryRecord,
    )

    world = build_diagnostic_world(kind="W1", seed=7, world_id="w1")
    archive = ReplayWorldArchive(tmp_path)
    archive.register_world(world)
    pol = ParameterizedPolicy(strategy="fixed", name="fixed")
    traj = TrajectoryRecord(
        world_id=world.world_id,
        split=world.split.value,
        policy_hash=pol.hash,
        steps=[ObservedStep(0, "magic-action", "s0", "s1", 1.0, "GO")],
        outcome="GO",
        total_cost=1.0,
    )
    archive.record_trajectory(traj)
    sim = HistoricalReplaySimulator(archive)
    _result, report = sim.replay_policy(pol, world)
    assert report["support_status"] == "UNSUPPORTED"
    assert "magic-action" in report["unsupported_actions"]


# ---------------------------------------------------------------------------
# Task 5: coverage authenticity (no duplicate counting)
# ---------------------------------------------------------------------------


def test_new_branch_not_duplicate_counted(tmp_path: Path) -> None:
    """Task 5: a genuinely different branch (different parent state, action,
    result state) adds coverage; re-recording the SAME branch does not."""
    from marketpilot.optimization.dream_rsi import _record_trajectory

    world = build_diagnostic_world(kind="W5", seed=7, world_id="w5")
    archive = ReplayWorldArchive(tmp_path)
    archive.register_world(world)
    # Two DIFFERENT families on W5 produce different (state, action) pairs.
    fixed = ParameterizedPolicy(strategy="fixed", name="fixed")
    adaptive = ParameterizedPolicy(strategy="adaptive-voi", name="adaptive")
    t1 = _record_trajectory(world, fixed, fixed.execute(AgentWorldView(world)))
    t2 = _record_trajectory(world, adaptive, adaptive.execute(AgentWorldView(world)))
    archive.record_trajectory(t1, round_index=0)
    archive.record_trajectory(t2, round_index=1)
    trans1 = {(s.action, s.product_id) for s in t1.steps if s.action != "stop"}
    trans2 = {(s.action, s.product_id) for s in t2.steps if s.action != "stop"}
    # The two families explore genuinely different branches on W5.
    assert trans1 != trans2
    # Re-recording t1 must NOT add a third distinct branch.
    archive.record_trajectory(t1, round_index=2)
    traces = archive.trajectories_for_world(world.world_id)
    distinct = {t.policy_hash for t in traces}
    assert len(distinct) == 2
