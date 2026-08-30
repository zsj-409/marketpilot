"""Evidence and provenance contracts."""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from marketpilot.domain.enums import EvidenceKind, EvidenceSourceType


class EvidenceItem(BaseModel):
    """A normalized, auditable observation used to support findings."""

    model_config = ConfigDict(frozen=True)

    evidence_id: UUID
    run_id: UUID
    task_id: UUID
    source_type: EvidenceSourceType
    source_uri: str = Field(min_length=3, max_length=2048)
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    content_hash: str = Field(min_length=8, max_length=128)
    excerpt: str = Field(min_length=1, max_length=2000)
    confidence: float = Field(ge=0, le=1)
    related_entity: str | None = Field(default=None, max_length=200)
    extraction_method: str = Field(default="deterministic_mock", max_length=100)
    tool_call_id: UUID | None = None
    snapshot_id: UUID | None = None
    kind: EvidenceKind = EvidenceKind.OBSERVATION
