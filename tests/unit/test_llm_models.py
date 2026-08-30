"""LLM contract model tests."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from marketpilot.llm.models import (
    LLMFinishReason,
    LLMMessage,
    LLMMessageRole,
    LLMRequest,
    LLMResponse,
    LLMStructuredOutputSpec,
    LLMUsage,
)


def test_request_requires_messages() -> None:
    with pytest.raises(ValidationError):
        LLMRequest(provider="mock", model="mock-model", messages=[])


def test_tool_message_requires_tool_call_id() -> None:
    with pytest.raises(ValidationError):
        LLMMessage(role=LLMMessageRole.TOOL, content="result")


def test_structured_output_spec_is_typed() -> None:
    spec = LLMStructuredOutputSpec(
        name="MarketResearchOutput",
        json_schema={"type": "object", "properties": {}},
    )
    assert spec.name == "MarketResearchOutput"


def test_usage_accounting() -> None:
    usage = LLMUsage(
        input_tokens=10,
        output_tokens=5,
        total_tokens=15,
        latency_ms=3,
        estimated_cost=0.0001,
    )
    assert usage.total_tokens == 15
    assert usage.estimated_cost == 0.0001


def test_response_supports_tool_calls() -> None:
    from marketpilot.llm.models import LLMToolCall
    from marketpilot.tools.base import ToolArguments

    response = LLMResponse(
        response_id="mock-1",
        provider="mock",
        model="mock-model",
        finish_reason=LLMFinishReason.TOOL_CALLS,
        content=None,
        tool_calls=[
            LLMToolCall(
                call_id=str(uuid4()),
                name="web_search",
                arguments=ToolArguments(query="pet supplies"),
            )
        ],
        usage=LLMUsage(input_tokens=1, output_tokens=0, total_tokens=1, latency_ms=0),
    )
    assert response.tool_calls[0].name == "web_search"
