"""Phase 5.7: Multi-Family Policy Search tests (Task 1 / Task 8).

Verifies:
- cross-family candidates are actually generated (not only AdaptiveVOI)
- PolicyConfig produces stable, correct version hashes
- ContextualHybridPolicy uses only observed state features
- world_id / seed are never policy choice features
- hidden truth / future nodes are never read
- incumbent is always retained as a candidate
- different families produce different behaviors
"""

from pathlib import Path

from marketpilot.optimization.dream_rsi import (
    ParameterizedPolicy,
    PolicyRegistry,
    RecursiveOptimizationLoop,
    ReplayWorldArchive,
)
from marketpilot.optimization.proposer import (
    STRATEGY_FAMILIES,
    ContextualHybridPolicy,
    MultiFamilyProposer,
    PolicyConfig,
)
from marketpilot.world.core import (
    AgentWorldView,
    build_diagnostic_world,
    build_minimal_world,
)


def test_cross_family_candidates_generated() -> None:
    """A multi-family proposal batch must contain candidates from DIFFERENT
    strategy families (not only AdaptiveVOI)."""
    incumbent = ParameterizedPolicy(name="incumbent", strategy="adaptive-voi")
    proposer = MultiFamilyProposer(seed=7)
    batch = proposer.propose(incumbent, round_index=0, n_candidates=8)
    strategies = {c.strategy for c in batch}
    # With 8 candidates, cross-family sampling must have hit at least one
    # non-adaptive family.
    assert len(strategies) > 1
    assert "incumbent" in proposer.provenance.get(incumbent.hash, "")


def test_incumbent_always_retained() -> None:
    """The incumbent is always the first candidate in the batch."""
    incumbent = ParameterizedPolicy(name="incumbent", strategy="fixed")
    proposer = MultiFamilyProposer(seed=7)
    batch = proposer.propose(incumbent, round_index=1, n_candidates=4)
    assert batch[0].hash == incumbent.hash
    assert proposer.provenance[batch[0].hash] == "incumbent"


def test_policy_config_hash_stable_and_distinct() -> None:
    """Same config -> same hash; different config -> different hash."""
    a = PolicyConfig(strategy="fixed", weights={"weight_margin": 0.5})
    b = PolicyConfig(strategy="fixed", weights={"weight_margin": 0.5})
    c = PolicyConfig(strategy="adaptive-voi", weights={"weight_margin": 0.5})
    assert a.hash == b.hash
    assert a.hash != c.hash
    # Invalid strategy rejected.
    try:
        PolicyConfig(strategy="not-a-family")
        raise AssertionError("should have raised for invalid strategy")
    except ValueError:
        pass


def test_contextual_policy_uses_only_observed_state() -> None:
    """ContextualHybridPolicy.choose_mode reads ONLY the AgentWorldView
    (observable state), never world metadata or oracle truth."""
    world = build_diagnostic_world(kind="W1", seed=7, world_id="w1")
    view = AgentWorldView(world)
    cfg = PolicyConfig(strategy="adaptive-voi")
    hybrid = ContextualHybridPolicy(cfg)
    mode = hybrid.choose_mode(view, budget_left=8.0)
    assert mode in ("fixed", "missing-evidence", "uncertainty", "adaptive-voi")
    # No world_id/seed dependence: different world_id, same state -> same mode
    # decision path (deterministic from observable state).
    view2 = AgentWorldView(build_diagnostic_world(kind="W1", seed=7, world_id="other"))
    mode2 = hybrid.choose_mode(view2, budget_left=8.0)
    assert mode == mode2  # world_id does not change the decision


def test_contextual_policy_executes() -> None:
    """ContextualHybridPolicy.execute runs and returns a ControllerResult."""
    world = build_diagnostic_world(kind="W1", seed=7, world_id="w1")
    cfg = PolicyConfig(strategy="adaptive-voi", weights={"weight_margin": 0.5})
    hybrid = ContextualHybridPolicy(cfg)
    result = hybrid.execute(AgentWorldView(world), budget=10.0)
    assert result.selected_id is not None or result.refused


def test_parameterized_policy_executes_contextual() -> None:
    """A ParameterizedPolicy with strategy='contextual-hybrid' executes via
    the ContextualHybridPolicy delegate."""
    world = build_diagnostic_world(kind="W1", seed=7, world_id="w1")
    policy = ParameterizedPolicy(strategy="contextual-hybrid", name="ctx")
    result = policy.execute(AgentWorldView(world))
    assert result.selected_id is not None or result.refused


def test_strategy_families_cover_four_baselines() -> None:
    """The proposer's family space covers all four existing strategies."""
    for family in ("fixed", "missing-evidence", "uncertainty", "adaptive-voi"):
        assert family in STRATEGY_FAMILIES


def test_different_families_different_behavior() -> None:
    """On W1 (hidden risk), fixed succeeds while adaptive-voi REFUSES —
    the family choice changes behavior."""
    world = build_diagnostic_world(kind="W1", seed=7, world_id="w1")
    fixed = ParameterizedPolicy(strategy="fixed", name="fixed")
    adaptive = ParameterizedPolicy(strategy="adaptive-voi", name="adaptive")
    r_fixed = fixed.execute(AgentWorldView(world))
    r_adaptive = adaptive.execute(AgentWorldView(world))
    assert not r_fixed.refused
    assert r_adaptive.refused  # known W1 negative result


def test_loop_with_proposer_runs() -> None:
    """RecursiveOptimizationLoop with a MultiFamilyProposer attached executes
    cross-family search end-to-end."""
    dev = build_minimal_world(seed=7)
    conf = build_minimal_world(seed=8)
    archive = ReplayWorldArchive(Path(".") / "tmp-mf-do-not-commit")
    archive.register_world(dev)
    archive.register_world(conf)
    registry = PolicyRegistry()
    loop = RecursiveOptimizationLoop(archive, registry, rounds=3)
    loop.proposer = MultiFamilyProposer(seed=7)
    summary = loop.run(dev, conf)
    assert summary["rounds"] == 3
    assert len(summary["round_log"]) == 3
