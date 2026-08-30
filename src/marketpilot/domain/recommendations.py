"""Product, score, risk, and recommendation contracts."""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from marketpilot.domain.enums import Decision


class ProductCandidate(BaseModel):
    """A provider-neutral product candidate."""

    model_config = ConfigDict(frozen=True)

    candidate_id: UUID
    run_id: UUID
    name: str = Field(min_length=2, max_length=200)
    category: str = Field(min_length=2, max_length=100)
    market: str = Field(min_length=2, max_length=100)
    provider: str = Field(default="mock", max_length=100)
    provider_product_id: str = Field(min_length=1, max_length=200)


class ProductScore(BaseModel):
    """Normalized product dimensions used by the decision agent."""

    model_config = ConfigDict(frozen=True)

    demand: float = Field(ge=0, le=1)
    trend: float = Field(ge=0, le=1)
    estimated_margin: float = Field(ge=0, le=1)
    competition: float = Field(ge=0, le=1)
    customer_pain_opportunity: float = Field(ge=0, le=1)
    operational_complexity: float = Field(ge=0, le=1)
    regulatory_risk: float = Field(ge=0, le=1)
    overall_score: float = Field(ge=0, le=1)


class RiskFlag(BaseModel):
    """A structured risk attached to a recommendation."""

    model_config = ConfigDict(frozen=True)

    risk_id: UUID
    run_id: UUID
    label: str = Field(min_length=3, max_length=200)
    severity: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=3, max_length=1000)
    evidence_ids: frozenset[UUID] = Field(default_factory=frozenset)


class Recommendation(BaseModel):
    """An evidence-grounded product recommendation."""

    model_config = ConfigDict(frozen=True)

    recommendation_id: UUID
    run_id: UUID
    candidate: ProductCandidate
    scores: ProductScore
    findings: frozenset[UUID] = Field(min_length=1)
    supporting_evidence: frozenset[UUID] = Field(min_length=1)
    risk_flags: frozenset[UUID] = Field(min_length=1)
    decision: Decision
    confidence: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=3, max_length=2000)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
