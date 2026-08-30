"""Structured evaluation contracts."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EvaluationCheck(BaseModel):
    """One deterministic structural assertion."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=3, max_length=200)
    passed: bool
    details: str = Field(min_length=0, max_length=2000)


class EvaluationMetrics(BaseModel):
    """System-level metrics suitable for future benchmarking."""

    model_config = ConfigDict(frozen=True)

    task_success_rate: float = Field(ge=0, le=1)
    evidence_coverage: float = Field(ge=0, le=1)
    unsupported_claim_rate: float = Field(ge=0, le=1)
    tool_success_rate: float = Field(ge=0, le=1)
    tool_calls_per_run: float = Field(ge=0)
    execution_latency_seconds: float = Field(ge=0)
    cost_per_run: float = Field(ge=0)
    retry_rate: float = Field(ge=0, le=1)
    recommendation_confidence: float = Field(ge=0, le=1)
    risk_violation_rate: float = Field(ge=0, le=1)
    llm_call_count: int = Field(ge=0)
    llm_input_tokens: int = Field(ge=0)
    llm_output_tokens: int = Field(ge=0)
    llm_total_tokens: int = Field(ge=0)
    llm_latency_ms: int = Field(ge=0)
    llm_estimated_cost: float | None = Field(default=None, ge=0)
    llm_failed_calls: int = Field(ge=0)
    llm_retry_count: int = Field(ge=0)


class EvaluationResult(BaseModel):
    """The complete result of evaluating one research run."""

    model_config = ConfigDict(frozen=True)

    run_id: UUID
    passed: bool
    checks: list[EvaluationCheck] = Field(min_length=1)
    metrics: EvaluationMetrics
