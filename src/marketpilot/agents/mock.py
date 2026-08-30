"""Deterministic mock agents for offline architecture validation."""

from hashlib import sha256
from typing import final
from uuid import NAMESPACE_URL, UUID, uuid5

from marketpilot.agents.base import Agent, AgentContext, AgentError, AgentResult
from marketpilot.agents.registry import AgentRegistry
from marketpilot.domain.enums import (
    AgentRole,
    AgentStatus,
    Decision,
    EvidenceSourceType,
    TaskType,
)
from marketpilot.domain.evidence import EvidenceItem
from marketpilot.domain.findings import Finding
from marketpilot.domain.recommendations import (
    ProductCandidate,
    ProductScore,
    Recommendation,
    RiskFlag,
)
from marketpilot.domain.state import ResearchState
from marketpilot.domain.tasks import TaskNode
from marketpilot.tools.base import ToolArguments, ToolInput, ToolOutput, ToolResult


def _uuid(run_id: UUID, task_id: UUID, label: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"marketpilot:{run_id}:{task_id}:{label}")


def _hash(value: str) -> str:
    return sha256(value.encode()).hexdigest()


async def _call_tool(context: AgentContext, name: str, arguments: ToolArguments) -> ToolResult:
    if context.tool_executor is None:
        raise ValueError("tool executor is not configured")
    result = await context.tool_executor(ToolInput(tool_name=name, arguments=arguments))
    if result.output is None:
        raise ValueError(f"tool {name} returned no output")
    return result


def _evidence(
    task: TaskNode,
    output: ToolOutput,
    result: ToolResult,
    source_type: EvidenceSourceType,
    entity: str | None = None,
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=_uuid(task.run_id, task.task_id, f"evidence:{result.tool_call_id}"),
        run_id=task.run_id,
        task_id=task.task_id,
        source_type=source_type,
        source_uri=output.source_uri,
        content_hash=_hash(output.observation),
        excerpt=output.observation,
        confidence=output.confidence,
        related_entity=entity,
        tool_call_id=result.tool_call_id,
    )


def _finding(
    task: TaskNode,
    claim: str,
    confidence: float,
    evidence_ids: list[UUID],
) -> Finding:
    return Finding(
        finding_id=_uuid(task.run_id, task.task_id, f"finding:{claim}"),
        run_id=task.run_id,
        task_id=task.task_id,
        claim=claim,
        confidence=confidence,
        evidence_ids=frozenset(evidence_ids),
    )


@final
class MockResearchManagerAgent(Agent):
    """Deterministic manager used to validate the manager contract."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.RESEARCH_MANAGER

    async def execute(
        self,
        task: TaskNode,
        state: ResearchState,
        context: AgentContext,
    ) -> AgentResult:
        return AgentResult(status=AgentStatus.SUCCEEDED, confidence=1.0)


@final
class MockMarketResearchAgent(Agent):
    """Produces a deterministic market signal and finding."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.MARKET_RESEARCH

    async def execute(
        self,
        task: TaskNode,
        state: ResearchState,
        context: AgentContext,
    ) -> AgentResult:
        result = await _call_tool(
            context,
            "get_market_signal",
            ToolArguments(category=state.goal.category, market=state.goal.market),
        )
        assert result.output is not None
        item = _evidence(task, result.output, result, EvidenceSourceType.MARKET_SIGNAL)
        finding = _finding(
            task,
            f"{state.goal.category} demand in {state.goal.market} is moderately rising.",
            0.82,
            [item.evidence_id],
        )
        return AgentResult(
            status=AgentStatus.SUCCEEDED,
            confidence=0.82,
            evidence=[item],
            findings=[finding],
            tool_calls=[result],
        )


@final
class MockProductResearchAgent(Agent):
    """Produces deterministic candidates, evidence, and findings."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.PRODUCT_RESEARCH

    async def execute(
        self,
        task: TaskNode,
        state: ResearchState,
        context: AgentContext,
    ) -> AgentResult:
        if task.task_type is TaskType.CANDIDATE_AGGREGATION:
            cost = await _call_tool(
                context,
                "estimate_cost",
                ToolArguments(product_name="automatic pet feeder"),
            )
            margin = await _call_tool(
                context,
                "estimate_margin",
                ToolArguments(product_name="automatic pet feeder"),
            )
            assert cost.output is not None and margin.output is not None
            cost_evidence = _evidence(task, cost.output, cost, EvidenceSourceType.MOCK)
            margin_evidence = _evidence(task, margin.output, margin, EvidenceSourceType.MOCK)
            finding = _finding(
                task,
                "Automatic pet feeder has an estimated gross margin above the user threshold.",
                0.74,
                [cost_evidence.evidence_id, margin_evidence.evidence_id],
            )
            return AgentResult(
                status=AgentStatus.SUCCEEDED,
                confidence=0.74,
                evidence=[cost_evidence, margin_evidence],
                findings=[finding],
                tool_calls=[cost, margin],
            )

        search = await _call_tool(
            context,
            "search_products",
            ToolArguments(category=state.goal.category, market=state.goal.market),
        )
        details = await _call_tool(
            context,
            "get_product_details",
            ToolArguments(product_id="mock-automatic-pet-feeder"),
        )
        assert search.output is not None and details.output is not None
        search_evidence = _evidence(
            task,
            search.output,
            search,
            EvidenceSourceType.PRODUCT_CATALOG,
            "automatic pet feeder",
        )
        details_evidence = _evidence(
            task,
            details.output,
            details,
            EvidenceSourceType.PRODUCT_CATALOG,
            "automatic pet feeder",
        )
        candidate = ProductCandidate(
            candidate_id=_uuid(task.run_id, task.task_id, "candidate"),
            run_id=task.run_id,
            name="Automatic pet feeder",
            category=state.goal.category,
            market=state.goal.market,
            provider="mock",
            provider_product_id="mock-automatic-pet-feeder",
        )
        finding = _finding(
            task,
            "Automatic pet feeder is a provider-neutral candidate with stable demand.",
            0.78,
            [search_evidence.evidence_id, details_evidence.evidence_id],
        )
        return AgentResult(
            status=AgentStatus.SUCCEEDED,
            confidence=0.78,
            evidence=[search_evidence, details_evidence],
            findings=[finding],
            candidates=[candidate],
            tool_calls=[search, details],
        )


@final
class MockReviewMiningAgent(Agent):
    """Produces deterministic review-pain evidence and findings."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.REVIEW_MINING

    async def execute(
        self,
        task: TaskNode,
        state: ResearchState,
        context: AgentContext,
    ) -> AgentResult:
        result = await _call_tool(
            context,
            "search_reviews",
            ToolArguments(product_name="automatic pet feeder"),
        )
        assert result.output is not None
        item = _evidence(task, result.output, result, EvidenceSourceType.REVIEW_FEED)
        finding = _finding(
            task,
            "Battery reliability is a recurring customer complaint for automatic pet feeders.",
            0.8,
            [item.evidence_id],
        )
        return AgentResult(
            status=AgentStatus.SUCCEEDED,
            confidence=0.8,
            evidence=[item],
            findings=[finding],
            tool_calls=[result],
        )


@final
class MockCompetitorResearchAgent(Agent):
    """Produces deterministic competitor evidence and findings."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.COMPETITOR_RESEARCH

    async def execute(
        self,
        task: TaskNode,
        state: ResearchState,
        context: AgentContext,
    ) -> AgentResult:
        result = await _call_tool(
            context,
            "web_search",
            ToolArguments(query=f"{state.goal.category} competitors {state.goal.market}"),
        )
        assert result.output is not None
        item = _evidence(task, result.output, result, EvidenceSourceType.SEARCH_RESULT)
        finding = _finding(
            task,
            "Competition for automatic pet feeders is medium-high.",
            0.71,
            [item.evidence_id],
        )
        return AgentResult(
            status=AgentStatus.SUCCEEDED,
            confidence=0.71,
            evidence=[item],
            findings=[finding],
            tool_calls=[result],
        )


@final
class MockRiskAnalysisAgent(Agent):
    """Produces deterministic risk flags."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.RISK_ANALYSIS

    async def execute(
        self,
        task: TaskNode,
        state: ResearchState,
        context: AgentContext,
    ) -> AgentResult:
        result = await _call_tool(
            context,
            "estimate_margin",
            ToolArguments(product_name="automatic pet feeder"),
        )
        assert result.output is not None
        item = _evidence(task, result.output, result, EvidenceSourceType.MOCK)
        risk = RiskFlag(
            risk_id=_uuid(task.run_id, task.task_id, "risk"),
            run_id=task.run_id,
            label="Medium-high competition",
            severity=0.62,
            rationale="Multiple established sellers and recurring price competition.",
            evidence_ids=frozenset({item.evidence_id}),
        )
        finding = _finding(
            task,
            "Competition and battery-reliability complaints create moderate execution risk.",
            0.69,
            [item.evidence_id],
        )
        return AgentResult(
            status=AgentStatus.SUCCEEDED,
            confidence=0.69,
            evidence=[item],
            findings=[finding],
            risk_flags=[risk],
            tool_calls=[result],
        )


@final
class MockDecisionAgent(Agent):
    """Produces a deterministic evidence-grounded recommendation."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.DECISION

    async def execute(
        self,
        task: TaskNode,
        state: ResearchState,
        context: AgentContext,
    ) -> AgentResult:
        if not state.candidates or not state.findings or not state.risk_flags:
            return AgentResult(
                status=AgentStatus.FAILED,
                confidence=0.0,
                error=AgentError(
                    code="INSUFFICIENT_INPUTS",
                    message="decision requires candidates, findings, and risk flags",
                ),
            )

        candidate = next(iter(state.candidates.values()))
        scores = ProductScore(
            demand=0.78,
            trend=0.72,
            estimated_margin=0.68,
            competition=0.62,
            customer_pain_opportunity=0.74,
            operational_complexity=0.55,
            regulatory_risk=0.22,
            overall_score=0.68,
        )
        recommendation = Recommendation(
            recommendation_id=_uuid(task.run_id, task.task_id, "recommendation"),
            run_id=task.run_id,
            candidate=candidate,
            scores=scores,
            findings=frozenset(state.findings),
            supporting_evidence=frozenset(state.evidence),
            risk_flags=frozenset(state.risk_flags),
            decision=Decision.WATCH,
            confidence=0.73,
            rationale=(
                "Demand and margin are acceptable, but medium-high competition and "
                "recurring reliability complaints warrant continued monitoring."
            ),
        )
        return AgentResult(
            status=AgentStatus.SUCCEEDED,
            confidence=0.73,
            recommendations=[recommendation],
        )


@final
class MockEvidenceVerifierAgent(Agent):
    """Deterministically validates evidence references."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.EVIDENCE_VERIFIER

    async def execute(
        self,
        task: TaskNode,
        state: ResearchState,
        context: AgentContext,
    ) -> AgentResult:
        for finding in state.findings.values():
            missing = set(finding.evidence_ids) - set(state.evidence)
            if missing:
                return AgentResult(
                    status=AgentStatus.FAILED,
                    confidence=0.0,
                    error=AgentError(
                        code="MISSING_EVIDENCE",
                        message=f"finding {finding.finding_id} references missing evidence",
                    ),
                )
        finding = _finding(
            task,
            "All findings reference evidence present in the shared evidence store.",
            1.0,
            list(state.evidence),
        )
        return AgentResult(status=AgentStatus.SUCCEEDED, confidence=1.0, findings=[finding])


def build_default_agent_registry() -> AgentRegistry:
    """Build the deterministic offline agent set."""

    registry = AgentRegistry()
    for agent in (
        MockResearchManagerAgent(),
        MockMarketResearchAgent(),
        MockProductResearchAgent(),
        MockReviewMiningAgent(),
        MockCompetitorResearchAgent(),
        MockRiskAnalysisAgent(),
        MockDecisionAgent(),
        MockEvidenceVerifierAgent(),
    ):
        registry.register(agent)
    return registry
