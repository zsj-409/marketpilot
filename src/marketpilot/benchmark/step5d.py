"""Step 5D policy-diverse research scaling gate."""

import csv
import json
import time
from pathlib import Path
from typing import Any
from uuid import UUID

from marketpilot.benchmark.llm_decision import LLMCandidateRanker
from marketpilot.config import MarketPilotSettings
from marketpilot.synthetic.environment import SyntheticEnvironment
from marketpilot.synthetic.providers import SyntheticSearchProviderV2

POLICIES = ("static-ranking", "constraint-first", "evidence-gap-first", "risk-first")


def build_pool(rankings: list[list[UUID]], top_k: int = 2) -> list[UUID]:
    seen: set[UUID] = set()
    pool: list[UUID] = []
    for ranking in rankings:
        for item in ranking[:top_k]:
            if item not in seen:
                seen.add(item)
                pool.append(item)
    return pool


async def run_policy_diverse_gate(
    settings: MarketPilotSettings,
    dataset_dir: Path,
    output_dir: Path,
    tasks: list[tuple[str, str, str]],
) -> list[dict[str, Any]]:
    environment = SyntheticEnvironment(dataset_dir)
    v2_sources = [
        json.loads(line)
        for line in (dataset_dir / "sources_v2.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    ranker = LLMCandidateRanker(settings, temperature=settings.llm_temperature)
    records = []
    summaries = []
    for task_key, category, difficulty in tasks:
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
        sources = [source for source in v2_sources if source.get("category") == category]
        search_provider = SyntheticSearchProviderV2(sources)
        branch_rankings: dict[str, list[UUID]] = {}
        branch_metrics: dict[str, dict[str, Any]] = {}
        branch_evidence: dict[str, str] = {}
        for policy in POLICIES:
            started = time.perf_counter()
            ranking, metrics, evidence = await ranker.rank_research(
                category, products, policy, sources, search_provider=search_provider
            )
            trajectory_wall_ms = round((time.perf_counter() - started) * 1000, 2)
            metrics = {**metrics, "trajectory_wall_latency_ms": trajectory_wall_ms}
            records.append(
                {
                    "task_key": task_key,
                    "category": category,
                    "difficulty": difficulty,
                    "policy": policy,
                    "ranking": [str(item) for item in ranking],
                    "metrics": metrics,
                    "trajectory_wall_latency_ms": trajectory_wall_ms,
                    "evidence": evidence,
                }
            )
            branch_rankings[policy] = ranking
            branch_metrics[policy] = metrics
            branch_evidence[policy] = evidence

        policy_pool = build_pool([branch_rankings[p] for p in POLICIES], top_k=2)
        policy_frontier = max(
            (opportunities.get(str(item), 0.0) for item in policy_pool), default=0.0
        )
        policy_regret = best - policy_frontier
        oracle_ranks = {}
        for policy in POLICIES:
            ranking = branch_rankings[policy]
            try:
                oracle_ranks[policy] = ranking.index(UUID(str(global_best_id))) + 1
            except ValueError:
                oracle_ranks[policy] = -1
        summaries.append(
            {
                "task_key": task_key,
                "category": category,
                "difficulty": difficulty,
                "policy_diverse_n4_regret": round(policy_regret, 4),
                "policy_diverse_frontier_utility": round(policy_frontier, 4),
                "oracle_ranks": oracle_ranks,
                "pool_size": len(policy_pool),
                "evidence_overlap": round(_evidence_overlap(branch_evidence), 4),
                "total_tokens": sum(
                    metrics["input_tokens"] + metrics["output_tokens"]
                    for metrics in branch_metrics.values()
                ),
                "llm_calls": len(branch_metrics),
                "trajectory_wall_latency_ms": sum(
                    metrics.get("trajectory_wall_latency_ms", 0.0)
                    for metrics in branch_metrics.values()
                ),
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "step5d_branch_records.jsonl").write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )
    (output_dir / "step5d_summary.json").write_text(
        json.dumps(summaries, indent=2), encoding="utf-8"
    )
    if summaries:
        with (output_dir / "step5d_summary.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(summaries[0].keys()))
            writer.writeheader()
            writer.writerows(summaries)
    return summaries


def _evidence_overlap(evidence: dict[str, str]) -> float:
    values = [set(text.split()) for text in evidence.values() if text]
    if len(values) < 2:
        return 0.0
    intersections = [
        len(left & right) / max(len(left | right), 1)
        for index, left in enumerate(values)
        for right in values[index + 1 :]
    ]
    return round(sum(intersections) / len(intersections), 4)
