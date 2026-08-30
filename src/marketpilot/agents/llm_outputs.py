"""Typed structured-output models for LLM agents."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from marketpilot.domain.enums import Decision
from marketpilot.domain.recommendations import ProductScore


class MarketResearchOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    claim: str = Field(min_length=3, max_length=1000)
    confidence: float = Field(ge=0, le=1)


class ProductResearchOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    candidate_name: str = Field(min_length=2, max_length=200)
    provider_product_id: str = Field(min_length=1, max_length=200)
    claim: str = Field(min_length=3, max_length=1000)
    confidence: float = Field(ge=0, le=1)


class ReviewResearchOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    claim: str = Field(min_length=3, max_length=1000)
    confidence: float = Field(ge=0, le=1)


class CompetitorResearchOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    claim: str = Field(min_length=3, max_length=1000)
    confidence: float = Field(ge=0, le=1)


class RiskAnalysisOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    label: str = Field(min_length=3, max_length=200)
    severity: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=3, max_length=1000)
    claim: str = Field(min_length=3, max_length=1000)
    confidence: float = Field(ge=0, le=1)


class DecisionOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    candidate_id: UUID
    decision: Decision
    confidence: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=3, max_length=2000)
    scores: ProductScore
