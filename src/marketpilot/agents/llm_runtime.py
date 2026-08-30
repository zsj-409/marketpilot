"""Reusable LLM agent execution runtime."""

import json
from abc import abstractmethod
from hashlib import sha256
from typing import cast
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import BaseModel

from marketpilot.agents.base import Agent, AgentContext, AgentError, AgentResult
from marketpilot.domain.enums import (
    AgentStatus,
    EventType,
    EvidenceSourceType,
)
from marketpilot.domain.evidence import EvidenceItem
from marketpilot.domain.state import ResearchState
from marketpilot.domain.tasks import TaskNode
from marketpilot.llm.base import LLMClient
from marketpilot.llm.errors import LLMError, LLMRetryExhaustedError, LLMStructuredOutputError
from marketpilot.llm.models import (
    LLMMessage,
    LLMMessageRole,
    LLMMetrics,
    LLMRequest,
    LLMResponse,
    LLMStructuredOutputSpec,
    LLMToolDefinition,
)
from marketpilot.llm.pricing import PricingCalculator
from marketpilot.llm.structured import parse_structured_output
from marketpilot.prompts.base import PromptRegistry
from marketpilot.tools.base import ToolInput, ToolResult


class LLMAgent(Agent):
    """Base class for LLM-backed agents."""

    def __init__(
        self,
        *,
        client: LLMClient,
        tool_definitions: list[LLMToolDefinition],
        prompt_registry: PromptRegistry,
        pricing: PricingCalculator | None = None,
        provider_name: str = "mock",
        model_name: str = "mock-research-model",
        allowed_tools: tuple[str, ...] | None = None,
        max_model_turns: int = 4,
        max_tool_calls: int = 8,
    ) -> None:
        self._client = client
        self._tool_definitions = tool_definitions
        self._prompt_registry = prompt_registry
        self._pricing = pricing
        self._provider_name_value = provider_name
        self._model_name_value = model_name
        self._max_model_turns = max_model_turns
        self._max_tool_calls = max_tool_calls
        self._allowed_tools = allowed_tools

    @property
    @abstractmethod
    def prompt_name(self) -> str:
        """Return the prompt name rendered for this role."""

    @property
    @abstractmethod
    def output_model(self) -> type[BaseModel]:
        """Return the structured output model for this role."""

    @property
    @abstractmethod
    def tool_names(self) -> tuple[str, ...]:
        """Return the tool names this role is allowed to call."""

    @abstractmethod
    def _convert_output(
        self,
        output: BaseModel,
        task: TaskNode,
        state: ResearchState,
        evidence: list[EvidenceItem],
    ) -> AgentResult:
        """Convert validated structured output into an AgentResult."""

    async def execute(
        self,
        task: TaskNode,
        state: ResearchState,
        context: AgentContext,
    ) -> AgentResult:
        metrics = LLMMetrics()
        evidence: list[EvidenceItem] = []
        tool_results: list[ToolResult] = []
        tool_calls_used = 0

        rendered = self._prompt_registry.render(
            self.prompt_name,
            {
                "objective": state.goal.objective,
                "market": state.goal.market,
                "category": state.goal.category,
                "task": task.description,
                "state_context": self._state_context(state),
                "json_schema": json.dumps(
                    self.output_model.model_json_schema(),
                    sort_keys=True,
                ),
            },
        )
        self._record(
            context,
            EventType.PROMPT_RENDERED,
            actor=self.role.value,
            task_id=task.task_id,
            output_summary=rendered.text[:500],
            metadata={
                "prompt_name": rendered.name,
                "prompt_version": rendered.version,
                "prompt_hash": rendered.prompt_hash,
            },
        )

        messages: list[LLMMessage] = [
            LLMMessage(
                role=LLMMessageRole.SYSTEM,
                content=(
                    "You are a precise MarketPilot research agent. "
                    "Before producing your final answer, call the available research tools "
                    "to collect observable evidence. Do not answer from memory. "
                    "After tool observations, return only valid JSON matching the requested schema."
                    if self.tool_names
                    else "You are a precise MarketPilot decision agent. "
                    "Return only valid JSON matching the requested schema."
                ),
            ),
            LLMMessage(role=LLMMessageRole.USER, content=rendered.text),
        ]

        for _turn in range(self._max_model_turns):
            request = LLMRequest(
                provider=self._provider_name(),
                model=self._model_name(),
                messages=messages,
                temperature=0.0,
                max_output_tokens=1024,
                tools=self._tool_definitions,
                structured_output=LLMStructuredOutputSpec(
                    name=self.output_model.__name__,
                    json_schema=cast(
                        "dict[str, object]",
                        self.output_model.model_json_schema(),
                    ),
                ),
                metadata={
                    "prompt_name": rendered.name,
                    "prompt_version": rendered.version,
                    "prompt_hash": rendered.prompt_hash,
                    "task_id": str(task.task_id),
                    "agent_role": self.role.value,
                    **self._request_metadata(task, state),
                },
            )
            self._record(
                context,
                EventType.LLM_REQUESTED,
                actor=self.role.value,
                task_id=task.task_id,
                input_summary=f"messages={len(messages)}; tools={len(self._tool_definitions)}",
                metadata={
                    "provider": request.provider,
                    "model": request.model,
                    "prompt_name": rendered.name,
                    "prompt_version": rendered.version,
                    "prompt_hash": rendered.prompt_hash,
                },
            )

            try:
                response = await self._client.generate(request)
            except LLMRetryExhaustedError as exc:
                metrics = self._failed_metrics(metrics, exc.attempts)
                self._record(
                    context,
                    EventType.LLM_FAILED,
                    actor=self.role.value,
                    task_id=task.task_id,
                    output_summary=exc.message,
                    metadata={
                        "provider": request.provider,
                        "model": request.model,
                        "attempts": exc.attempts,
                        "error_category": exc.category.value,
                    },
                )
                return AgentResult(
                    status=AgentStatus.FAILED,
                    confidence=0.0,
                    error=AgentError(code="LLM_RETRY_EXHAUSTED", message=exc.message),
                    llm_metrics=metrics,
                    tool_calls=tool_results,
                )
            except LLMError as exc:
                metrics = self._failed_metrics(metrics, 1)
                self._record(
                    context,
                    EventType.LLM_FAILED,
                    actor=self.role.value,
                    task_id=task.task_id,
                    output_summary=exc.message,
                    metadata={
                        "provider": request.provider,
                        "model": request.model,
                        "error_category": exc.category.value,
                    },
                )
                return AgentResult(
                    status=AgentStatus.FAILED,
                    confidence=0.0,
                    error=AgentError(code=exc.category.value, message=exc.message),
                    llm_metrics=metrics,
                    tool_calls=tool_results,
                )

            metrics = self._successful_metrics(metrics, response)
            self._record(
                context,
                EventType.LLM_COMPLETED,
                actor=self.role.value,
                task_id=task.task_id,
                output_summary=f"finish_reason={response.finish_reason.value}",
                duration_ms=response.usage.latency_ms,
                metadata={
                    "provider": response.provider,
                    "model": response.model,
                    "prompt_name": rendered.name,
                    "prompt_version": rendered.version,
                    "prompt_hash": rendered.prompt_hash,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.total_tokens,
                    "estimated_cost": response.usage.estimated_cost,
                    "attempts": response.attempts,
                },
            )
            if response.attempts > 1:
                self._record(
                    context,
                    EventType.LLM_RETRIED,
                    actor=self.role.value,
                    task_id=task.task_id,
                    output_summary=f"attempts={response.attempts}",
                    metadata={"attempts": response.attempts},
                )

            if response.tool_calls:
                messages.append(
                    LLMMessage(
                        role=LLMMessageRole.ASSISTANT,
                        content=response.content,
                        tool_calls=response.tool_calls,
                    )
                )
                for call in response.tool_calls:
                    self._record(
                        context,
                        EventType.TOOL_REQUESTED_BY_MODEL,
                        actor=self.role.value,
                        task_id=task.task_id,
                        output_summary=call.name,
                        metadata={"tool_name": call.name, "call_id": call.call_id},
                    )
                    if call.name not in self._effective_tool_names():
                        return self._invalid_tool_result(
                            task,
                            tool_results,
                            metrics,
                            f"tool not allowed for {self.role.value}: {call.name}",
                        )
                    if tool_calls_used >= self._max_tool_calls:
                        return self._limit_result(
                            task,
                            tool_results,
                            metrics,
                            "maximum tool calls exceeded",
                        )
                    if context.tool_executor is None:
                        return self._invalid_tool_result(
                            task,
                            tool_results,
                            metrics,
                            "tool executor is not configured",
                        )
                    result = await context.tool_executor(
                        ToolInput(tool_name=call.name, arguments=call.arguments)
                    )
                    tool_results.append(result)
                    tool_calls_used += 1
                    if result.succeeded and result.output is not None:
                        evidence.append(
                            EvidenceItem(
                                evidence_id=uuid5(
                                    NAMESPACE_URL,
                                    f"marketpilot:evidence:{task.run_id}:{result.tool_call_id}",
                                ),
                                run_id=task.run_id,
                                task_id=task.task_id,
                                source_type=result.output.evidence_source_type
                                or EvidenceSourceType.MOCK,
                                source_uri=result.output.source_uri,
                                retrieved_at=result.started_at,
                                content_hash=sha256(result.output.observation.encode()).hexdigest(),
                                excerpt=result.output.observation,
                                confidence=result.output.confidence,
                                related_entity=None,
                                extraction_method="llm_tool_observation",
                                tool_call_id=result.tool_call_id,
                                snapshot_id=result.output.snapshot_id,
                            )
                        )
                    messages.append(
                        LLMMessage(
                            role=LLMMessageRole.TOOL,
                            content=self._tool_message_content(result),
                            tool_call_id=call.call_id,
                            tool_name=call.name,
                        )
                    )
                continue

            try:
                output = parse_structured_output(response.content, self.output_model)
            except LLMStructuredOutputError as exc:
                self._record(
                    context,
                    EventType.STRUCTURED_OUTPUT_REJECTED,
                    actor=self.role.value,
                    task_id=task.task_id,
                    output_summary=exc.message,
                    metadata={"prompt_name": rendered.name},
                )
                return AgentResult(
                    status=AgentStatus.FAILED,
                    confidence=0.0,
                    error=AgentError(code="STRUCTURED_OUTPUT_INVALID", message=exc.message),
                    llm_metrics=metrics,
                    tool_calls=tool_results,
                )
            self._record(
                context,
                EventType.STRUCTURED_OUTPUT_VALIDATED,
                actor=self.role.value,
                task_id=task.task_id,
                output_summary=output.model_dump_json(),
                metadata={"prompt_name": rendered.name},
            )
            converted = self._convert_output(output, task, state, evidence)
            return converted.model_copy(update={"llm_metrics": metrics, "tool_calls": tool_results})

        return AgentResult(
            status=AgentStatus.FAILED,
            confidence=0.0,
            error=AgentError(
                code="MAX_MODEL_TURNS_EXCEEDED",
                message=f"LLM agent exceeded {self._max_model_turns} model turns",
            ),
            llm_metrics=metrics,
            tool_calls=tool_results,
        )

    def _provider_name(self) -> str:
        return self._provider_name_value

    def _model_name(self) -> str:
        return self._model_name_value

    def _request_metadata(
        self,
        task: TaskNode,
        state: ResearchState,
    ) -> dict[str, str | int | float | bool | None]:
        return {}

    def _state_context(self, state: ResearchState) -> str:
        return json.dumps(
            {
                "findings": [
                    {"id": str(item.finding_id), "claim": item.claim}
                    for item in state.findings.values()
                ],
                "evidence": [
                    {"id": str(item.evidence_id), "source_uri": item.source_uri}
                    for item in state.evidence.values()
                ],
                "candidates": [
                    {"id": str(item.candidate_id), "name": item.name}
                    for item in state.candidates.values()
                ],
                "risks": [
                    {"id": str(item.risk_id), "label": item.label}
                    for item in state.risk_flags.values()
                ],
            },
            indent=2,
            sort_keys=True,
        )

    def _tool_message_content(self, result: ToolResult) -> str:
        if result.output is not None:
            return result.output.summary
        return result.error_message or "tool failed"

    def _effective_tool_names(self) -> set[str]:
        return set(self._allowed_tools) if self._allowed_tools is not None else set(self.tool_names)

    def _record(
        self,
        context: AgentContext,
        event_type: EventType,
        actor: str,
        task_id: UUID | None = None,
        input_summary: str | None = None,
        output_summary: str | None = None,
        metadata: dict[str, str | int | float | bool | None] | None = None,
        duration_ms: int = 0,
    ) -> None:
        if context.trajectory is None:
            return
        context.trajectory.record(
            event_type,
            actor=actor,
            task_id=task_id,
            input_summary=input_summary,
            output_summary=output_summary,
            metadata=metadata,
            duration_ms=duration_ms,
        )

    def _successful_metrics(self, metrics: LLMMetrics, response: LLMResponse) -> LLMMetrics:
        estimated_cost = response.usage.estimated_cost
        if metrics.llm_estimated_cost is not None and estimated_cost is not None:
            total_cost = metrics.llm_estimated_cost + estimated_cost
        elif metrics.llm_estimated_cost is None and estimated_cost is None:
            total_cost = None
        else:
            total_cost = metrics.llm_estimated_cost or estimated_cost
        return metrics.model_copy(
            update={
                "llm_calls": metrics.llm_calls + response.attempts,
                "llm_input_tokens": metrics.llm_input_tokens + response.usage.input_tokens,
                "llm_output_tokens": metrics.llm_output_tokens + response.usage.output_tokens,
                "llm_total_tokens": metrics.llm_total_tokens + response.usage.total_tokens,
                "llm_latency_ms": metrics.llm_latency_ms + response.usage.latency_ms,
                "llm_estimated_cost": total_cost,
                "llm_retry_count": metrics.llm_retry_count + response.attempts - 1,
            }
        )

    def _failed_metrics(self, metrics: LLMMetrics, attempts: int) -> LLMMetrics:
        return metrics.model_copy(
            update={
                "llm_calls": metrics.llm_calls + attempts,
                "llm_failed_calls": metrics.llm_failed_calls + attempts,
                "llm_retry_count": metrics.llm_retry_count + max(attempts - 1, 0),
            }
        )

    def _invalid_tool_result(
        self,
        task: TaskNode,
        tool_results: list[ToolResult],
        metrics: LLMMetrics,
        message: str,
    ) -> AgentResult:
        return AgentResult(
            status=AgentStatus.FAILED,
            confidence=0.0,
            error=AgentError(code="INVALID_TOOL_CALL", message=message),
            llm_metrics=metrics,
            tool_calls=tool_results,
        )

    def _limit_result(
        self,
        task: TaskNode,
        tool_results: list[ToolResult],
        metrics: LLMMetrics,
        message: str,
    ) -> AgentResult:
        return AgentResult(
            status=AgentStatus.FAILED,
            confidence=0.0,
            error=AgentError(code="EXECUTION_LIMIT_EXCEEDED", message=message),
            llm_metrics=metrics,
            tool_calls=tool_results,
        )
