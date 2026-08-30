"""Low-cost resumable DEV candidate-headroom gate for Step 5B."""

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from marketpilot.benchmark.llm_decision import LLMCandidateRanker
from marketpilot.config import MarketPilotSettings
from marketpilot.synthetic.environment import SyntheticEnvironment


@dataclass(frozen=True)
class PoolConfig:
    model: str
    base_url: str | None
    temperature: float
    top_k_per_rollout: int
    max_rollouts: int

    def hash(self) -> str:
        payload = json.dumps(
            {
                "model": self.model,
                "base_url": self.base_url or "",
                "temperature": self.temperature,
                "top_k_per_rollout": self.top_k_per_rollout,
                "max_rollouts": self.max_rollouts,
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


@dataclass(frozen=True)
class PilotTask:
    task_key: str
    category: str
    difficulty: str


def build_pool(
    rankings: list[list[UUID]],
    top_k: int,
) -> list[UUID]:
    """Return the deduplicated union of the first top-k IDs per rollout."""

    ordered: list[UUID] = []
    seen: set[UUID] = set()
    for ranking in rankings:
        for candidate_id in ranking[:top_k]:
            if candidate_id not in seen:
                seen.add(candidate_id)
                ordered.append(candidate_id)
    return ordered


class ResumablePilotStore:
    """Append-only rollout persistence keyed by task, rollout, and config."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._records: dict[tuple[str, int, str], dict[str, Any]] = {}
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    record = json.loads(line)
                    self._records[
                        (record["task_key"], int(record["rollout_index"]), record["config_hash"])
                    ] = record

    def get(self, task_key: str, rollout_index: int, config_hash: str) -> dict[str, Any] | None:
        return self._records.get((task_key, rollout_index, config_hash))

    def put(self, record: dict[str, Any]) -> None:
        key = (record["task_key"], int(record["rollout_index"]), record["config_hash"])
        self._records[key] = record
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


async def run_pool_gate(
    settings: MarketPilotSettings,
    dataset_dir: Path,
    output_dir: Path,
    tasks: list[PilotTask],
    *,
    top_k_per_rollout: int = 2,
    max_rollouts: int = 4,
) -> list[dict[str, Any]]:
    config = PoolConfig(
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        temperature=settings.llm_temperature,
        top_k_per_rollout=top_k_per_rollout,
        max_rollouts=max_rollouts,
    )
    config_hash = config.hash()
    store = ResumablePilotStore(output_dir / "rollout_records.jsonl")
    environment = SyntheticEnvironment(dataset_dir)
    ranker = LLMCandidateRanker(settings, temperature=settings.llm_temperature)
    summaries: list[dict[str, Any]] = []

    for task in tasks:
        products = environment.observable_products(task.category, task.difficulty)
        rankings: list[list[UUID]] = []
        call_metrics: list[dict[str, Any]] = []
        for rollout_index in range(max_rollouts):
            cached = store.get(task.task_key, rollout_index, config_hash)
            if cached is not None:
                rankings.append([UUID(str(item)) for item in cached["ranking"]])
                call_metrics.append(cached["metrics"])
                continue
            ranking, metrics = await ranker.rank(task.category, products)
            store.put(
                {
                    "task_key": task.task_key,
                    "rollout_index": rollout_index,
                    "config_hash": config_hash,
                    "ranking": [str(item) for item in ranking],
                    "metrics": metrics,
                }
            )
            rankings.append(ranking)
            call_metrics.append(metrics)

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

        first_rankings = rankings[0]
        first = first_rankings[0] if first_rankings else None
        first_regret = best - opportunities.get(str(first), 0.0) if first else best

        n1_pool = build_pool(rankings[:1], top_k_per_rollout)
        n2_pool = build_pool(rankings[:2], top_k_per_rollout)
        n4_pool = build_pool(rankings[:4], top_k_per_rollout)

        n1_oracle = (
            best - max(opportunities.get(str(item), 0.0) for item in n1_pool) if n1_pool else best
        )
        n2_oracle = (
            best - max(opportunities.get(str(item), 0.0) for item in n2_pool) if n2_pool else best
        )
        n4_oracle = (
            best - max(opportunities.get(str(item), 0.0) for item in n4_pool) if n4_pool else best
        )

        unique_top1 = len({str(ranking[0]) for ranking in rankings if ranking})
        top1_sequence = [str(ranking[0]) for ranking in rankings if ranking]
        disagreement = (
            1.0 - (len(set(top1_sequence)) / len(top1_sequence)) if top1_sequence else 0.0
        )
        summaries.append(
            {
                "task_key": task.task_key,
                "category": task.category,
                "difficulty": task.difficulty,
                "n1_first_regret": round(first_regret, 4),
                "n1_oracle_regret": round(n1_oracle, 4),
                "n2_oracle_regret": round(n2_oracle, 4),
                "n4_oracle_regret": round(n4_oracle, 4),
                "oracle_gain_n4_vs_n1": round(n1_oracle - n4_oracle, 4),
                "unique_top1": unique_top1,
                "candidate_pool_size_n4": len(n4_pool),
                "ranking_disagreement": round(disagreement, 4),
                "llm_calls": len(call_metrics),
                "input_tokens": sum(metrics["input_tokens"] for metrics in call_metrics),
                "output_tokens": sum(metrics["output_tokens"] for metrics in call_metrics),
                "total_tokens": sum(
                    metrics["input_tokens"] + metrics["output_tokens"] for metrics in call_metrics
                ),
                "latency_ms": sum(metrics["latency_ms"] for metrics in call_metrics),
            }
        )
    return summaries


def write_summaries(summaries: list[dict[str, Any]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "candidate_pool_diagnostics.json").write_text(
        json.dumps(summaries, indent=2), encoding="utf-8"
    )
    if summaries:
        with (output_dir / "candidate_pool_diagnostics.csv").open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=list(summaries[0].keys()))
            writer.writeheader()
            writer.writerows(summaries)
