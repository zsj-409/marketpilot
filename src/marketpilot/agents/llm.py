"""LLM-backed MarketPilot agents."""

from typing import TypedDict
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel

from marketpilot.agents.base import AgentError, AgentResult
from marketpilot.agents.llm_outputs import (
    CompetitorResearchOutput,
    DecisionOutput,
    MarketResearchOutput,
    ProductResearchOutput,
    ReviewResearchOutput,
    RiskAnalysisOutput,
)
from marketpilot.agents.llm_runtime import LLMAgent
from marketpilot.agents.mock import MockEvidenceVerifierAgent, MockResearchManagerAgent
from marketpilot.agents.registry import AgentRegistry
from marketpilot.domain.enums import AgentRole, AgentStatus
from marketpilot.domain.evidence import EvidenceItem
from marketpilot.domain.findings import Finding
from marketpilot.domain.recommendations import (
    ProductCandidate,
    Recommendation,
    RiskFlag,
)
from marketpilot.domain.state import ResearchState
from marketpilot.domain.tasks import TaskNode
from marketpilot.llm.base import LLMClient
from marketpilot.llm.models import LLMToolDefinition
from marketpilot.llm.pricing import PricingCalculator
from marketpilot.prompts.base import PromptRegistry
from marketpilot.tools.registry import ToolRegistry


class LLMRuntimeKwargs(TypedDict):
    """Typed constructor keyword arguments shared by LLM agents."""

    client: LLMClient
    prompt_registry: PromptRegistry
    pricing: PricingCalculator | None
    provider_name: str
    model_name: str
    allowed_tools: tuple[str, ...] | None
    max_model_turns: int
    max_tool_calls: int


def _tool_definitions(
    tool_registry: ToolRegistry,
    names: list[str],
) -> list[LLMToolDefinition]:
    definitions: list[LLMToolDefinition] = []
    for name in names:
        tool = tool_registry.get(name)
        definitions.append(
            LLMToolDefinition(
                name=tool.metadata.name,
                description=tool.metadata.description,
                input_schema=tool.metadata.input_schema,
            )
        )
    return definitions


def _finding(
    task: TaskNode,
    claim: str,
    confidence: float,
    evidence: list[EvidenceItem],
) -> Finding:
    return Finding(
        finding_id=uuid5(
            NAMESPACE_URL,
            f"marketpilot:llm-finding:{task.run_id}:{task.task_id}:{claim}",
        ),
        run_id=task.run_id,
        task_id=task.task_id,
        claim=claim,
        confidence=confidence,
        evidence_ids=frozenset(item.evidence_id for item in evidence),
    )


class LLMMarketResearchAgent(LLMAgent):
    """LLM-backed market research agent."""

    @property
    def prompt_name(self) -> str:
        return "market_research"

    @property
    def output_model(self) -> type[BaseModel]:
        return MarketResearchOutput

    @property
    def tool_names(self) -> tuple[str, ...]:
        return ("get_market_signal",)

    @property
    def role(self) -> AgentRole:
        return AgentRole.MARKET_RESEARCH

    def _convert_output(
        self,
        output: BaseModel,
        task: TaskNode,
        state: ResearchState,
        evidence: list[EvidenceItem],
    ) -> AgentResult:
        assert isinstance(output, MarketResearchOutput)
        if not evidence:
            return self._missing_evidence(task)
        finding = _finding(task, output.claim, output.confidence, evidence)
        return AgentResult(
            status=AgentStatus.SUCCEEDED,
            confidence=output.confidence,
            evidence=evidence,
            findings=[finding],
        )

    def _missing_evidence(self, task: TaskNode) -> AgentResult:
        return AgentResult(
            status=AgentStatus.FAILED,
            confidence=0.0,
            error=AgentError(code="MISSING_EVIDENCE", message="no evidence collected"),
        )


class LLMProductResearchAgent(LLMAgent):
    """LLM-backed product research and aggregation agent."""

    @property
    def prompt_name(self) -> str:
        return "product_research"

    @property
    def output_model(self) -> type[BaseModel]:
        return ProductResearchOutput

    @property
    def tool_names(self) -> tuple[str, ...]:
        return (
            "search_products",
            "get_product_details",
            "estimate_cost",
            "estimate_margin",
        )

    @property
    def role(self) -> AgentRole:
        return AgentRole.PRODUCT_RESEARCH

    def _convert_output(
        self,
        output: BaseModel,
        task: TaskNode,
        state: ResearchState,
        evidence: list[EvidenceItem],
    ) -> AgentResult:
        assert isinstance(output, ProductResearchOutput)
        if not evidence:
            return AgentResult(
                status=AgentStatus.FAILED,
                confidence=0.0,
                error=AgentError(code="MISSING_EVIDENCE", message="no evidence collected"),
            )
        candidate = next(
            (
                item
                for item in state.candidates.values()
                if item.name == output.candidate_name
                and item.provider_product_id == output.provider_product_id
            ),
            None,
        )
        if candidate is None:
            candidate = ProductCandidate(
                candidate_id=uuid5(
                    NAMESPACE_URL,
                    f"marketpilot:llm-candidate:{task.run_id}:{task.task_id}:"
                    f"{output.provider_product_id}",
                ),
                run_id=task.run_id,
                name=output.candidate_name,
                category=state.goal.category,
                market=state.goal.market,
                provider="llm",
                provider_product_id=output.provider_product_id,
            )
        finding = _finding(task, output.claim, output.confidence, evidence)
        return AgentResult(
            status=AgentStatus.SUCCEEDED,
            confidence=output.confidence,
            evidence=evidence,
            findings=[finding],
            candidates=[candidate],
        )


class LLMReviewResearchAgent(LLMAgent):
    """LLM-backed review mining agent."""

    @property
    def prompt_name(self) -> str:
        return "review_research"

    @property
    def output_model(self) -> type[BaseModel]:
        return ReviewResearchOutput

    @property
    def tool_names(self) -> tuple[str, ...]:
        return ("search_reviews",)

    @property
    def role(self) -> AgentRole:
        return AgentRole.REVIEW_MINING

    def _convert_output(
        self,
        output: BaseModel,
        task: TaskNode,
        state: ResearchState,
        evidence: list[EvidenceItem],
    ) -> AgentResult:
        assert isinstance(output, ReviewResearchOutput)
        if not evidence:
            return AgentResult(
                status=AgentStatus.FAILED,
                confidence=0.0,
                error=AgentError(code="MISSING_EVIDENCE", message="no evidence collected"),
            )
        finding = _finding(task, output.claim, output.confidence, evidence)
        return AgentResult(
            status=AgentStatus.SUCCEEDED,
            confidence=output.confidence,
            evidence=evidence,
            findings=[finding],
        )


class LLMCompetitorResearchAgent(LLMAgent):
    """LLM-backed competitor research agent."""

    @property
    def prompt_name(self) -> str:
        return "competitor_research"

    @property
    def output_model(self) -> type[BaseModel]:
        return CompetitorResearchOutput

    @property
    def tool_names(self) -> tuple[str, ...]:
        return ("web_search",)

    @property
    def role(self) -> AgentRole:
        return AgentRole.COMPETITOR_RESEARCH

    def _convert_output(
        self,
        output: BaseModel,
        task: TaskNode,
        state: ResearchState,
        evidence: list[EvidenceItem],
    ) -> AgentResult:
        assert isinstance(output, CompetitorResearchOutput)
        if not evidence:
            return AgentResult(
                status=AgentStatus.FAILED,
                confidence=0.0,
                error=AgentError(code="MISSING_EVIDENCE", message="no evidence collected"),
            )
        finding = _finding(task, output.claim, output.confidence, evidence)
        return AgentResult(
            status=AgentStatus.SUCCEEDED,
            confidence=output.confidence,
            evidence=evidence,
            findings=[finding],
        )


class LLMRiskAnalysisAgent(LLMAgent):
    """LLM-backed risk analysis agent."""

    @property
    def prompt_name(self) -> str:
        return "risk_analysis"

    @property
    def output_model(self) -> type[BaseModel]:
        return RiskAnalysisOutput

    @property
    def tool_names(self) -> tuple[str, ...]:
        return ("estimate_cost", "estimate_margin")

    @property
    def role(self) -> AgentRole:
        return AgentRole.RISK_ANALYSIS

    def _convert_output(
        self,
        output: BaseModel,
        task: TaskNode,
        state: ResearchState,
        evidence: list[EvidenceItem],
    ) -> AgentResult:
        assert isinstance(output, RiskAnalysisOutput)
        if not evidence:
            return AgentResult(
                status=AgentStatus.FAILED,
                confidence=0.0,
                error=AgentError(code="MISSING_EVIDENCE", message="no evidence collected"),
            )
        risk = RiskFlag(
            risk_id=uuid5(
                NAMESPACE_URL,
                f"marketpilot:llm-risk:{task.run_id}:{task.task_id}:{output.label}",
            ),
            run_id=task.run_id,
            label=output.label,
            severity=output.severity,
            rationale=output.rationale,
            evidence_ids=frozenset(item.evidence_id for item in evidence),
        )
        finding = _finding(task, output.claim, output.confidence, evidence)
        return AgentResult(
            status=AgentStatus.SUCCEEDED,
            confidence=output.confidence,
            evidence=evidence,
            findings=[finding],
            risk_flags=[risk],
        )


class LLMDecisionAgent(LLMAgent):
    """LLM-backed decision agent."""

    @property
    def prompt_name(self) -> str:
        return "decision"

    @property
    def output_model(self) -> type[BaseModel]:
        return DecisionOutput

    @property
    def tool_names(self) -> tuple[str, ...]:
        return ()

    def _request_metadata(
        self,
        task: TaskNode,
        state: ResearchState,
    ) -> dict[str, str | int | float | bool | None]:
        if not state.candidates:
            return {}
        candidate = next(iter(state.candidates.values()))
        return {"candidate_id": str(candidate.candidate_id)}

    @property
    def role(self) -> AgentRole:
        return AgentRole.DECISION

    def _convert_output(
        self,
        output: BaseModel,
        task: TaskNode,
        state: ResearchState,
        evidence: list[EvidenceItem],
    ) -> AgentResult:
        assert isinstance(output, DecisionOutput)
        candidate = state.candidates.get(output.candidate_id)
        if candidate is None:
            return AgentResult(
                status=AgentStatus.FAILED,
                confidence=0.0,
                error=AgentError(
                    code="CANDIDATE_NOT_FOUND",
                    message=f"candidate not found: {output.candidate_id}",
                ),
            )
        if not state.findings or not state.evidence or not state.risk_flags:
            return AgentResult(
                status=AgentStatus.FAILED,
                confidence=0.0,
                error=AgentError(
                    code="INSUFFICIENT_EVIDENCE",
                    message="decision requires findings, evidence, and risks",
                ),
            )
        recommendation = Recommendation(
            recommendation_id=uuid5(
                NAMESPACE_URL,
                f"marketpilot:llm-recommendation:{task.run_id}:{task.task_id}",
            ),
            run_id=task.run_id,
            candidate=candidate,
            scores=output.scores,
            findings=frozenset(state.findings),
            supporting_evidence=frozenset(state.evidence),
            risk_flags=frozenset(state.risk_flags),
            decision=output.decision,
            confidence=output.confidence,
            rationale=output.rationale,
        )
        return AgentResult(
            status=AgentStatus.SUCCEEDED,
            confidence=output.confidence,
            recommendations=[recommendation],
        )


def build_llm_agent_registry(
    *,
    client: LLMClient,
    tool_registry: ToolRegistry,
    prompt_registry: PromptRegistry,
    provider_name: str,
    model_name: str,
    pricing: PricingCalculator | None = None,
    allowed_tools: tuple[str, ...] | None = None,
    max_model_turns: int = 4,
    max_tool_calls: int = 8,
) -> AgentRegistry:
    """Build an agent registry that uses LLM workers and deterministic verification."""

    runtime: LLMRuntimeKwargs = {
        "client": client,
        "prompt_registry": prompt_registry,
        "pricing": pricing,
        "provider_name": provider_name,
        "model_name": model_name,
        "allowed_tools": allowed_tools,
        "max_model_turns": max_model_turns,
        "max_tool_calls": max_tool_calls,
    }

    effective_tools = list(allowed_tools) if allowed_tools is not None else None
    market = LLMMarketResearchAgent(
        tool_definitions=_tool_definitions(tool_registry, effective_tools or ["get_market_signal"]),
        **runtime,
    )
    product = LLMProductResearchAgent(
        tool_definitions=_tool_definitions(
            tool_registry,
            effective_tools
            or [
                "search_products",
                "get_product_details",
                "estimate_cost",
                "estimate_margin",
            ],
        ),
        **runtime,
    )
    review = LLMReviewResearchAgent(
        tool_definitions=_tool_definitions(tool_registry, effective_tools or ["search_reviews"]),
        **runtime,
    )
    competitor = LLMCompetitorResearchAgent(
        tool_definitions=_tool_definitions(tool_registry, effective_tools or ["web_search"]),
        **runtime,
    )
    risk = LLMRiskAnalysisAgent(
        tool_definitions=_tool_definitions(
            tool_registry,
            effective_tools or ["estimate_cost", "estimate_margin"],
        ),
        **runtime,
    )
    decision = LLMDecisionAgent(tool_definitions=[], **runtime)

    registry = AgentRegistry()
    registry.register(MockResearchManagerAgent())
    registry.register(market)
    registry.register(product)
    registry.register(review)
    registry.register(competitor)
    registry.register(risk)
    registry.register(decision)
    registry.register(MockEvidenceVerifierAgent())
    return registry
