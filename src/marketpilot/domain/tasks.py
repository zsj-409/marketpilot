"""Task node contracts for the research DAG."""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from marketpilot.domain.enums import AgentRole, TaskStatus, TaskType


class TaskNode(BaseModel):
    """A typed unit of long-horizon research work."""

    model_config = ConfigDict(validate_assignment=True)

    task_id: UUID
    run_id: UUID
    task_type: TaskType
    assigned_role: AgentRole
    description: str = Field(min_length=3, max_length=500)
    dependencies: frozenset[UUID] = frozenset()
    status: TaskStatus = TaskStatus.PENDING
    attempt_count: int = Field(default=0, ge=0)
    max_attempts: int = Field(default=3, ge=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_self_dependency(self) -> "TaskNode":
        if self.task_id in self.dependencies:
            raise ValueError("a task cannot depend on itself")
        return self

    @property
    def can_retry(self) -> bool:
        return self.attempt_count < self.max_attempts
