"""Typed closed-loop product-selection contracts."""

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DecisionCriticVerdict(StrEnum):
    ACCEPT = "ACCEPT"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    CONSTRAINT_FAILURE = "CONSTRAINT_FAILURE"
    EVIDENCE_CONFLICT = "EVIDENCE_CONFLICT"
    NO_VIABLE_CANDIDATE = "NO_VIABLE_CANDIDATE"


class TerminationDecision(StrEnum):
    FINISH = "FINISH"
    CONTINUE_TARGETED_RESEARCH = "CONTINUE_TARGETED_RESEARCH"
    REPLAN_CANDIDATES = "REPLAN_CANDIDATES"
    INVESTIGATE_CONFLICT = "INVESTIGATE_CONFLICT"
    STOP_BUDGET_EXHAUSTED = "STOP_BUDGET_EXHAUSTED"
    STOP_NO_VIABLE_PATH = "STOP_NO_VIABLE_PATH"


class ResearchGap(BaseModel):
    model_config = ConfigDict(frozen=True)

    candidate_id: UUID
    facet: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=500)
    priority: int = Field(default=1, ge=1)
    required_evidence: str = Field(min_length=1, max_length=1000)


class ConstraintViolation(BaseModel):
    model_config = ConfigDict(frozen=True)

    candidate_id: UUID
    constraint: str = Field(min_length=1, max_length=200)
    severity: str = Field(min_length=1, max_length=50)
    evidence_ids: list[UUID] = Field(default_factory=list)


class EvidenceConflict(BaseModel):
    model_config = ConfigDict(frozen=True)

    candidate_id: UUID
    facet: str = Field(min_length=1, max_length=100)
    evidence_ids: list[UUID] = Field(min_length=2)
    explanation: str = Field(min_length=1, max_length=1000)


class ResearchRound(BaseModel):
    model_config = ConfigDict(frozen=True)

    round_number: int = Field(ge=0)
    unresolved_gaps: list[ResearchGap] = Field(default_factory=list)
    conflicts: list[EvidenceConflict] = Field(default_factory=list)
    completed_followup_tasks: list[str] = Field(default_factory=list)
    remaining_budget: int = Field(ge=0)
    termination_reason: TerminationDecision
