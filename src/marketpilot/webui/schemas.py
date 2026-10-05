"""Typed schemas for the web workbench API."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from marketpilot.benchmark.models import BenchmarkResult


class RunSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    kind: str  # "research" or "selection"
    status: str
    market: str = ""
    category: str = ""
    objective: str = ""
    decision: str = "NONE"
    termination: str | None = None
    evaluation_passed: bool | None = None
    started_at: str | None = None
    duration_ms: int = 0
    task_success_rate: float | None = None
    evidence_coverage: float | None = None
    tool_success_rate: float | None = None
    llm_calls: int = 0
    llm_total_tokens: int = 0
    llm_estimated_cost: float | None = None
    tool_calls: int = 0
    recommendation_text: str = ""
    mode: str = ""
    research_mode: str = ""
    llm_provider: str = ""
    llm_model: str = ""
    research_rounds: int | None = None
    initial_candidates: int | None = None


class GoalView(BaseModel):
    model_config = ConfigDict(frozen=True)

    objective: str
    market: str
    category: str
    constraints: dict[str, Any] = Field(default_factory=dict)
    budget: dict[str, Any] = Field(default_factory=dict)


class EvaluationView(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    checks: list[dict[str, Any]] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


class RunDetail(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    kind: str
    status: str
    goal: GoalView
    summary: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    findings: list[dict[str, Any]] = Field(default_factory=list)
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    risk_flags: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    trajectory: list[dict[str, Any]] = Field(default_factory=list)
    evaluation: EvaluationView | None = None
    sources: list[dict[str, Any]] = Field(default_factory=list)
    snapshots: list[dict[str, Any]] = Field(default_factory=list)
    retrievals: list[dict[str, Any]] = Field(default_factory=list)


class SelectionDetail(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    kind: str = "selection"
    termination: str
    result: dict[str, Any] = Field(default_factory=dict)
    candidates: list[dict[str, Any]] = Field(default_factory=list)


class ExperimentSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    experiment_id: str
    name: str
    strategy: str
    model: str
    provider: str
    seed: int
    dataset: str
    benchmark_suite: str
    git_commit: str = ""
    started_at: str | None = None
    completed_at: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


class ExperimentDetail(ExperimentSummary):
    manifest: dict[str, Any] = Field(default_factory=dict)
    results: list[BenchmarkResult] = Field(default_factory=list)
    failures: list[dict[str, Any]] = Field(default_factory=list)


class StrategyRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    strategy: str
    experiment_count: int
    task_count: int
    mean_regret: float = 0.0
    mean_top_k_recall: float = 0.0
    mean_verifier_score: float = 0.0
    mean_tool_calls: float = 0.0


class CategoryStats(BaseModel):
    model_config = ConfigDict(frozen=True)

    category: str
    product_count: int
    mean_gross_margin: float = 0.0
    mean_opportunity: float = 0.0
    regimes: dict[str, int] = Field(default_factory=dict)
    top_products: list[dict[str, Any]] = Field(default_factory=list)


class EnvironmentSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    dataset: str
    version: str
    generator_version: str
    seed: int
    product_count: int
    review_count: int
    source_count: int
    categories: list[CategoryStats] = Field(default_factory=list)
    evidence_facets: list[str] = Field(default_factory=list)
    note: str = ""


class OverviewStats(BaseModel):
    model_config = ConfigDict(frozen=True)

    research_runs: int
    selection_runs: int
    experiments: int
    total_benchmark_tasks: int
    environment: EnvironmentSummary | None = None
    strategy_table: list[StrategyRow] = Field(default_factory=list)
    latest_experiments: list[ExperimentSummary] = Field(default_factory=list)
    latest_runs: list[RunSummary] = Field(default_factory=list)
