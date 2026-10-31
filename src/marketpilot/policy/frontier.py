"""Phase 3: candidate generation and candidate frontier (offline core).

The V2 spec: candidate generation via real LLM multi-branch exploration with
prefix semantics (N=1,2,4,8), measuring candidate quality, headroom, tokens,
tool calls, and latency. The audit's gating fact from v1 Step 5B/5D.2 is that
candidate generation (not selection) is the bottleneck, so this phase builds
the exploration harness BEFORE any selector or RSI training.

This module is fully offline/deterministic: it computes candidate frontiers,
headroom, prefix pools, and overlap metrics from rankings. The LLM branch
itself (real provider) is wired in `marketpilot.benchmark.llm_decision`
already; this module adds the frontier/headroom accounting on top.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path
    from uuid import UUID

from marketpilot.world.core import World, WorldOracle


@dataclass(frozen=True)
class BranchResult:
    """One research branch: a ranking plus measured cost/latency."""

    branch_id: str
    policy: str
    ranking: list[UUID]
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: int = 0
    latency_ms: int = 0


@dataclass
class FrontierMetrics:
    """Candidate frontier accounting for a task."""

    task_key: str
    category: str
    difficulty: str
    n_values: tuple[int, ...] = (1, 2, 4, 8)
    branches: list[BranchResult] = field(default_factory=list)
    oracle_utilities: dict[str, float] = field(default_factory=dict)
    global_best_id: str | None = None
    global_best_utility: float = 0.0

    def _pool(self, n: int) -> list[UUID]:
        """Prefix semantics: only the first n branches contribute."""
        seen: set[UUID] = set()
        pool: list[UUID] = []
        for branch in self.branches[:n]:
            for candidate_id in branch.ranking[:2]:  # top-k per branch = 2
                if candidate_id not in seen:
                    seen.add(candidate_id)
                    pool.append(candidate_id)
        return pool

    def frontier_regret(self, n: int) -> float:
        """Best available utility minus best utility in the n-branch pool."""
        pool = self._pool(n)
        if not pool:
            return self.global_best_utility
        best_in_pool = max(
            (self.oracle_utilities.get(str(item), 0.0) for item in pool), default=0.0
        )
        return self.global_best_utility - best_in_pool

    def headroom(self, n: int) -> float:
        """Gain from going from n-1 to n branches (prefix semantics)."""
        if n <= 1:
            return self.global_best_utility - self.frontier_regret(1) - (
                self.global_best_utility - self.frontier_regret(1)
            )
        return self.frontier_regret(n - 1) - self.frontier_regret(n)

    def token_cost(self, n: int) -> int:
        return sum(
            branch.input_tokens + branch.output_tokens for branch in self.branches[:n]
        )

    def tool_calls(self, n: int) -> int:
        return sum(branch.tool_calls for branch in self.branches[:n])

    def latency(self, n: int) -> int:
        return sum(branch.latency_ms for branch in self.branches[:n])

    def summary(self) -> dict[str, Any]:
        rows: dict[str, Any] = {
            "task_key": self.task_key,
            "category": self.category,
            "difficulty": self.difficulty,
            "global_best_utility": round(self.global_best_utility, 4),
            "global_best_id": self.global_best_id,
            "branch_count": len(self.branches),
        }
        for n in self.n_values:
            if n > len(self.branches):
                continue
            rows[f"frontier_regret_n{n}"] = round(self.frontier_regret(n), 4)
            rows[f"headroom_n{n}"] = round(self.headroom(n), 4)
            rows[f"tokens_n{n}"] = self.token_cost(n)
            rows[f"tool_calls_n{n}"] = self.tool_calls(n)
            rows[f"latency_ms_n{n}"] = self.latency(n)
        return rows

    def to_json(self) -> dict[str, Any]:
        return {
            "summary": self.summary(),
            "branches": [
                {
                    "branch_id": b.branch_id,
                    "policy": b.policy,
                    "ranking": [str(item) for item in b.ranking],
                    "input_tokens": b.input_tokens,
                    "output_tokens": b.output_tokens,
                    "tool_calls": b.tool_calls,
                    "latency_ms": b.latency_ms,
                }
                for b in self.branches
            ],
        }


def compute_frontier_metrics(
    world: World,
    branches: list[BranchResult],
    *,
    task_key: str,
    n_values: tuple[int, ...] = (1, 2, 4, 8),
) -> FrontierMetrics:
    """Compute candidate frontier / headroom / cost metrics for one task.

    Oracle utilities come from WorldOracle (hidden truth) — this is an
    EVALUATOR-ONLY function; research policies never call it.
    """
    oracle = WorldOracle(world)
    utilities: dict[str, float] = {}
    for product in world.products:
        utilities[product.product_id] = oracle.true_utility(product.product_id)
    best_id = oracle.best_product_id()
    best_utility = oracle.best_utility()
    return FrontierMetrics(
        task_key=task_key,
        category=world.world_id,
        difficulty=world.difficulty.value,
        n_values=n_values,
        branches=branches,
        oracle_utilities=utilities,
        global_best_id=best_id,
        global_best_utility=best_utility,
    )


def write_frontier_report(metrics: list[FrontierMetrics], output_dir: Path) -> None:
    """Write the candidate-frontier report (JSON + CSV)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "frontier_report.json").write_text(
        json.dumps([m.to_json() for m in metrics], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    if metrics:
        summaries = [m.summary() for m in metrics]
        with (output_dir / "frontier_report.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(summaries[0].keys()))
            writer.writeheader()
            writer.writerows(summaries)


def ranking_overlap(left: list[UUID], right: list[UUID]) -> float:
    """Jaccard overlap of top-5 candidate sets between two branch rankings."""
    left_set = {str(item) for item in left[:5]}
    right_set = {str(item) for item in right[:5]}
    union = left_set | right_set
    if not union:
        return 1.0
    return len(left_set & right_set) / len(union)
