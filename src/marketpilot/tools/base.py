"""Tool protocol and structured input/output contracts."""

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from marketpilot.domain.enums import EvidenceSourceType, ToolResultStatus
from marketpilot.research.budget import BudgetTracker
from marketpilot.research.dedup import SourceDeduplicator
from marketpilot.research.replay import ReplayStore
from marketpilot.research.store import ResearchStore


class ToolArguments(BaseModel):
    """Typed arguments shared by deterministic mock tools."""

    model_config = ConfigDict(frozen=True)

    query: str | None = Field(default=None, min_length=1, max_length=500)
    category: str | None = Field(default=None, min_length=2, max_length=100)
    market: str | None = Field(default=None, min_length=2, max_length=100)
    product_name: str | None = Field(default=None, min_length=2, max_length=200)
    product_id: str | None = Field(default=None, min_length=1, max_length=200)
    memory_key: str | None = Field(default=None, min_length=1, max_length=200)
    memory_value: str | None = Field(default=None, min_length=1, max_length=2000)
    url: str | None = Field(default=None, min_length=3, max_length=2048)


class ToolInput(BaseModel):
    """A single typed tool invocation."""

    model_config = ConfigDict(frozen=True)

    tool_name: str = Field(min_length=1, max_length=100)
    arguments: ToolArguments = ToolArguments()


class ToolOutput(BaseModel):
    """A normalized observation returned by a tool."""

    model_config = ConfigDict(frozen=True)

    summary: str = Field(min_length=1, max_length=1000)
    source_uri: str = Field(min_length=3, max_length=2048)
    observation: str = Field(min_length=1, max_length=4000)
    confidence: float = Field(ge=0, le=1)
    entities: frozenset[str] = frozenset()
    source_id: UUID | None = None
    snapshot_id: UUID | None = None
    evidence_source_type: EvidenceSourceType | None = None


class ToolResult(BaseModel):
    """Structured success or failure result."""

    model_config = ConfigDict(frozen=True)

    tool_call_id: UUID = Field(default_factory=uuid4)
    tool_name: str = Field(min_length=1, max_length=100)
    status: ToolResultStatus
    output: ToolOutput | None = None
    error_message: str | None = Field(default=None, max_length=2000)
    latency_ms: int = Field(default=0, ge=0)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def succeeded(self) -> bool:
        return self.status is ToolResultStatus.SUCCESS


class ToolMetadata(BaseModel):
    """Stable tool contract metadata."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=1000)
    version: str = Field(min_length=1, max_length=20)
    input_schema: dict[str, object] = Field(default_factory=dict)
    risk_level: str = Field(default="low", max_length=20)
    timeout_seconds: float = Field(default=5.0, gt=0)
    retry_policy: str = Field(default="none", max_length=100)


class ToolContext(BaseModel):
    """Execution context passed to a tool."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    run_id: UUID
    task_id: UUID
    research_store: ResearchStore | None = None
    budget: BudgetTracker | None = None
    replay_store: ReplayStore | None = None
    research_mode: str = "mock"
    deduplicator: SourceDeduplicator | None = None


class Tool(Protocol):
    """Provider-neutral tool interface."""

    @property
    def metadata(self) -> ToolMetadata:
        """Return the tool's stable contract."""

    async def execute(self, arguments: ToolArguments, context: ToolContext) -> ToolOutput:
        """Execute the tool and return a normalized observation."""
