"""Benchmark and experiment models."""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FailureCategory(StrEnum):
    """Structured failure taxonomy."""

    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    LOW_SOURCE_DIVERSITY = "LOW_SOURCE_DIVERSITY"
    CONSTRAINT_VIOLATION = "CONSTRAINT_VIOLATION"
    UNSUPPORTED_CLAIM = "UNSUPPORTED_CLAIM"
    RISK_MISSED = "RISK_MISSED"
    POOR_RANKING = "POOR_RANKING"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    TOOL_FAILURE = "TOOL_FAILURE"
    STRUCTURED_OUTPUT_FAILURE = "STRUCTURED_OUTPUT_FAILURE"
    REPLAY_MISS = "REPLAY_MISS"


class BenchmarkTask(BaseModel):
    model_config = ConfigDict(frozen=True)

    task_id: UUID
    task_key: str
    family: str
    difficulty: str = "easy"
    goal: str
    market: str
    category: str
    constraints: dict[str, float] = Field(default_factory=dict)
    environment_id: str
    allowed_budget: dict[str, int] = Field(default_factory=dict)
    rubric: dict[str, object] = Field(default_factory=dict)
    hidden_ground_truth_ref: dict[str, str] = Field(default_factory=dict)


class BenchmarkSuite(BaseModel):
    model_config = ConfigDict(frozen=True)

    suite_id: str
    name: str
    version: str
    tasks: list[BenchmarkTask]


class BenchmarkResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    task_key: str
    family: str
    difficulty: str = "easy"
    category: str
    strategy: str
    status: str
    selected_product_id: UUID | None = None
    best_available_opportunity: float = 0.0
    selected_opportunity: float = 0.0
    regret: float = 0.0
    top_k_recall: float = 0.0
    constraint_satisfied: bool = True
    risk_recall: float = 0.0
    ranking_correlation: float = 0.0
    verifier_score: float = 0.0
    tool_calls: int = 0
    llm_tokens: int = 0
    latency_ms: int = 0
    estimated_cost: float = 0.0
    failure: FailureCategory | None = None


class ExperimentManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    experiment_id: str
    name: str
    git_commit: str
    dataset: str
    dataset_version: str
    generator_version: str
    seed: int
    benchmark_suite: str
    strategy: str
    model: str
    provider: str
    prompt_versions: dict[str, str] = Field(default_factory=dict)
    research_budget: dict[str, int] = Field(default_factory=dict)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
