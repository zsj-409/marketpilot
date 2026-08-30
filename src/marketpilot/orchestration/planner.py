"""Deterministic initial research planner."""

from uuid import NAMESPACE_URL, UUID, uuid5

from marketpilot.domain.enums import AgentRole, TaskType
from marketpilot.domain.goals import ResearchGoal
from marketpilot.domain.tasks import TaskNode
from marketpilot.orchestration.dag import TaskDAG


class ResearchPlanner:
    """Create the initial Step 1 research DAG."""

    def plan(self, run_id: UUID, goal: ResearchGoal) -> TaskDAG:
        market = self._task(
            run_id,
            TaskType.MARKET_RESEARCH,
            AgentRole.MARKET_RESEARCH,
            f"Analyze market signals for {goal.category} in {goal.market}.",
            set(),
        )
        product = self._task(
            run_id,
            TaskType.PRODUCT_DISCOVERY,
            AgentRole.PRODUCT_RESEARCH,
            f"Discover provider-neutral product candidates in {goal.category}.",
            set(),
        )
        reviews = self._task(
            run_id,
            TaskType.REVIEW_RESEARCH,
            AgentRole.REVIEW_MINING,
            f"Identify recurring customer pain points for {goal.category}.",
            set(),
        )
        competitors = self._task(
            run_id,
            TaskType.COMPETITOR_RESEARCH,
            AgentRole.COMPETITOR_RESEARCH,
            f"Assess competitive intensity for {goal.category} in {goal.market}.",
            set(),
        )
        aggregation = self._task(
            run_id,
            TaskType.CANDIDATE_AGGREGATION,
            AgentRole.PRODUCT_RESEARCH,
            "Aggregate candidates and estimate unit economics.",
            {market.task_id, product.task_id, reviews.task_id, competitors.task_id},
        )
        risk = self._task(
            run_id,
            TaskType.RISK_ANALYSIS,
            AgentRole.RISK_ANALYSIS,
            "Analyze execution, competition, and regulatory risks.",
            {aggregation.task_id},
        )
        decision = self._task(
            run_id,
            TaskType.DECISION,
            AgentRole.DECISION,
            "Produce an evidence-grounded product recommendation.",
            {risk.task_id},
        )
        verification = self._task(
            run_id,
            TaskType.EVIDENCE_VERIFICATION,
            AgentRole.EVIDENCE_VERIFIER,
            "Verify that all findings and recommendations reference valid evidence.",
            {decision.task_id},
        )
        return TaskDAG(
            [
                market,
                product,
                reviews,
                competitors,
                aggregation,
                risk,
                decision,
                verification,
            ]
        )

    def _task(
        self,
        run_id: UUID,
        task_type: TaskType,
        role: AgentRole,
        description: str,
        dependencies: set[UUID],
    ) -> TaskNode:
        return TaskNode(
            task_id=uuid5(
                NAMESPACE_URL,
                f"marketpilot:task:{run_id}:{task_type.value}",
            ),
            run_id=run_id,
            task_type=task_type,
            assigned_role=role,
            description=description,
            dependencies=frozenset(dependencies),
        )
