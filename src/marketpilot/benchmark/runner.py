"""Deterministic benchmark runner."""

import csv
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from marketpilot.benchmark.evaluation import evaluate_selection
from marketpilot.benchmark.loader import load_benchmark_suite
from marketpilot.benchmark.models import (
    BenchmarkResult,
    BenchmarkTask,
    ExperimentManifest,
    FailureCategory,
)
from marketpilot.benchmark.strategies import ResearchStrategy, strategy_for
from marketpilot.synthetic.environment import SyntheticEnvironment
from marketpilot.verifier.verifier import verify_recommendation


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


class BenchmarkRunner:
    """Run a strategy over a synthetic benchmark suite."""

    def __init__(
        self,
        *,
        datasets_dir: Path,
        output_dir: Path,
        suite_name: str,
        strategy_name: str,
        n: int = 1,
        seed: int = 42,
        provider: str = "mock",
        model: str = "synthetic-baseline",
    ) -> None:
        self.datasets_dir = datasets_dir
        self.output_dir = output_dir
        self.suite_name = suite_name
        self.strategy_name = strategy_name
        self.n = n
        self.seed = seed
        self.provider = provider
        self.model = model

    def run(self) -> tuple[ExperimentManifest, list[BenchmarkResult], dict[str, object]]:
        suite = load_benchmark_suite(self.suite_name, self.datasets_dir)
        dataset_dir = self.datasets_dir / "synthetic-market-v1"
        environment = SyntheticEnvironment(dataset_dir)
        strategy = strategy_for(self.strategy_name, n=self.n, seed=self.seed)
        results = [self._run_task(task, strategy, environment) for task in suite.tasks]
        metrics = self._aggregate(results)
        experiment_id = str(uuid4())
        manifest = ExperimentManifest(
            experiment_id=experiment_id,
            name=f"{self.suite_name}-{self.strategy_name}",
            git_commit=_git_commit(),
            dataset="synthetic-market-v1",
            dataset_version="v1",
            generator_version="1.0.0",
            seed=self.seed,
            benchmark_suite=self.suite_name,
            strategy=self.strategy_name,
            model=self.model,
            provider=self.provider,
            completed_at=datetime.now(UTC),
        )
        self._write_artifacts(experiment_id, manifest, results, metrics)
        return manifest, results, metrics

    def _run_task(
        self,
        task: BenchmarkTask,
        strategy: ResearchStrategy,
        environment: SyntheticEnvironment,
    ) -> BenchmarkResult:
        selected = strategy.select(task.category, task.constraints, environment, task.difficulty)
        evaluation = evaluate_selection(environment, task.category, selected, task.constraints)
        if not evaluation:
            return BenchmarkResult(
                task_key=task.task_key,
                family=task.family,
                category=task.category,
                strategy=strategy.name,
                status="FAILED",
                failure=FailureCategory.INSUFFICIENT_EVIDENCE,
            )

        verifier_score = 0.0
        if selected:
            products = environment.observable_products(task.category)
            product = next((p for p in products if p["product_id"] == str(selected[0])), None)
            if product is not None:
                sources = environment.sources_for_category(task.category)
                domains = len({source.get("url", "") for source in sources})
                verifier_score = verify_recommendation(
                    product=product,
                    constraints=task.constraints,
                    evidence_count=1 if sources else 0,
                    snapshot_count=1 if sources else 0,
                    distinct_domains=domains,
                    risk_covered=True,
                ).score.total

        failure = None
        if not evaluation.get("constraint_satisfied", False):
            failure = FailureCategory.CONSTRAINT_VIOLATION
        elif not selected:
            failure = FailureCategory.INSUFFICIENT_EVIDENCE

        tool_calls = {
            "baseline": 1,
            "best-of-n": self.n,
            "verifier-best-of-n": self.n,
            "adaptive-planner": 2 if task.difficulty == "hard" else 1,
            "episodic-memory": 2,
            "skill-memory": 2,
        }.get(strategy.name, 1)

        return BenchmarkResult(
            task_key=task.task_key,
            family=task.family,
            difficulty=task.difficulty,
            category=task.category,
            strategy=strategy.name,
            status="COMPLETED" if failure is None else "FAILED",
            selected_product_id=selected[0] if selected else None,
            best_available_opportunity=float(evaluation["best_available_opportunity"]),
            selected_opportunity=float(evaluation["selected_opportunity"]),
            regret=float(evaluation["regret"]),
            top_k_recall=float(evaluation["top_k_recall"]),
            constraint_satisfied=bool(evaluation["constraint_satisfied"]),
            risk_recall=float(evaluation["risk_recall"]),
            ranking_correlation=float(evaluation["ranking_correlation"]),
            verifier_score=verifier_score,
            tool_calls=tool_calls,
            llm_tokens=0,
            latency_ms=0,
            estimated_cost=0.0,
            failure=failure,
        )

    def _aggregate(self, results: list[BenchmarkResult]) -> dict[str, object]:
        if not results:
            return {}
        completed = [r for r in results if r.status == "COMPLETED"]
        return {
            "task_count": len(results),
            "success_rate": len(completed) / len(results),
            "mean_regret": sum(r.regret for r in results) / len(results),
            "mean_top_k_recall": sum(r.top_k_recall for r in results) / len(results),
            "constraint_satisfaction_rate": sum(r.constraint_satisfied for r in results)
            / len(results),
            "mean_verifier_score": sum(r.verifier_score for r in results) / len(results),
            "mean_risk_recall": sum(r.risk_recall for r in results) / len(results),
            "mean_ranking_correlation": sum(r.ranking_correlation for r in results) / len(results),
            "mean_tool_calls": sum(r.tool_calls for r in results) / len(results),
            "by_difficulty": {
                difficulty: {
                    "mean_regret": sum(
                        r.regret
                        for r in results
                        if r.status == "COMPLETED" and r.difficulty == difficulty
                    )
                    / max(
                        sum(
                            r.status == "COMPLETED" and r.difficulty == difficulty for r in results
                        ),
                        1,
                    ),
                    "mean_top_k_recall": sum(
                        r.top_k_recall
                        for r in results
                        if r.status == "COMPLETED" and r.difficulty == difficulty
                    )
                    / max(
                        sum(
                            r.status == "COMPLETED" and r.difficulty == difficulty for r in results
                        ),
                        1,
                    ),
                }
                for difficulty in ("easy", "medium", "hard")
            },
            "by_family": {
                family: {
                    "task_count": sum(r.family == family for r in results),
                    "mean_regret": sum(r.regret for r in results if r.family == family)
                    / max(sum(r.family == family for r in results), 1),
                    "mean_top_k_recall": sum(r.top_k_recall for r in results if r.family == family)
                    / max(sum(r.family == family for r in results), 1),
                }
                for family in sorted({r.family for r in results})
            },
            "failure_counts": {
                category.value: sum(r.failure is category for r in results)
                for category in FailureCategory
                if sum(r.failure is category for r in results)
            },
        }

    def _write_artifacts(
        self,
        experiment_id: str,
        manifest: ExperimentManifest,
        results: list[BenchmarkResult],
        metrics: dict[str, object],
    ) -> None:
        run_dir = self.output_dir / experiment_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
        with (run_dir / "results.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
            for result in results:
                handle.write(result.model_dump_json() + "\n")
        (run_dir / "results.json").write_text(
            json.dumps([result.model_dump(mode="json") for result in results], indent=2),
            encoding="utf-8",
        )
        with (run_dir / "results.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "task_key",
                    "family",
                    "difficulty",
                    "category",
                    "status",
                    "regret",
                    "top_k_recall",
                    "verifier_score",
                    "tool_calls",
                    "failure",
                ],
            )
            writer.writeheader()
            for result in results:
                writer.writerow(
                    {
                        "task_key": result.task_key,
                        "family": result.family,
                        "difficulty": result.difficulty,
                        "category": result.category,
                        "status": result.status,
                        "regret": result.regret,
                        "top_k_recall": result.top_k_recall,
                        "verifier_score": result.verifier_score,
                        "tool_calls": result.tool_calls,
                        "failure": result.failure.value if result.failure else "",
                    }
                )
        (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        with (run_dir / "failures.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
            for result in results:
                if result.failure is not None:
                    handle.write(
                        json.dumps(
                            {
                                "task_key": result.task_key,
                                "failure": result.failure.value,
                            }
                        )
                        + "\n"
                    )
        from marketpilot.reporting.benchmark_html import render_benchmark_html

        render_benchmark_html(manifest, metrics, results, run_dir / "benchmark.html")
