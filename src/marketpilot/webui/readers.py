"""Read MarketPilot artifacts (runs, benchmarks, datasets) for the web workbench.

All functions are read-only: they never mutate project artifacts and never
read hidden ground-truth files (ground_truth.jsonl stays evaluator-only).
"""

import json
import uuid
from datetime import UTC
from pathlib import Path
from typing import Any

from marketpilot.benchmark.models import BenchmarkResult, ExperimentManifest
from marketpilot.domain.state import ResearchState
from marketpilot.observability.events import AgentEvent
from marketpilot.product_selection.loop import ProductSelectionResult
from marketpilot.webui.schemas import (
    CategoryStats,
    EnvironmentSummary,
    EvaluationView,
    ExperimentDetail,
    ExperimentSummary,
    GoalView,
    OverviewStats,
    RunDetail,
    RunSummary,
    SelectionDetail,
    StrategyRow,
)


class ArtifactNotFoundError(Exception):
    """Raised when a referenced artifact does not exist."""


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return dict(json.load(handle))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return [dict(json.loads(line)) for line in handle if line.strip()]


def _iso_to_ms(left: str | None, right: str | None) -> int:
    """Duration in ms between two ISO timestamps (0 when unusable)."""

    if not left or not right:
        return 0
    try:
        from datetime import datetime

        start = datetime.fromisoformat(left.replace("Z", "+00:00"))
        end = datetime.fromisoformat(right.replace("Z", "+00:00"))
        return max(int((end - start).total_seconds() * 1000), 0)
    except ValueError:
        return 0


def _first_last_event_time(trajectory: list[dict[str, Any]]) -> tuple[str | None, str | None]:
    first = next((item.get("timestamp") for item in trajectory), None)
    last = next((item.get("timestamp") for item in reversed(trajectory)), None)
    return (
        str(first) if first else None,
        str(last) if last else None,
    )


def load_run_summary(runs_dir: Path, run_dir: Path) -> RunSummary | None:
    summary_path = run_dir / "summary.json"
    recommendation_path = run_dir / "recommendation.json"
    if summary_path.exists():
        summary = _read_json(summary_path)
        trajectory = _read_jsonl(run_dir / "trajectory.jsonl")
        started_at, ended_at = _first_last_event_time(trajectory)
        return RunSummary(
            run_id=str(summary.get("run_id", run_dir.name)),
            kind="research",
            status=str(summary.get("status", "UNKNOWN")),
            market=str(summary.get("market", "")),
            category=str(summary.get("category", "")),
            objective=_objective_from_summary(run_dir),
            decision=str(summary.get("decision", "NONE")),
            evaluation_passed=bool(summary.get("evaluation_passed", False)),
            started_at=started_at,
            duration_ms=_iso_to_ms(started_at, ended_at),
            task_success_rate=_optional_float(summary.get("task_success_rate")),
            evidence_coverage=_optional_float(summary.get("evidence_coverage")),
            tool_success_rate=_optional_float(summary.get("tool_success_rate")),
            llm_calls=int(summary.get("llm_calls", 0) or 0),
            llm_total_tokens=int(summary.get("llm_total_tokens", 0) or 0),
            llm_estimated_cost=_optional_float(summary.get("llm_estimated_cost")),
            tool_calls=int(summary.get("tool_calls", 0) or 0),
            recommendation_text=str(summary.get("recommendation", "")),
            mode=str(summary.get("mode", "")),
            research_mode=str(summary.get("research_mode", "")),
            llm_provider=str(summary.get("llm_provider", "")),
            llm_model=str(summary.get("llm_model", "")),
        )
    if recommendation_path.exists():
        result = _read_json(recommendation_path)
        started_at = _file_mtime_iso(recommendation_path)
        return RunSummary(
            run_id=run_dir.name,
            kind="selection",
            status=result.get("termination", "UNKNOWN"),
            objective="",
            decision=str(result.get("final_verdict", "NONE")),
            termination=str(result.get("termination", "")),
            evaluation_passed=None,
            started_at=started_at,
            recommendation_text="Closed-loop product selection result.",
            research_rounds=int(result.get("research_rounds", 0)),
            initial_candidates=int(result.get("initial_candidates", 0)),
        )
    return None


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _file_mtime_iso(path: Path) -> str | None:
    from datetime import datetime

    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat()
    except OSError:
        return None


def list_runs(runs_dir: Path) -> list[RunSummary]:
    if not runs_dir.exists():
        return []
    summaries: list[RunSummary] = []
    for run_dir in sorted(runs_dir.iterdir(), key=lambda p: p.name):
        if not run_dir.is_dir():
            continue
        summary = load_run_summary(runs_dir, run_dir)
        if summary is not None:
            summaries.append(summary)
    summaries.sort(key=lambda item: item.started_at or "", reverse=True)
    return summaries


def _objective_from_summary(run_dir: Path) -> str:
    final_state_path = run_dir / "final_state.json"
    if not final_state_path.exists():
        return ""
    try:
        final_state = _read_json(final_state_path)
    except (json.JSONDecodeError, OSError):
        return ""
    goal = final_state.get("goal", {})
    return str(goal.get("objective", "")) if isinstance(goal, dict) else ""


def load_run_detail(runs_dir: Path, run_id: str) -> RunDetail:
    _validate_uuid(run_id)
    run_dir = runs_dir / run_id
    if not run_dir.is_dir():
        raise ArtifactNotFoundError(f"run not found: {run_id}")
    summary = _read_json(run_dir / "summary.json") if (run_dir / "summary.json").exists() else {}
    final_state = _read_json(run_dir / "final_state.json")
    state = ResearchState.model_validate(final_state)
    trajectory = [
        AgentEvent.model_validate(item).model_dump(mode="json")
        for item in _read_jsonl(run_dir / "trajectory.jsonl")
    ]
    sources_payload = _read_jsonl(run_dir / "sources.jsonl")

    goal = state.goal
    evaluation = _extract_evaluation(trajectory)

    return RunDetail(
        run_id=str(state.run_id),
        kind="research",
        status=state.status.value,
        goal=GoalView(
            objective=goal.objective,
            market=goal.market,
            category=goal.category,
            constraints=goal.constraints.model_dump(),
            budget=goal.budget.model_dump(),
        ),
        summary=summary,
        metrics=state.metrics.model_dump(),
        tasks=[task.model_dump(mode="json") for task in state.tasks.values()],
        evidence=[item.model_dump(mode="json") for item in state.evidence.values()],
        findings=[item.model_dump(mode="json") for item in state.findings.values()],
        candidates=[item.model_dump(mode="json") for item in state.candidates.values()],
        risk_flags=[item.model_dump(mode="json") for item in state.risk_flags.values()],
        recommendations=[
            item.model_dump(mode="json") for item in state.recommendations.values()
        ],
        trajectory=trajectory,
        evaluation=evaluation,
        sources=[item for item in sources_payload if item.get("kind") == "source"],
        snapshots=[item for item in sources_payload if item.get("kind") == "snapshot"],
        retrievals=[item for item in sources_payload if item.get("kind") == "retrieval"],
    )


def _extract_evaluation(trajectory: list[dict[str, Any]]) -> EvaluationView | None:
    for item in reversed(trajectory):
        if item.get("event_type") == "EVALUATION_COMPLETED":
            raw = item.get("output_summary")
            if not raw:
                continue
            try:
                payload = json.loads(str(raw))
            except json.JSONDecodeError:
                continue
            return EvaluationView(
                passed=bool(payload.get("passed", False)),
                checks=list(payload.get("checks", [])),
                metrics=dict(payload.get("metrics", {})),
            )
    return None


def load_selection_detail(runs_dir: Path, run_id: str) -> SelectionDetail:
    run_dir = runs_dir / run_id
    recommendation_path = run_dir / "recommendation.json"
    if not recommendation_path.exists():
        raise ArtifactNotFoundError(f"selection run not found: {run_id}")
    result = ProductSelectionResult.model_validate_json(recommendation_path.read_text("utf-8"))
    candidates_path = run_dir / "candidates.json"
    candidates: list[dict[str, Any]] = []
    if candidates_path.exists():
        raw = json.loads(candidates_path.read_text("utf-8"))
        if isinstance(raw, list):
            candidates = [dict(item) for item in raw if isinstance(item, dict)]
    return SelectionDetail(
        run_id=run_id,
        termination=result.termination.value,
        result=result.model_dump(mode="json"),
        candidates=candidates,
    )


def _validate_uuid(value: str) -> None:
    try:
        uuid.UUID(value)
    except ValueError as exc:
        raise ArtifactNotFoundError(f"invalid id: {value}") from exc


def load_experiment_summary(experiment_dir: Path) -> ExperimentSummary | None:
    manifest_path = experiment_dir / "manifest.json"
    metrics_path = experiment_dir / "metrics.json"
    if not manifest_path.exists():
        return None
    manifest = ExperimentManifest.model_validate(_read_json(manifest_path))
    metrics = _read_json(metrics_path) if metrics_path.exists() else {}
    return ExperimentSummary(
        experiment_id=manifest.experiment_id,
        name=manifest.name,
        strategy=manifest.strategy,
        model=manifest.model,
        provider=manifest.provider,
        seed=manifest.seed,
        dataset=manifest.dataset,
        benchmark_suite=manifest.benchmark_suite,
        git_commit=manifest.git_commit,
        started_at=manifest.started_at.isoformat(),
        completed_at=manifest.completed_at.isoformat() if manifest.completed_at else None,
        metrics=metrics,
    )


def list_experiments(benchmark_runs_dir: Path) -> list[ExperimentSummary]:
    if not benchmark_runs_dir.exists():
        return []
    summaries: list[ExperimentSummary] = []
    for experiment_dir in benchmark_runs_dir.iterdir():
        if not experiment_dir.is_dir():
            continue
        summary = load_experiment_summary(experiment_dir)
        if summary is not None:
            summaries.append(summary)
    summaries.sort(key=lambda item: item.started_at or "", reverse=True)
    return summaries


def load_experiment_detail(benchmark_runs_dir: Path, experiment_id: str) -> ExperimentDetail:
    _validate_uuid(experiment_id)
    experiment_dir = benchmark_runs_dir / experiment_id
    if not experiment_dir.is_dir() or not (experiment_dir / "manifest.json").exists():
        raise ArtifactNotFoundError(f"experiment not found: {experiment_id}")
    summary = load_experiment_summary(experiment_dir)
    if summary is None:
        raise ArtifactNotFoundError(f"experiment not found: {experiment_id}")
    results = [
        BenchmarkResult.model_validate(item)
        for item in _read_jsonl(experiment_dir / "results.jsonl")
    ]
    return ExperimentDetail(
        **summary.model_dump(),
        manifest=_read_json(experiment_dir / "manifest.json"),
        results=results,
        failures=_read_jsonl(experiment_dir / "failures.jsonl"),
    )


def build_strategy_table(summaries: list[ExperimentSummary]) -> list[StrategyRow]:
    """Aggregate per-strategy metrics across experiments (task-weighted)."""

    grouped: dict[str, list[ExperimentSummary]] = {}
    for item in summaries:
        grouped.setdefault(item.strategy, []).append(item)

    rows: list[StrategyRow] = []
    for strategy, items in sorted(grouped.items()):
        task_count = sum(int(item.metrics.get("task_count", 0) or 0) for item in items)
        rows.append(
            StrategyRow(
                strategy=strategy,
                experiment_count=len(items),
                task_count=task_count,
                mean_regret=_weighted(items, "mean_regret", "task_count"),
                mean_top_k_recall=_weighted(items, "mean_top_k_recall", "task_count"),
                mean_verifier_score=_weighted(items, "mean_verifier_score", "task_count"),
                mean_tool_calls=_weighted(items, "mean_tool_calls", "task_count"),
            )
        )
    rows.sort(key=lambda row: row.mean_regret)
    return rows


def _weighted(items: list[ExperimentSummary], metric: str, weight_key: str) -> float:
    total_weight = 0.0
    total = 0.0
    for item in items:
        weight = float(item.metrics.get(weight_key, 0) or 0)
        value = _optional_float(item.metrics.get(metric))
        total += weight * (value or 0.0)
        total_weight += weight
    return round(total / total_weight, 4) if total_weight else 0.0


def load_environment(
    datasets_dir: Path,
    dataset: str = "synthetic-market-v1",
) -> EnvironmentSummary:
    dataset_dir = datasets_dir / dataset
    manifest_path = dataset_dir / "manifest.json"
    if not manifest_path.exists():
        raise ArtifactNotFoundError(
            f"dataset not found: {dataset} (run `marketpilot dataset generate` first)"
        )
    manifest = _read_json(manifest_path)
    products = _read_jsonl(dataset_dir / "products.jsonl")
    facet_sources = _read_jsonl(dataset_dir / "sources_v2.jsonl")

    facets = sorted(
        {
            facet
            for item in facet_sources
            for facet in (item.get("evidence_facets") or [])
            if isinstance(facet, str)
        }
    )

    by_category: dict[str, list[dict[str, Any]]] = {}
    for product in products:
        category = str(product.get("category", "unknown"))
        by_category.setdefault(category, []).append(product)

    categories: list[CategoryStats] = []
    for category, items in sorted(by_category.items()):
        regimes: dict[str, int] = {}
        for item in items:
            regime = str(item.get("regime", "unknown"))
            regimes[regime] = regimes.get(regime, 0) + 1
        margins = [_metric(item, "gross_margin") for item in items]
        opportunities = [_metric(item, "opportunity_score") for item in items]
        top_products = sorted(
            items, key=lambda item: _metric(item, "opportunity_score"), reverse=True
        )[:3]
        categories.append(
            CategoryStats(
                category=category,
                product_count=len(items),
                mean_gross_margin=round(sum(margins) / len(margins), 4) if margins else 0.0,
                mean_opportunity=round(sum(opportunities) / len(opportunities), 4)
                if opportunities
                else 0.0,
                regimes=dict(sorted(regimes.items(), key=lambda pair: -pair[1])),
                top_products=[
                    {
                        "product_id": item.get("product_id"),
                        "title": item.get("title"),
                        "brand": item.get("brand"),
                        "regime": item.get("regime"),
                        "opportunity_score": item.get("opportunity_score"),
                        "selling_price": item.get("selling_price"),
                        "gross_margin": item.get("gross_margin"),
                    }
                    for item in top_products
                ],
            )
        )

    return EnvironmentSummary(
        dataset=str(manifest.get("dataset", dataset)),
        version=str(manifest.get("version", "")),
        generator_version=str(manifest.get("generator_version", "")),
        seed=int(manifest.get("seed", 0)),
        product_count=int(manifest.get("product_count", len(products))),
        review_count=int(manifest.get("review_count", 0)),
        source_count=int(manifest.get("source_count", 0)),
        categories=categories,
        evidence_facets=facets,
        note=(
            "Only observable agent-facing fields are exposed here; hidden latent "
            "ground truth (ground_truth.jsonl) is never read by the workbench."
        ),
    )


def _metric(item: dict[str, Any], key: str) -> float:
    value = item.get(key)
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


# Observable, agent-facing product fields only. Hidden latent ground truth
# (ground_truth.jsonl) is intentionally never exposed through the workbench.
_OBSERVABLE_PRODUCT_FIELDS = (
    "product_id",
    "title",
    "brand",
    "category",
    "subcategory",
    "regime",
    "selling_price",
    "estimated_cogs",
    "gross_margin",
    "monthly_search_volume",
    "search_growth_3m",
    "seasonality_index",
    "estimated_monthly_units",
    "seller_count",
    "median_competitor_reviews",
    "median_competitor_rating",
    "rating",
    "review_count",
    "return_rate",
    "complaint_rate",
    "regulatory_risk",
    "ip_risk",
    "saturation_risk",
    "ad_cpc_proxy",
    "differentiation_score",
    "demand_score",
    "competition_score",
    "risk_score",
    "opportunity_score",
    "battery",
    "fragile",
    "liquid",
    "oversize",
)


def load_environment_products(
    datasets_dir: Path,
    category: str | None = None,
    sort: str = "opportunity_score",
    limit: int = 200,
) -> dict[str, Any]:
    """Return observable product rows for the synthetic environment explorer."""

    dataset_dir = datasets_dir / "synthetic-market-v1"
    products_path = dataset_dir / "products.jsonl"
    if not products_path.exists():
        raise ArtifactNotFoundError("dataset not found (run `marketpilot dataset generate` first)")
    products = _read_jsonl(products_path)
    if category:
        products = [item for item in products if str(item.get("category")) == category]
    sort_key = sort if sort in _OBSERVABLE_PRODUCT_FIELDS else "opportunity_score"
    products.sort(key=lambda item: _metric(item, sort_key), reverse=True)
    products = products[: max(1, min(limit, 500))]
    return {
        "category": category,
        "sort": sort_key,
        "total": len(products),
        "products": [
            {field: item.get(field) for field in _OBSERVABLE_PRODUCT_FIELDS}
            for item in products
        ],
    }


def load_overview(
    runs_dir: Path,
    benchmark_runs_dir: Path,
    datasets_dir: Path,
) -> OverviewStats:
    runs = list_runs(runs_dir)
    experiments = list_experiments(benchmark_runs_dir)
    research_runs = [item for item in runs if item.kind == "research"]
    selection_runs = [item for item in runs if item.kind == "selection"]
    total_benchmark_tasks = sum(
        int(item.metrics.get("task_count", 0) or 0) for item in experiments
    )
    environment: EnvironmentSummary | None = None
    try:
        environment = load_environment(datasets_dir)
    except ArtifactNotFoundError:
        environment = None
    return OverviewStats(
        research_runs=len(research_runs),
        selection_runs=len(selection_runs),
        experiments=len(experiments),
        total_benchmark_tasks=total_benchmark_tasks,
        environment=environment,
        strategy_table=build_strategy_table(experiments),
        latest_experiments=experiments[:5],
        latest_runs=runs[:8],
    )
