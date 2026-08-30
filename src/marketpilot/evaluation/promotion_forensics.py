"""Zero-API candidate promotion forensics."""

import csv
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from marketpilot.synthetic.environment import SyntheticEnvironment

FEATURES = (
    "demand_score",
    "gross_margin",
    "differentiation_score",
    "competition_score",
    "risk_score",
    "return_rate",
    "seller_count",
)


class CandidateRankRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    task_key: str
    category: str
    difficulty: str
    policy: str
    candidate_id: str
    rank: int
    display_name: str
    observable_opportunity: float
    components: dict[str, float]


class PromotionForensicsTaskResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    task_key: str
    category: str
    difficulty: str
    policy: str
    oracle_candidate_id: str
    oracle_rank: int
    rank1_candidate_id: str
    rank2_candidate_id: str
    rank2_score: float
    oracle_score: float
    promotion_gap: float
    k_star: int | None
    oracle_regret_k: dict[str, float]
    component_deltas: dict[str, float] = Field(default_factory=dict)


class PromotionForensicsReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    results: list[PromotionForensicsTaskResult]
    branch_union_frontier: dict[str, float] = Field(default_factory=dict)
    candidate_policy_matrix: dict[str, dict[str, int]] = Field(default_factory=dict)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _opportunity(product: dict[str, Any]) -> float:
    return (
        0.35 * float(str(product.get("demand_score", 0.0)))
        + 0.25 * float(str(product.get("gross_margin", 0.0)))
        + 0.20 * float(str(product.get("differentiation_score", 0.0)))
        - 0.15 * float(str(product.get("competition_score", 0.0)))
        - 0.10 * float(str(product.get("risk_score", 0.0)))
    )


def run_promotion_forensics(
    dataset_dir: Path,
    branch_records_file: Path,
    output_dir: Path,
) -> PromotionForensicsReport:
    environment = SyntheticEnvironment(dataset_dir)
    records = _read_jsonl(branch_records_file)
    products = environment.products
    product_observable: dict[str, dict[str, Any]] = {
        str(product_id): {
            "name": product.title,
            "opportunity": _opportunity(
                {
                    key: getattr(product, key, 0.0)
                    for key in (
                        "demand_score",
                        "gross_margin",
                        "differentiation_score",
                        "competition_score",
                        "risk_score",
                        "return_rate",
                        "seller_count",
                    )
                }
            ),
            "components": {key: float(getattr(product, key, 0.0)) for key in FEATURES},
        }
        for product_id, product in products.items()
    }
    opportunities = {
        str(product_id): float(
            str(environment.ground_truth_for(product_id)["latent_opportunity_score"])
        )
        for product_id in products
    }

    results: list[PromotionForensicsTaskResult] = []
    candidate_policy_matrix: dict[str, dict[str, int]] = {}
    union_records: dict[str, list[str]] = {}

    for record in records:
        task_key = record["task_key"]
        policy = record["policy"]
        category = record["category"]
        difficulty = record["difficulty"]
        ranking = [str(item) for item in record["ranking"]]
        category_opportunities = {
            str(product_id): float(
                str(environment.ground_truth_for(product_id)["latent_opportunity_score"])
            )
            for product_id, product in products.items()
            if product.category == category
        }
        oracle_candidate_id = max(
            category_opportunities, key=lambda key: category_opportunities[key]
        )
        union_records.setdefault(task_key, [])
        union_records[task_key].extend(ranking[:10])

        oracle_rank = (
            ranking.index(oracle_candidate_id) + 1 if oracle_candidate_id in ranking else -1
        )
        rank1_id = ranking[0] if ranking else ""
        rank2_id = ranking[1] if len(ranking) > 1 else ""
        rank2 = product_observable.get(rank2_id, {"opportunity": 0.0, "components": {}, "name": ""})
        oracle = product_observable.get(
            oracle_candidate_id, {"opportunity": 0.0, "components": {}, "name": ""}
        )
        rank2_score = rank2["opportunity"]
        oracle_score = oracle["opportunity"]
        promotion_gap = rank2_score - oracle_score
        component_deltas = {
            key: float(oracle["components"].get(key, 0.0))
            - float(rank2["components"].get(key, 0.0))
            for key in FEATURES
        }
        k_values = (1, 2, 3, 4, 5, 8, 10)
        k_star = next((k for k in k_values if oracle_candidate_id in ranking[:k]), None)
        best = max(category_opportunities.values())
        oracle_regret_k = {
            str(k): round(
                best
                - max((category_opportunities.get(item, 0.0) for item in ranking[:k]), default=0.0),
                4,
            )
            for k in k_values
        }

        for rank, candidate_id in enumerate(ranking, start=1):
            candidate_policy_matrix.setdefault(candidate_id, {})
            candidate_policy_matrix[candidate_id][f"{task_key}:{policy}"] = rank

        results.append(
            PromotionForensicsTaskResult(
                task_key=task_key,
                category=category,
                difficulty=difficulty,
                policy=policy,
                oracle_candidate_id=oracle_candidate_id,
                oracle_rank=oracle_rank,
                rank1_candidate_id=rank1_id,
                rank2_candidate_id=rank2_id,
                rank2_score=rank2_score,
                oracle_score=oracle_score,
                promotion_gap=promotion_gap,
                k_star=k_star,
                oracle_regret_k=oracle_regret_k,
                component_deltas=component_deltas,
            )
        )

    branch_union_frontier: dict[str, float] = {}
    for task_key, candidate_ids in union_records.items():
        unique = list(dict.fromkeys(candidate_ids))
        best = max(opportunities.values())
        branch_union_frontier[task_key] = round(
            best - max((opportunities.get(item, 0.0) for item in unique), default=0.0), 4
        )

    report = PromotionForensicsReport(
        results=results,
        branch_union_frontier=branch_union_frontier,
        candidate_policy_matrix=candidate_policy_matrix,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "promotion_forensics.json").write_text(
        report.model_dump_json(indent=2), encoding="utf-8"
    )
    with (output_dir / "promotion_forensics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "task_key",
                "difficulty",
                "policy",
                "oracle_rank",
                "rank1_candidate_id",
                "rank2_candidate_id",
                "rank2_score",
                "oracle_score",
                "promotion_gap",
                "k_star",
            ],
        )
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "task_key": result.task_key,
                    "difficulty": result.difficulty,
                    "policy": result.policy,
                    "oracle_rank": result.oracle_rank,
                    "rank1_candidate_id": result.rank1_candidate_id,
                    "rank2_candidate_id": result.rank2_candidate_id,
                    "rank2_score": result.rank2_score,
                    "oracle_score": result.oracle_score,
                    "promotion_gap": result.promotion_gap,
                    "k_star": result.k_star,
                }
            )
    return report
