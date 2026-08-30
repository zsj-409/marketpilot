"""LLM agent runtime tests."""

from uuid import UUID, uuid4

from marketpilot.agents.base import AgentContext
from marketpilot.agents.llm import LLMMarketResearchAgent
from marketpilot.domain.enums import ToolResultStatus
from marketpilot.domain.goals import ResearchGoal
from marketpilot.domain.state import ResearchState
from marketpilot.llm.errors import LLMRateLimitError
from marketpilot.llm.models import (
    LLMFinishReason,
    LLMResponse,
    LLMToolCall,
    LLMToolDefinition,
    LLMUsage,
)
from marketpilot.llm.providers.mock import MockLLMClient
from marketpilot.observability.trajectory import TrajectoryRecorder
from marketpilot.prompts.templates import build_default_prompt_registry
from marketpilot.tools.base import ToolArguments, ToolInput, ToolOutput, ToolResult
from tests.conftest import make_task


def _state_and_task() -> tuple[ResearchState, UUID]:
    run_id = str(uuid4())
    goal = ResearchGoal(
        market="US",
        category="pet supplies",
        objective="Find promising pet products",
    )
    state = ResearchState(run_id=run_id, goal=goal, budget=goal.budget)
    task = make_task(run_id)
    state.add_task(task)
    return state, state.run_id


async def _tool_executor(tool_input: ToolInput) -> ToolResult:
    return ToolResult(
        tool_name=tool_input.tool_name,
        status=ToolResultStatus.SUCCESS,
        output=ToolOutput(
            summary="mock observation",
            source_uri="mock://observation",
            observation="Deterministic observation",
            confidence=0.8,
        ),
        latency_ms=0,
    )


def _tool_response(name: str, call_id: str) -> LLMResponse:
    return LLMResponse(
        response_id=f"mock-{call_id}",
        provider="mock",
        model="mock-research-model",
        finish_reason=LLMFinishReason.TOOL_CALLS,
        content=None,
        tool_calls=[
            LLMToolCall(
                call_id=call_id,
                name=name,
                arguments=ToolArguments(category="pet supplies", market="US"),
            )
        ],
        usage=LLMUsage(input_tokens=10, output_tokens=0, total_tokens=10, latency_ms=0),
    )


def _final_response(content: str) -> LLMResponse:
    return LLMResponse(
        response_id="mock-final",
        provider="mock",
        model="mock-research-model",
        finish_reason=LLMFinishReason.STOP,
        content=content,
        tool_calls=[],
        usage=LLMUsage(input_tokens=20, output_tokens=40, total_tokens=60, latency_ms=0),
    )


def _agent(client: MockLLMClient) -> LLMMarketResearchAgent:
    return LLMMarketResearchAgent(
        client=client,
        tool_definitions=[
            LLMToolDefinition(
                name="get_market_signal",
                description="mock signal",
                input_schema={"type": "object"},
            )
        ],
        prompt_registry=build_default_prompt_registry(),
    )


async def test_llm_agent_tool_loop_produces_finding() -> None:
    state, run_id = _state_and_task()
    client = MockLLMClient(
        responses_by_prompt={
            "market_research": [
                _tool_response("get_market_signal", "call-1"),
                _final_response('{"claim":"Demand is rising.","confidence":0.8}'),
            ]
        }
    )
    context = AgentContext(
        run_id=run_id,
        tool_executor=_tool_executor,
        trajectory=TrajectoryRecorder(run_id=run_id),
    )
    result = await _agent(client).execute(state.tasks[next(iter(state.tasks))], state, context)
    assert result.status.value == "SUCCEEDED"
    assert len(result.findings) == 1
    assert len(result.evidence) == 1
    assert result.llm_metrics is not None
    assert result.llm_metrics.llm_calls == 2


async def test_llm_agent_rejects_unknown_tool() -> None:
    state, run_id = _state_and_task()
    client = MockLLMClient(
        responses_by_prompt={"market_research": [_tool_response("unknown_tool", "call-1")]}
    )
    context = AgentContext(
        run_id=run_id,
        tool_executor=_tool_executor,
        trajectory=TrajectoryRecorder(run_id=run_id),
    )
    result = await _agent(client).execute(state.tasks[next(iter(state.tasks))], state, context)
    assert result.status.value == "FAILED"
    assert result.error is not None
    assert result.error.code == "INVALID_TOOL_CALL"


async def test_llm_agent_rejects_malformed_structured_output() -> None:
    state, run_id = _state_and_task()
    client = MockLLMClient(responses_by_prompt={"market_research": [_final_response('{"claim":')]})
    context = AgentContext(
        run_id=run_id,
        tool_executor=_tool_executor,
        trajectory=TrajectoryRecorder(run_id=run_id),
    )
    result = await _agent(client).execute(state.tasks[next(iter(state.tasks))], state, context)
    assert result.status.value == "FAILED"
    assert result.error is not None
    assert result.error.code == "STRUCTURED_OUTPUT_INVALID"


async def test_llm_agent_surfaces_provider_failure() -> None:
    state, run_id = _state_and_task()
    client = MockLLMClient(responses=[LLMRateLimitError("slow down")])
    context = AgentContext(
        run_id=run_id,
        tool_executor=_tool_executor,
        trajectory=TrajectoryRecorder(run_id=run_id),
    )
    result = await _agent(client).execute(state.tasks[next(iter(state.tasks))], state, context)
    assert result.status.value == "FAILED"
    assert result.error is not None
    assert result.error.code == "RATE_LIMIT"
