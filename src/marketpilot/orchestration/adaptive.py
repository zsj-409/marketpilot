"""Bounded adaptive research planning."""

from uuid import NAMESPACE_URL, uuid5

from marketpilot.domain.enums import AgentRole, TaskType
from marketpilot.domain.state import ResearchState
from marketpilot.domain.tasks import TaskNode


class AdaptiveResearchPlanner:
    """Spawn bounded follow-up tasks when evidence coverage is insufficient."""

    def __init__(self, max_followup_tasks: int = 3, max_replans: int = 2) -> None:
        self.max_followup_tasks = max_followup_tasks
        self.max_replans = max_replans

    def plan_followups(self, state: ResearchState) -> list[TaskNode]:
        """Return typed follow-up tasks for missing research coverage."""

        followups: list[TaskNode] = []
        existing_types = {task.task_type for task in state.tasks.values()}
        evidence_count = len(state.evidence)
        findings_count = len(state.findings)
        risk_count = len(state.risk_flags)

        if evidence_count == 0 and TaskType.MARKET_RESEARCH not in existing_types:
            followups.append(self._task(state, TaskType.MARKET_RESEARCH, AgentRole.MARKET_RESEARCH))
        if findings_count < 3 and TaskType.REVIEW_RESEARCH not in existing_types:
            followups.append(self._task(state, TaskType.REVIEW_RESEARCH, AgentRole.REVIEW_MINING))
        if TaskType.COMPETITOR_RESEARCH not in existing_types:
            followups.append(
                self._task(state, TaskType.COMPETITOR_RESEARCH, AgentRole.COMPETITOR_RESEARCH)
            )
        if risk_count == 0 and TaskType.RISK_ANALYSIS not in existing_types:
            followups.append(self._task(state, TaskType.RISK_ANALYSIS, AgentRole.RISK_ANALYSIS))
        if not state.recommendations and TaskType.DECISION not in existing_types:
            followups.append(self._task(state, TaskType.DECISION, AgentRole.DECISION))

        return followups[: self.max_followup_tasks]

    def _task(self, state: ResearchState, task_type: TaskType, role: AgentRole) -> TaskNode:
        return TaskNode(
            task_id=uuid5(
                NAMESPACE_URL,
                f"marketpilot:adaptive:{state.run_id}:{task_type.value}:{len(state.tasks)}",
            ),
            run_id=state.run_id,
            task_type=task_type,
            assigned_role=role,
            description=f"Adaptive follow-up: {task_type.value}",
        )
