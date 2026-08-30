"""Intermediate analytical conclusions."""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Finding(BaseModel):
    """A claim that must be backed by at least one evidence item."""

    model_config = ConfigDict(frozen=True)

    finding_id: UUID
    run_id: UUID
    task_id: UUID
    claim: str = Field(min_length=3, max_length=1000)
    confidence: float = Field(ge=0, le=1)
    evidence_ids: frozenset[UUID] = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
