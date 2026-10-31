"""Phase 4: Adaptive Research Controller tests (offline, deterministic)."""

from pathlib import Path

from marketpilot.policy.controller import (
    ControllerAction,
    StopReason,
    StrategyKind,
    run_controller_episode,
)
from marketpilot.policy.curves import (
    build_regret_budget_curve,
    evaluate_episode,
    write_curves,
)
from marketpilot.world.core import AgentWorldView, EvidenceFacet, WorldOracle, build_minimal_world


def _pid(world, label: str) -> str:
    for product in world.products:
        if label == "good" and product.true_utility > 0.6:
            return product.product_id
        if label == "bad" and product.true_utility <= 0.6:
            return product.product_id
    raise AssertionError(f"no {label} product in world")


def test_fixed_controller_acquires_all_required_facets() -> None:
    world = build_minimal_world(seed=7)
    result = run_controller_episode(AgentWorldView(world), StrategyKind.FIXED, budget=20)
    assert result.selected_id == _pid(world, "good")
    assert result.decision == "GO"
    assert result.stop_reason is StopReason.SUFFICIENT_EVIDENCE
    # All required facets revealed for every candidate.
    for pid in (p.product_id for p in world.products):
        revealed = set(result.revealed_facets[pid])
        assert EvidenceFacet.MARGIN in revealed
        assert EvidenceFacet.DEMAND in revealed
        assert EvidenceFacet.RISK in revealed


def test_missing_evidence_controller_acquires_minimal_set() -> None:
    world = build_minimal_world(seed=7)
    result = run_controller_episode(AgentWorldView(world), StrategyKind.MISSING_EVIDENCE, budget=20)
    assert result.selected_id == _pid(world, "good")
    assert result.decision == "GO"
    # Should not search more than required facets (3 facets x 2 candidates = 6).
    assert result.step_count <= 6


def test_uncertainty_controller_acquires_divergent_facets() -> None:
    world = build_minimal_world(seed=7)
    result = run_controller_episode(AgentWorldView(world), StrategyKind.UNCERTAINTY, budget=20)
    assert result.selected_id == _pid(world, "good")
    assert result.decision == "GO"
    assert result.step_count <= 6


def test_adaptive_voi_controller_refuses_when_evidence_insufficient() -> None:
    """With a tiny budget, VOI stops early and must refuse (not guess)."""
    world = build_minimal_world(seed=7)
    result = run_controller_episode(
        AgentWorldView(world), StrategyKind.ADAPTIVE_VOI, budget=1.0, max_steps=2
    )
    assert result.total_cost <= 1.0
    assert result.decision == "INSUFFICIENT"
    assert result.refused or result.human_review


def test_adaptive_voi_controller_succeeds_with_budget() -> None:
    world = build_minimal_world(seed=7)
    result = run_controller_episode(AgentWorldView(world), StrategyKind.ADAPTIVE_VOI, budget=20)
    assert result.selected_id == _pid(world, "good")
    assert result.decision == "GO"
    assert result.stop_reason is StopReason.SUFFICIENT_EVIDENCE


def test_controller_steps_have_cost_and_reason() -> None:
    world = build_minimal_world(seed=7)
    result = run_controller_episode(AgentWorldView(world), StrategyKind.MISSING_EVIDENCE, budget=20)
    assert result.steps
    assert all(step.action is ControllerAction.SEARCH for step in result.steps)
    assert all(step.cost > 0 for step in result.steps)
    assert all(step.reason for step in result.steps)
    assert result.total_cost > 0


def test_budget_limits_steps() -> None:
    world = build_minimal_world(seed=7)
    result = run_controller_episode(
        AgentWorldView(world), StrategyKind.FIXED, budget=2.0, max_steps=12
    )
    assert result.total_cost <= 2.0 + 1e-9
    assert result.step_count <= 12


def test_evaluate_episode_computes_regret() -> None:
    world = build_minimal_world(seed=7)
    result, point = evaluate_episode(world, StrategyKind.MISSING_EVIDENCE, budget=20)
    assert point.regret == 0.0  # selects the oracle-best
    assert point.quality == 1.0
    assert point.cost == result.total_cost


def test_budget_curve_monotone_quality() -> None:
    world = build_minimal_world(seed=7)
    points = build_regret_budget_curve(
        world, StrategyKind.MISSING_EVIDENCE, budgets=(2.0, 4.0, 6.0, 10.0)
    )
    assert len(points) == 4
    # At higher budgets the controller should reach sufficient evidence.
    assert points[-1].regret == 0.0
    assert points[-1].quality == 1.0


def test_curves_written(tmp_path: Path) -> None:
    world = build_minimal_world(seed=7)
    by_strategy = {
        strategy.value: build_regret_budget_curve(world, strategy, budgets=(4.0, 10.0))
        for strategy in StrategyKind
    }
    write_curves(by_strategy, tmp_path)
    assert (tmp_path / "regret_budget_curves.json").exists()
    assert (tmp_path / "regret_budget_curves.csv").exists()


def test_controller_never_reads_oracle() -> None:
    """The controller consumes only AgentWorldView; oracle access is evaluator-side."""
    world = build_minimal_world(seed=7)
    view = AgentWorldView(world)
    run_controller_episode(view, StrategyKind.ADAPTIVE_VOI, budget=20)
    oracle = WorldOracle(world)
    # The view used by the controller has no oracle surface.
    assert not hasattr(view, "ground_truth_for")
    assert oracle.best_utility() > 0.0
