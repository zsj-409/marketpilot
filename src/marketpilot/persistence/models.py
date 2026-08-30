"""SQLAlchemy models for the future PostgreSQL persistence layer.

Step 1 defines the logical schema but does not require a live database. This
keeps the offline demo reproducible while making the future storage boundary
explicit.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Base class for persistence models."""


finding_evidence = Table(
    "finding_evidence",
    Base.metadata,
    Column("finding_id", String(36), ForeignKey("findings.finding_id"), primary_key=True),
    Column("evidence_id", String(36), ForeignKey("evidence_items.evidence_id"), primary_key=True),
)

recommendation_findings = Table(
    "recommendation_findings",
    Base.metadata,
    Column(
        "recommendation_id",
        String(36),
        ForeignKey("recommendations.recommendation_id"),
        primary_key=True,
    ),
    Column("finding_id", String(36), ForeignKey("findings.finding_id"), primary_key=True),
)

recommendation_evidence = Table(
    "recommendation_evidence",
    Base.metadata,
    Column(
        "recommendation_id",
        String(36),
        ForeignKey("recommendations.recommendation_id"),
        primary_key=True,
    ),
    Column(
        "evidence_id",
        String(36),
        ForeignKey("evidence_items.evidence_id"),
        primary_key=True,
    ),
)

recommendation_risks = Table(
    "recommendation_risks",
    Base.metadata,
    Column(
        "recommendation_id",
        String(36),
        ForeignKey("recommendations.recommendation_id"),
        primary_key=True,
    ),
    Column("risk_id", String(36), ForeignKey("risk_flags.risk_id"), primary_key=True),
)


class ResearchRunRow(Base):
    __tablename__ = "research_runs"

    run_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    market: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    constraints: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    budget: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tasks: Mapped[list["ResearchTaskRow"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    evidence: Mapped[list["EvidenceItemRow"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    findings: Mapped[list["FindingRow"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_research_runs_market_category", "market", "category"),)


class ResearchTaskRow(Base):
    __tablename__ = "research_tasks"

    task_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(
        ForeignKey("research_runs.run_id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    assigned_role: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    dependencies: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    run: Mapped[ResearchRunRow] = relationship(back_populates="tasks")


class SourceRow(Base):
    __tablename__ = "sources"

    source_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    uri: Mapped[str] = mapped_column(String(2048), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    __table_args__ = (UniqueConstraint("source_type", "uri", name="uq_source_type_uri"),)


class ToolCallRow(Base):
    __tablename__ = "tool_calls"

    tool_call_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    run_id: Mapped[str] = mapped_column(
        ForeignKey("research_runs.run_id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[str] = mapped_column(
        ForeignKey("research_tasks.task_id", ondelete="CASCADE"), nullable=False, index=True
    )
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    input: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class EvidenceItemRow(Base):
    __tablename__ = "evidence_items"

    evidence_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    run_id: Mapped[str] = mapped_column(
        ForeignKey("research_runs.run_id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[str] = mapped_column(
        ForeignKey("research_tasks.task_id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_id: Mapped[str] = mapped_column(
        ForeignKey("sources.source_id"), nullable=False, index=True
    )
    tool_call_id: Mapped[str | None] = mapped_column(
        ForeignKey("tool_calls.tool_call_id"), nullable=True
    )
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    related_entity: Mapped[str | None] = mapped_column(String(200), nullable=True)
    extraction_method: Mapped[str] = mapped_column(String(100), nullable=False)

    run: Mapped[ResearchRunRow] = relationship(back_populates="evidence")
    findings: Mapped[list["FindingRow"]] = relationship(
        secondary=finding_evidence, back_populates="evidence"
    )


class FindingRow(Base):
    __tablename__ = "findings"

    finding_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    run_id: Mapped[str] = mapped_column(
        ForeignKey("research_runs.run_id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[str] = mapped_column(
        ForeignKey("research_tasks.task_id", ondelete="CASCADE"), nullable=False, index=True
    )
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    run: Mapped[ResearchRunRow] = relationship(back_populates="findings")
    evidence: Mapped[list[EvidenceItemRow]] = relationship(
        secondary=finding_evidence, back_populates="findings"
    )


class ProductCandidateRow(Base):
    __tablename__ = "product_candidates"

    candidate_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    run_id: Mapped[str] = mapped_column(
        ForeignKey("research_runs.run_id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    market: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_product_id: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class ProductScoreRow(Base):
    __tablename__ = "product_scores"

    score_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("product_candidates.candidate_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    demand: Mapped[float] = mapped_column(Float, nullable=False)
    trend: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_margin: Mapped[float] = mapped_column(Float, nullable=False)
    competition: Mapped[float] = mapped_column(Float, nullable=False)
    customer_pain_opportunity: Mapped[float] = mapped_column(Float, nullable=False)
    operational_complexity: Mapped[float] = mapped_column(Float, nullable=False)
    regulatory_risk: Mapped[float] = mapped_column(Float, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)


class RiskFlagRow(Base):
    __tablename__ = "risk_flags"

    risk_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(
        ForeignKey("research_runs.run_id", ondelete="CASCADE"), nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    severity: Mapped[float] = mapped_column(Float, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class RecommendationRow(Base):
    __tablename__ = "recommendations"

    recommendation_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    run_id: Mapped[str] = mapped_column(
        ForeignKey("research_runs.run_id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("product_candidates.candidate_id", ondelete="CASCADE"), nullable=False
    )
    score_id: Mapped[str] = mapped_column(
        ForeignKey("product_scores.score_id", ondelete="CASCADE"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    findings: Mapped[list[FindingRow]] = relationship(secondary=recommendation_findings)
    evidence: Mapped[list[EvidenceItemRow]] = relationship(secondary=recommendation_evidence)
    risks: Mapped[list[RiskFlagRow]] = relationship(secondary=recommendation_risks)


class AgentEventRow(Base):
    __tablename__ = "agent_events"

    event_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    run_id: Mapped[str] = mapped_column(
        ForeignKey("research_runs.run_id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[str | None] = mapped_column(
        ForeignKey("research_tasks.task_id", ondelete="SET NULL"), nullable=True
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )
    parent_event_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    input_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    output_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    event_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, default=dict
    )
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("run_id", "sequence_number", name="uq_agent_events_sequence"),
    )


class MemoryRow(Base):
    __tablename__ = "memories"

    memory_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    scope: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    run_id: Mapped[str | None] = mapped_column(
        ForeignKey("research_runs.run_id", ondelete="CASCADE"), nullable=True, index=True
    )
    key: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    __table_args__ = (Index("ix_memories_scope_key", "scope", "key"),)


class EvaluationRow(Base):
    __tablename__ = "evaluations"

    evaluation_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    run_id: Mapped[str] = mapped_column(
        ForeignKey("research_runs.run_id", ondelete="CASCADE"), nullable=False, unique=True
    )
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    checks: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class BenchmarkSuiteRow(Base):
    __tablename__ = "benchmark_suites"

    suite_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    manifest: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class BenchmarkTaskRow(Base):
    __tablename__ = "benchmark_tasks"

    task_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    suite_id: Mapped[str] = mapped_column(
        ForeignKey("benchmark_suites.suite_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_key: Mapped[str] = mapped_column(String(200), nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    market: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    constraints: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    environment_id: Mapped[str] = mapped_column(String(200), nullable=False)
    allowed_budget: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    rubric: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    hidden_ground_truth_ref: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )

    __table_args__ = (UniqueConstraint("suite_id", "task_key", name="uq_benchmark_task_key"),)


class BenchmarkRunRow(Base):
    __tablename__ = "benchmark_runs"

    benchmark_run_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    suite_id: Mapped[str] = mapped_column(
        ForeignKey("benchmark_suites.suite_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_id: Mapped[str] = mapped_column(
        ForeignKey("benchmark_tasks.task_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    strategy: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(200), nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False, default=42)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="CREATED")
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ExperimentRow(Base):
    __tablename__ = "experiments"

    experiment_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    git_commit: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    dataset: Mapped[str] = mapped_column(String(200), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(50), nullable=False)
    generator_version: Mapped[str] = mapped_column(String(50), nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False, default=42)
    benchmark_suite: Mapped[str] = mapped_column(String(200), nullable=False)
    strategy: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(200), nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_versions: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    research_budget: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


__all__ = [
    "AgentEventRow",
    "Base",
    "BenchmarkRunRow",
    "BenchmarkSuiteRow",
    "BenchmarkTaskRow",
    "EvaluationRow",
    "EvidenceItemRow",
    "ExperimentRow",
    "FindingRow",
    "MemoryRow",
    "ProductCandidateRow",
    "ProductScoreRow",
    "RecommendationRow",
    "ResearchRunRow",
    "ResearchTaskRow",
    "RiskFlagRow",
    "SourceRow",
    "ToolCallRow",
]
