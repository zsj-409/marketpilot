"""Phase 4: Regret-Budget and Quality-Cost curve generation (evaluator-side).

The controller itself never reads oracle truth. These curves are computed by
the EVALUATOR after an episode: regret is oracle regret of the selected
candidate; cost is the controller's spent budget; quality is decision quality
(correct GO/NO_GO vs oracle viability).
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from marketpilot.policy.controller import ControllerResult, StrategyKind, run_controller_episode
from marketpilot.world.core import AgentWorldView, World, WorldOracle


@dataclass
class CurvePoint:
    budget: float
    regret: float
    cost: float
    quality: float
    decision: str
    refused: bool
    human_review: bool


def evaluate_episode(
    world: World,
    strategy: StrategyKind,
    *,
    budget: float,
    max_steps: int = 12,
) -> tuple[ControllerResult, CurvePoint]:
    """Run one episode on a fresh view and compute oracle-based metrics."""
    view = AgentWorldView(world)
    oracle = WorldOracle(world)
    result = run_controller_episode(view, strategy, budget=budget, max_steps=max_steps)
    selected = result.selected_id
    regret = oracle.regret(selected) if selected else oracle.best_utility()
    # Quality: 1.0 if the selected candidate is the oracle-best (viable+max
    # utility); 0.0 otherwise; 0.5 for refuse/human-review (no claim).
    if result.refused or result.human_review:
        quality = 0.5
    elif selected is not None and selected == oracle.best_product_id():
        quality = 1.0
    else:
        quality = 0.0
    point = CurvePoint(
        budget=budget,
        regret=round(regret, 4),
        cost=round(result.total_cost, 4),
        quality=round(quality, 4),
        decision=result.decision,
        refused=result.refused,
        human_review=result.human_review,
    )
    return result, point


def build_regret_budget_curve(
    world: World,
    strategy: StrategyKind,
    *,
    budgets: tuple[float, ...] = (2.0, 4.0, 6.0, 8.0, 10.0),
    max_steps: int = 12,
) -> list[CurvePoint]:
    """Run the same strategy at increasing budgets and record regret/cost."""
    points: list[CurvePoint] = []
    for budget in budgets:
        _result, point = evaluate_episode(world, strategy, budget=budget, max_steps=max_steps)
        points.append(point)
    return points


def write_curves(points_by_strategy: dict[str, list[CurvePoint]], output_dir: Path) -> None:
    """Write Regret-Budget / Quality-Cost curves for all strategies."""
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        strategy: [
            {
                "budget": p.budget,
                "regret": p.regret,
                "cost": p.cost,
                "quality": p.quality,
                "decision": p.decision,
                "refused": p.refused,
                "human_review": p.human_review,
            }
            for p in points
        ]
        for strategy, points in points_by_strategy.items()
    }
    (output_dir / "regret_budget_curves.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    rows: list[dict[str, object]] = []
    for strategy, points in points_by_strategy.items():
        for point in points:
            rows.append(
                {
                    "strategy": strategy,
                    "budget": point.budget,
                    "regret": point.regret,
                    "cost": point.cost,
                    "quality": point.quality,
                    "decision": point.decision,
                    "refused": point.refused,
                    "human_review": point.human_review,
                }
            )
    if rows:
        with (output_dir / "regret_budget_curves.csv").open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
