"""Phase 3: candidate frontier metrics tests (offline, deterministic)."""

from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from marketpilot.policy.frontier import (
    BranchResult,
    compute_frontier_metrics,
    ranking_overlap,
    write_frontier_report,
)
from marketpilot.world.core import (
    AgentWorldView,
    DeterministicPolicy,
    ResearchAction,
    WorldOracle,
    build_minimal_world,
)


def _pid(world, label: str) -> str:
    for product in world.products:
        if label == "good" and product.true_utility > 0.6:
            return product.product_id
        if label == "bad" and product.true_utility <= 0.6:
            return product.product_id
    raise AssertionError(f"no {label} product in world")


def _branches(world, n: int) -> list[BranchResult]:
    """Build n branch rankings over the minimal world using the deterministic
    policy with different action sets (simulating multi-branch exploration)."""
    product_ids = [p.product_id for p in world.products]
    action_sets = [
        (ResearchAction.SEARCH_MARGIN, ResearchAction.SEARCH_DEMAND),
        (ResearchAction.SEARCH_DEMAND, ResearchAction.SEARCH_RISK),
        (ResearchAction.SEARCH_MARGIN, ResearchAction.SEARCH_RISK),
        (ResearchAction.SEARCH_MARKET, ResearchAction.SEARCH_DEMAND),
        (ResearchAction.SEARCH_MARGIN, ResearchAction.SEARCH_COMPETITION),
        (ResearchAction.SEARCH_DEMAND, ResearchAction.SEARCH_COMPETITION),
        (ResearchAction.SEARCH_RISK, ResearchAction.SEARCH_COMPETITION),
        (ResearchAction.SEARCH_MARGIN, ResearchAction.SEARCH_MARKET),
    ]
    branches: list[BranchResult] = []
    for index, actions in enumerate(action_sets[:n]):
        result = DeterministicPolicy(actions).run(AgentWorldView(world))
        selected = result["selected_id"]
        ranking = [UUID(selected)]
        others = [pid for pid in product_ids if pid != selected]
        ranking.append(UUID(others[0]))
        branches.append(
            BranchResult(
                branch_id=f"branch-{index}",
                policy="+".join(action.value for action in actions),
                ranking=ranking,
                input_tokens=100 + index,
                output_tokens=50,
                tool_calls=2,
                latency_ms=10 * index,
            )
        )
    return branches


def test_frontier_prefix_semantics() -> None:
    world = build_minimal_world(seed=7)
    good = _pid(world, "good")
    metrics = compute_frontier_metrics(world, _branches(world, 4), task_key="minimal-dev")
    assert metrics.global_best_id == good
    assert metrics.frontier_regret(1) == 0.0  # first branch already picks good
    assert metrics.summary()["tokens_n2"] == 100 + 101 + 100


def test_frontier_headroom_never_negative_prefix() -> None:
    world = build_minimal_world(seed=7)
    metrics = compute_frontier_metrics(world, _branches(world, 8), task_key="minimal-dev")
    for n in (2, 4, 8):
        assert metrics.headroom(n) >= -1e-9


def test_frontier_report_written(tmp_path: Path) -> None:
    world = build_minimal_world(seed=7)
    metrics = compute_frontier_metrics(world, _branches(world, 4), task_key="minimal-dev")
    write_frontier_report([metrics], tmp_path)
    assert (tmp_path / "frontier_report.json").exists()
    assert (tmp_path / "frontier_report.csv").exists()
    report = __import__("json").loads(
        (tmp_path / "frontier_report.json").read_text(encoding="utf-8")
    )
    assert report[0]["summary"]["task_key"] == "minimal-dev"
    assert "frontier_regret_n4" in report[0]["summary"]


def test_ranking_overlap() -> None:
    a = [uuid5(NAMESPACE_URL, "x"), uuid5(NAMESPACE_URL, "y")]
    b = [uuid5(NAMESPACE_URL, "x"), uuid5(NAMESPACE_URL, "z")]
    assert ranking_overlap(a, b) == 1 / 3


def test_frontier_metrics_do_not_expose_oracle_to_agent() -> None:
    """The frontier metrics are computed by the evaluator; the agent world view
    never carries utility."""
    world = build_minimal_world(seed=7)
    view = AgentWorldView(world)
    assert "true_utility" not in str(view.candidates())
    oracle = WorldOracle(world)
    assert oracle.best_utility() > 0.0
