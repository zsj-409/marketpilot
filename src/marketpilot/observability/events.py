"""Machine-readable trajectory event contracts."""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from marketpilot.domain.enums import EventType


class ErrorInfo(BaseModel):
    """Structured error information attached to an event."""

    model_config = ConfigDict(frozen=True)

    code: str = Field(min_length=3, max_length=100)
    message: str = Field(min_length=3, max_length=2000)


class AgentEvent(BaseModel):
    """One immutable, ordered event in an agent trajectory."""

    model_config = ConfigDict(frozen=True)

    event_id: UUID
    sequence_number: int = Field(ge=0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    run_id: UUID
    task_id: UUID | None = None
    actor: str = Field(min_length=1, max_length=100)
    event_type: EventType
    parent_event_id: UUID | None = None
    input_summary: str | None = Field(default=None, max_length=2000)
    input_hash: str | None = Field(default=None, max_length=128)
    output_summary: str | None = Field(default=None, max_length=2000)
    output_hash: str | None = Field(default=None, max_length=128)
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    duration_ms: int = Field(default=0, ge=0)
    error: ErrorInfo | None = None
