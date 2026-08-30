"""Shared blackboard state for a research run."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from marketpilot.domain.enums import RunStatus, TaskStatus
from marketpilot.domain.evidence import EvidenceItem
from marketpilot.domain.findings import Finding
from marketpilot.domain.goals import ResearchBudget, ResearchGoal
from marketpilot.domain.recommendations import ProductCandidate, Recommendation, RiskFlag
from marketpilot.domain.tasks import TaskNode


class ExecutionMetrics(BaseModel):
    """Accumulated execution metrics for observability and evaluation."""

    model_config = ConfigDict(frozen=True)

    tasks_total: int = Field(default=0, ge=0)
    tasks_successful: int = Field(default=0, ge=0)
    tasks_failed: int = Field(default=0, ge=0)
    tool_calls: int = Field(default=0, ge=0)
    tool_failures: int = Field(default=0, ge=0)
    evidence_count: int = Field(default=0, ge=0)
    elapsed_seconds: float = Field(default=0.0, ge=0)
    token_cost: float = Field(default=0.0, ge=0)
    llm_calls: int = Field(default=0, ge=0)
    llm_input_tokens: int = Field(default=0, ge=0)
    llm_output_tokens: int = Field(default=0, ge=0)
    llm_total_tokens: int = Field(default=0, ge=0)
    llm_latency_ms: int = Field(default=0, ge=0)
    llm_estimated_cost: float | None = Field(default=None, ge=0)
    llm_failed_calls: int = Field(default=0, ge=0)
    llm_retry_count: int = Field(default=0, ge=0)


class ResearchState(BaseModel):
    """Typed shared state that agents read from and explicitly update."""

    model_config = ConfigDict(validate_assignment=True)

    run_id: UUID
    goal: ResearchGoal
    status: RunStatus = RunStatus.CREATED
    tasks: dict[UUID, TaskNode] = Field(default_factory=dict)
    evidence: dict[UUID, EvidenceItem] = Field(default_factory=dict)
    findings: dict[UUID, Finding] = Field(default_factory=dict)
    candidates: dict[UUID, ProductCandidate] = Field(default_factory=dict)
    risk_flags: dict[UUID, RiskFlag] = Field(default_factory=dict)
    recommendations: dict[UUID, Recommendation] = Field(default_factory=dict)
    budget: ResearchBudget
    metrics: ExecutionMetrics = ExecutionMetrics()

    @model_validator(mode="after")
    def validate_budget(self) -> "ResearchState":
        if self.budget != self.goal.budget:
            self.__dict__["budget"] = self.goal.budget
        return self

    def add_task(self, task: TaskNode) -> None:
        if task.run_id != self.run_id:
            raise ValueError("task belongs to a different run")
        self.tasks[task.task_id] = task
        self.metrics = self.metrics.model_copy(update={"tasks_total": self.metrics.tasks_total + 1})

    def update_task(self, task: TaskNode) -> None:
        if task.task_id not in self.tasks:
            raise KeyError(str(task.task_id))
        self.tasks[task.task_id] = task
        if task.status is TaskStatus.SUCCEEDED:
            self.metrics = self.metrics.model_copy(
                update={"tasks_successful": self.metrics.tasks_successful + 1}
            )
        elif task.status is TaskStatus.FAILED and task.attempt_count >= task.max_attempts:
            self.metrics = self.metrics.model_copy(
                update={"tasks_failed": self.metrics.tasks_failed + 1}
            )

    def add_evidence(self, item: EvidenceItem) -> None:
        if item.run_id != self.run_id:
            raise ValueError("evidence belongs to a different run")
        self.evidence[item.evidence_id] = item
        self.metrics = self.metrics.model_copy(
            update={"evidence_count": self.metrics.evidence_count + 1}
        )

    def add_finding(self, finding: Finding) -> None:
        missing = set(finding.evidence_ids) - set(self.evidence)
        if missing:
            raise ValueError(f"finding references missing evidence: {sorted(missing)}")
        self.findings[finding.finding_id] = finding

    def add_candidate(self, candidate: ProductCandidate) -> None:
        if candidate.run_id != self.run_id:
            raise ValueError("candidate belongs to a different run")
        self.candidates[candidate.candidate_id] = candidate

    def add_risk_flag(self, flag: RiskFlag) -> None:
        if flag.run_id != self.run_id:
            raise ValueError("risk flag belongs to a different run")
        self.risk_flags[flag.risk_id] = flag

    def add_recommendation(self, recommendation: Recommendation) -> None:
        if recommendation.run_id != self.run_id:
            raise ValueError("recommendation belongs to a different run")
        missing_findings = set(recommendation.findings) - set(self.findings)
        missing_evidence = set(recommendation.supporting_evidence) - set(self.evidence)
        missing_risks = set(recommendation.risk_flags) - set(self.risk_flags)
        if missing_findings or missing_evidence or missing_risks:
            raise ValueError(
                "recommendation references missing objects: "
                f"findings={sorted(missing_findings)}, "
                f"evidence={sorted(missing_evidence)}, risks={sorted(missing_risks)}"
            )
        self.recommendations[recommendation.recommendation_id] = recommendation
