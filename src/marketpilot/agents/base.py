"""Framework-independent agent contracts."""

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from marketpilot.domain.enums import AgentRole, AgentStatus
from marketpilot.domain.evidence import EvidenceItem
from marketpilot.domain.findings import Finding
from marketpilot.domain.recommendations import ProductCandidate, Recommendation, RiskFlag
from marketpilot.domain.state import ResearchState
from marketpilot.domain.tasks import TaskNode
from marketpilot.llm.models import LLMMetrics
from marketpilot.memory.base import MemoryStore
from marketpilot.observability.trajectory import TrajectoryRecorder
from marketpilot.tools.base import ToolInput, ToolResult

ToolExecutor = Callable[[ToolInput], Awaitable[ToolResult]]


class AgentError(BaseModel):
    """A structured agent failure."""

    model_config = ConfigDict(frozen=True)

    code: str = Field(min_length=3, max_length=100)
    message: str = Field(min_length=3, max_length=2000)


class AgentContext(BaseModel):
    """Dependencies injected into an agent execution."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    run_id: UUID
    tool_executor: ToolExecutor | None = None
    memory_store: MemoryStore | None = None
    trajectory: TrajectoryRecorder | None = None


class AgentResult(BaseModel):
    """Structured outputs from one agent execution."""

    model_config = ConfigDict(frozen=True)

    status: AgentStatus
    confidence: float = Field(ge=0, le=1)
    findings: list[Finding] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    candidates: list[ProductCandidate] = Field(default_factory=list)
    risk_flags: list[RiskFlag] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    proposed_tasks: list[TaskNode] = Field(default_factory=list)
    tool_calls: list[ToolResult] = Field(default_factory=list)
    llm_metrics: LLMMetrics | None = None
    error: AgentError | None = None


class Agent(ABC):
    """A role-specific agent with an explicit typed contract."""

    @property
    @abstractmethod
    def role(self) -> AgentRole:
        """Return the role implemented by this agent."""

    @abstractmethod
    async def execute(
        self,
        task: TaskNode,
        state: ResearchState,
        context: AgentContext,
    ) -> AgentResult:
        """Execute one task against shared state and return structured outputs."""
