"""Zero-API forensic analysis of existing LLM rollout records."""

import csv
import itertools
import json
from pathlib import Path
from typing import Any
from uuid import UUID

from marketpilot.synthetic.environment import SyntheticEnvironment


def _spearman(left: list[float], right: list[float]) -> float:
    if len(left) < 2:
        return 0.0

    def ranks(values: list[float]) -> list[float]:
        order = sorted(range(len(values)), key=lambda index: values[index])
        result = [0.0] * len(values)
        for rank, index in enumerate(order):
            result[index] = float(rank)
        return result

    left_ranks = ranks(left)
    right_ranks = ranks(right)
    left_mean = sum(left_ranks) / len(left_ranks)
    right_mean = sum(right_ranks) / len(right_ranks)
    numerator = sum(
        (a - left_mean) * (b - right_mean) for a, b in zip(left_ranks, right_ranks, strict=False)
    )
    left_var = sum((a - left_mean) ** 2 for a in left_ranks)
    right_var = sum((b - right_mean) ** 2 for b in right_ranks)
    denominator = (left_var * right_var) ** 0.5
    return numerator / denominator if denominator else 0.0


def run_forensics(
    dataset_dir: Path,
    rollout_file: Path,
    output_dir: Path,
    task_meta: dict[str, tuple[str, str]] | None = None,
) -> list[dict[str, Any]]:
    environment = SyntheticEnvironment(dataset_dir)
    records: dict[tuple[str, int], dict[str, Any]] = {}
    for line in rollout_file.read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            records[(record["task_key"], int(record["rollout_index"]))] = record

    task_keys = sorted({key for key, _ in records})
    rows: list[dict[str, Any]] = []
    for task_key in task_keys:
        task_records = [
            records[(task_key, index)] for index in range(4) if (task_key, index) in records
        ]
        if not task_records:
            continue
        if task_meta and task_key in task_meta:
            category, difficulty = task_meta[task_key]
        else:
            category = task_records[0].get("category", "unknown")
            difficulty = task_records[0].get("difficulty", "easy")
        products = environment.observable_products(category, difficulty)
        opportunities = {
            str(product["product_id"]): float(
                str(
                    environment.ground_truth_for(
                        next(
                            product_id
                            for product_id in environment.products
                            if str(product_id) == product["product_id"]
                        )
                    )["latent_opportunity_score"]
                )
            )
            for product in products
        }
        best = max(opportunities.values())
        global_best_id = max(opportunities, key=lambda key: opportunities[key])

        rankings = [[UUID(str(item)) for item in record["ranking"]] for record in task_records]
        pool_n1 = rankings[0][:2]
        pool_n4: list[UUID] = []
        seen: set[UUID] = set()
        for ranking in rankings:
            for item in ranking[:2]:
                if item not in seen:
                    seen.add(item)
                    pool_n4.append(item)

        first_selected = rankings[0][0] if rankings[0] else None
        first_regret = (
            best - opportunities.get(str(first_selected), 0.0) if first_selected else best
        )
        n1_pool_oracle = best - max(
            (opportunities.get(str(item), 0.0) for item in pool_n1), default=0.0
        )
        n4_pool_oracle = best - max(
            (opportunities.get(str(item), 0.0) for item in pool_n4), default=0.0
        )
        global_oracle = 0.0

        global_rank_positions = []
        for ranking in rankings:
            try:
                global_rank_positions.append(ranking.index(UUID(str(global_best_id))) + 1)
            except ValueError:
                global_rank_positions.append(-1)

        pool_utilities = sorted({opportunities.get(str(item), 0.0) for item in pool_n4})
        consecutive_spearman = []
        for left, right in itertools.pairwise(rankings):
            left_map = {str(item): position for position, item in enumerate(left)}
            common = [item for item in left if item in set(right)]
            if len(common) >= 3:
                left_values = [float(left_map[str(item)]) for item in common]
                right_values = [float(right.index(item)) for item in common]
                consecutive_spearman.append(_spearman(left_values, right_values))

        rows.append(
            {
                "task_key": task_key,
                "category": category,
                "difficulty": difficulty,
                "global_candidate_oracle_regret": round(global_oracle, 4),
                "n1_selected_regret": round(first_regret, 4),
                "n1_pool_oracle_regret": round(n1_pool_oracle, 4),
                "n4_pool_oracle_regret": round(n4_pool_oracle, 4),
                "rollout_frontier_gap": round(n1_pool_oracle - n4_pool_oracle, 4),
                "selection_gap": round(first_regret - n1_pool_oracle, 4),
                "observable_universe_gap": round(n4_pool_oracle - global_oracle, 4),
                "global_best_rank_positions": global_rank_positions,
                "pool_size_n4": len(pool_n4),
                "unique_top1": len({str(ranking[0]) for ranking in rankings if ranking}),
                "pool_utility_min": round(min(pool_utilities), 4) if pool_utilities else None,
                "pool_utility_max": round(max(pool_utilities), 4) if pool_utilities else None,
                "mean_ranking_spearman": round(
                    sum(consecutive_spearman) / len(consecutive_spearman), 4
                )
                if consecutive_spearman
                else None,
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "forensics.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    if rows:
        with (output_dir / "forensics.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    return rows
