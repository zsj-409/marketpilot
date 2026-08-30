"""Deterministic DAG execution over the shared blackboard."""

import time
from collections.abc import Awaitable, Callable
from uuid import UUID

from marketpilot.agents.base import AgentContext, AgentError, AgentResult
from marketpilot.agents.registry import AgentRegistry
from marketpilot.domain.enums import (
    AgentStatus,
    EventType,
    MemoryScope,
    RunStatus,
    ToolResultStatus,
)
from marketpilot.domain.state import ResearchState
from marketpilot.domain.tasks import TaskNode
from marketpilot.evaluation.evaluator import SystemEvaluator
from marketpilot.evaluation.schemas import EvaluationResult
from marketpilot.llm.models import LLMMetrics
from marketpilot.memory.base import MemoryQuery, MemoryRecord, MemoryStore
from marketpilot.memory.in_memory import InMemoryMemoryStore
from marketpilot.observability.events import ErrorInfo
from marketpilot.observability.trajectory import TrajectoryRecorder
from marketpilot.orchestration.dag import TaskDAG
from marketpilot.research.budget import BudgetTracker
from marketpilot.research.dedup import SourceDeduplicator
from marketpilot.research.replay import ReplayStore
from marketpilot.research.store import ResearchStore
from marketpilot.tools.base import ToolContext, ToolInput, ToolResult
from marketpilot.tools.errors import ToolError
from marketpilot.tools.registry import ToolRegistry

ToolExecutor = Callable[[ToolInput], Awaitable[ToolResult]]


class DAGRunner:
    """Execute ready tasks and apply structured agent outputs to state."""

    def __init__(
        self,
        agent_registry: AgentRegistry,
        tool_registry: ToolRegistry,
        recorder: TrajectoryRecorder,
        memory_store: MemoryStore | None = None,
        evaluator: SystemEvaluator | None = None,
        research_store: ResearchStore | None = None,
        budget: BudgetTracker | None = None,
        replay_store: ReplayStore | None = None,
        research_mode: str = "mock",
        deduplicator: SourceDeduplicator | None = None,
    ) -> None:
        self._agents = agent_registry
        self._tools = tool_registry
        self._recorder = recorder
        self._memory = memory_store or InMemoryMemoryStore()
        self._evaluator = evaluator or SystemEvaluator()
        self._research_store = research_store
        self._budget = budget
        self._replay_store = replay_store
        self._research_mode = research_mode
        self._deduplicator = deduplicator

    async def run(self, state: ResearchState) -> tuple[ResearchState, EvaluationResult]:
        started = time.perf_counter()
        state.status = RunStatus.RUNNING
        self._recorder.record(
            EventType.RUN_STARTED,
            actor="DAGRunner",
            input_summary=state.goal.objective,
            metadata={"market": state.goal.market, "category": state.goal.category},
        )
        await self._read_semantic_memory(state)

        dag = TaskDAG(list(state.tasks.values()))
        failure: ErrorInfo | None = None
        while dag.ready_tasks():
            for task in dag.ready_tasks():
                executed = await self._execute_task(task, state, dag)
                if not executed:
                    failure = ErrorInfo(
                        code="TASK_FAILED",
                        message=f"task {task.task_id} exhausted retries",
                    )
                    break
            if failure is not None:
                break

        elapsed = time.perf_counter() - started
        state.metrics = state.metrics.model_copy(update={"elapsed_seconds": elapsed})
        if failure is None and dag.all_succeeded():
            state.status = RunStatus.COMPLETED
        else:
            state.status = RunStatus.FAILED

        evaluation = self._evaluator.evaluate(state)
        self._recorder.record(
            EventType.EVALUATION_COMPLETED,
            actor="SystemEvaluator",
            output_summary=evaluation.model_dump_json(),
            metadata={"passed": evaluation.passed},
        )
        await self._write_episodic_memory(state, evaluation)
        if state.status is RunStatus.COMPLETED:
            self._recorder.record(
                EventType.RUN_COMPLETED,
                actor="DAGRunner",
                output_summary="research run completed",
                metadata={"elapsed_seconds": elapsed},
            )
        else:
            self._recorder.record(
                EventType.RUN_FAILED,
                actor="DAGRunner",
                output_summary="research run failed",
                error=failure,
                metadata={"elapsed_seconds": elapsed},
            )
        return state, evaluation

    async def _execute_task(
        self,
        task: TaskNode,
        state: ResearchState,
        dag: TaskDAG,
    ) -> bool:
        running = dag.mark_running(task.task_id)
        state.update_task(running)
        self._recorder.record(
            EventType.TASK_STARTED,
            actor=running.assigned_role.value,
            task_id=running.task_id,
            input_summary=running.description,
        )

        async def execute_tool(tool_input: ToolInput) -> ToolResult:
            return await self._execute_tool(tool_input, running.task_id, state)

        context = AgentContext(
            run_id=state.run_id,
            tool_executor=execute_tool,
            memory_store=self._memory,
            trajectory=self._recorder,
        )
        agent = self._agents.get(running.assigned_role)
        agent_started = time.perf_counter()
        self._recorder.record(
            EventType.AGENT_STARTED,
            actor=agent.role.value,
            task_id=running.task_id,
            input_summary=running.description,
        )
        try:
            result = await agent.execute(running, state, context)
        except Exception as exc:
            result = AgentResult(
                status=AgentStatus.FAILED,
                confidence=0.0,
                error=AgentError(
                    code="UNEXPECTED_AGENT_ERROR",
                    message=str(exc),
                ),
            )

        duration_ms = int((time.perf_counter() - agent_started) * 1000)
        if result.llm_metrics is not None:
            self._apply_llm_metrics(state, result.llm_metrics)
        if result.status is AgentStatus.SUCCEEDED:
            self._apply_result(result, state)
            completed = dag.mark_succeeded(running.task_id)
            state.update_task(completed)
            self._recorder.record(
                EventType.AGENT_COMPLETED,
                actor=agent.role.value,
                task_id=running.task_id,
                output_summary=f"status={result.status.value}; confidence={result.confidence}",
                duration_ms=duration_ms,
            )
            self._recorder.record(
                EventType.TASK_COMPLETED,
                actor=agent.role.value,
                task_id=running.task_id,
                output_summary=completed.description,
                duration_ms=duration_ms,
            )
            return True

        failed = dag.mark_failed(running.task_id)
        state.update_task(failed)
        error = result.error or AgentError(
            code="AGENT_FAILED",
            message="agent returned a failed status without an error",
        )
        self._recorder.record(
            EventType.AGENT_FAILED,
            actor=agent.role.value,
            task_id=running.task_id,
            output_summary=error.message,
            duration_ms=duration_ms,
            error=ErrorInfo(code=error.code, message=error.message),
        )
        self._recorder.record(
            EventType.TASK_FAILED,
            actor=agent.role.value,
            task_id=running.task_id,
            output_summary=error.message,
            duration_ms=duration_ms,
            error=ErrorInfo(code=error.code, message=error.message),
        )
        if dag.can_retry(running.task_id):
            retried = dag.retry_task(running.task_id)
            state.update_task(retried)
            self._recorder.record(
                EventType.TASK_RETRIED,
                actor="DAGRunner",
                task_id=running.task_id,
                output_summary=f"attempt={retried.attempt_count}",
            )
            return True
        return False

    async def _execute_tool(
        self,
        tool_input: ToolInput,
        task_id: UUID,
        state: ResearchState,
    ) -> ToolResult:
        started = time.perf_counter()
        self._recorder.record(
            EventType.TOOL_CALLED,
            actor=tool_input.tool_name,
            task_id=task_id,
            input_summary=tool_input.arguments.model_dump_json(),
        )
        state.metrics = state.metrics.model_copy(
            update={"tool_calls": state.metrics.tool_calls + 1}
        )
        if tool_input.tool_name == "web_search":
            self._recorder.record(
                EventType.SEARCH_REQUESTED,
                actor=tool_input.tool_name,
                task_id=task_id,
                input_summary=tool_input.arguments.query or "",
            )
        elif tool_input.tool_name == "fetch_page":
            self._recorder.record(
                EventType.SOURCE_RETRIEVAL_STARTED,
                actor=tool_input.tool_name,
                task_id=task_id,
                input_summary=tool_input.arguments.url or "",
            )
        try:
            tool = self._tools.get(tool_input.tool_name)
            self._tools.validate_input(tool_input)
            output = await tool.execute(
                tool_input.arguments,
                ToolContext(
                    run_id=state.run_id,
                    task_id=task_id,
                    research_store=self._research_store,
                    budget=self._budget,
                    replay_store=self._replay_store,
                    research_mode=self._research_mode,
                    deduplicator=self._deduplicator,
                ),
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
            result = ToolResult(
                tool_name=tool_input.tool_name,
                status=ToolResultStatus.SUCCESS,
                output=output,
                latency_ms=duration_ms,
            )
            self._recorder.record(
                EventType.TOOL_SUCCEEDED,
                actor=tool_input.tool_name,
                task_id=task_id,
                output_summary=output.summary,
                duration_ms=duration_ms,
                metadata={"status": result.status.value},
            )
            if tool_input.tool_name == "web_search":
                self._recorder.record(
                    EventType.SEARCH_COMPLETED,
                    actor=tool_input.tool_name,
                    task_id=task_id,
                    output_summary=output.summary,
                )
            elif tool_input.tool_name == "fetch_page":
                self._recorder.record(
                    EventType.SOURCE_RETRIEVAL_COMPLETED,
                    actor=tool_input.tool_name,
                    task_id=task_id,
                    output_summary=output.summary,
                    metadata={
                        "snapshot_id": str(output.snapshot_id),
                    }
                    if output.snapshot_id is not None
                    else {},
                )
                if output.snapshot_id is not None:
                    self._recorder.record(
                        EventType.SOURCE_SNAPSHOT_CREATED,
                        actor=tool_input.tool_name,
                        task_id=task_id,
                        output_summary=str(output.snapshot_id),
                    )
            if self._research_mode == "replay":
                self._recorder.record(
                    EventType.REPLAY_HIT,
                    actor=tool_input.tool_name,
                    task_id=task_id,
                    output_summary=tool_input.tool_name,
                )
            return result
        except ToolError as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            state.metrics = state.metrics.model_copy(
                update={"tool_failures": state.metrics.tool_failures + 1}
            )
            result = ToolResult(
                tool_name=tool_input.tool_name,
                status=exc.status,
                error_message=exc.message,
                latency_ms=duration_ms,
            )
            self._recorder.record(
                EventType.TOOL_FAILED,
                actor=tool_input.tool_name,
                task_id=task_id,
                output_summary=exc.message,
                duration_ms=duration_ms,
                metadata={"status": exc.status.value},
                error=ErrorInfo(code=exc.status.value, message=exc.message),
            )
            if exc.status is ToolResultStatus.REPLAY_MISS:
                self._recorder.record(
                    EventType.REPLAY_MISS,
                    actor=tool_input.tool_name,
                    task_id=task_id,
                    output_summary=exc.message,
                )
            elif exc.status is ToolResultStatus.BUDGET_EXHAUSTED:
                self._recorder.record(
                    EventType.RESEARCH_BUDGET_EXHAUSTED,
                    actor=tool_input.tool_name,
                    task_id=task_id,
                    output_summary=exc.message,
                )
            return result
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            state.metrics = state.metrics.model_copy(
                update={"tool_failures": state.metrics.tool_failures + 1}
            )
            result = ToolResult(
                tool_name=tool_input.tool_name,
                status=ToolResultStatus.PERMANENT_ERROR,
                error_message=str(exc),
                latency_ms=duration_ms,
            )
            self._recorder.record(
                EventType.TOOL_FAILED,
                actor=tool_input.tool_name,
                task_id=task_id,
                output_summary=str(exc),
                duration_ms=duration_ms,
                metadata={"status": result.status.value},
                error=ErrorInfo(code=result.status.value, message=str(exc)),
            )
            return result

    def _apply_result(self, result: AgentResult, state: ResearchState) -> None:
        for evidence_item in result.evidence:
            state.add_evidence(evidence_item)
            self._recorder.record(
                EventType.EVIDENCE_CREATED,
                actor="ResearchState",
                task_id=evidence_item.task_id,
                output_summary=evidence_item.excerpt,
                metadata={"source_type": evidence_item.source_type.value},
            )
        for finding_item in result.findings:
            state.add_finding(finding_item)
            self._recorder.record(
                EventType.FINDING_CREATED,
                actor="ResearchState",
                task_id=finding_item.task_id,
                output_summary=finding_item.claim,
                metadata={"confidence": finding_item.confidence},
            )
        for candidate_item in result.candidates:
            state.add_candidate(candidate_item)
        for risk_item in result.risk_flags:
            state.add_risk_flag(risk_item)
        for recommendation_item in result.recommendations:
            state.add_recommendation(recommendation_item)
            self._recorder.record(
                EventType.RECOMMENDATION_CREATED,
                actor="ResearchState",
                output_summary=recommendation_item.rationale,
                metadata={"decision": recommendation_item.decision.value},
            )
        self._recorder.record(
            EventType.STATE_UPDATED,
            actor="DAGRunner",
            output_summary=(
                f"evidence={len(state.evidence)}; findings={len(state.findings)}; "
                f"recommendations={len(state.recommendations)}"
            ),
        )

    def _apply_llm_metrics(
        self,
        state: ResearchState,
        metrics: LLMMetrics,
    ) -> None:
        current = state.metrics
        estimated_cost: float | None
        if current.llm_estimated_cost is not None and metrics.llm_estimated_cost is not None:
            estimated_cost = current.llm_estimated_cost + metrics.llm_estimated_cost
        elif current.llm_estimated_cost is not None:
            estimated_cost = current.llm_estimated_cost
        else:
            estimated_cost = metrics.llm_estimated_cost
        state.metrics = current.model_copy(
            update={
                "llm_calls": current.llm_calls + metrics.llm_calls,
                "llm_input_tokens": current.llm_input_tokens + metrics.llm_input_tokens,
                "llm_output_tokens": current.llm_output_tokens + metrics.llm_output_tokens,
                "llm_total_tokens": current.llm_total_tokens + metrics.llm_total_tokens,
                "llm_latency_ms": current.llm_latency_ms + metrics.llm_latency_ms,
                "llm_estimated_cost": estimated_cost,
                "llm_failed_calls": current.llm_failed_calls + metrics.llm_failed_calls,
                "llm_retry_count": current.llm_retry_count + metrics.llm_retry_count,
            }
        )

    async def _read_semantic_memory(self, state: ResearchState) -> None:
        records = await self._memory.retrieve(MemoryQuery(scope=MemoryScope.SEMANTIC))
        self._recorder.record(
            EventType.MEMORY_READ,
            actor="InMemoryMemoryStore",
            output_summary=f"records={len(records)}",
        )

    async def _write_episodic_memory(
        self,
        state: ResearchState,
        evaluation: EvaluationResult,
    ) -> None:
        record = MemoryRecord(
            scope=MemoryScope.EPISODIC,
            run_id=state.run_id,
            key=f"run:{state.run_id}",
            content=(
                f"status={state.status.value}; evaluation_passed={evaluation.passed}; "
                f"recommendations={len(state.recommendations)}"
            ),
            tags=frozenset({state.goal.market, state.goal.category}),
        )
        await self._memory.store(record)
        self._recorder.record(
            EventType.MEMORY_WRITTEN,
            actor="InMemoryMemoryStore",
            output_summary=record.content,
        )
