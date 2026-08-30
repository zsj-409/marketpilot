"""Mock LLM provider tests."""

from uuid import uuid4

import pytest

from marketpilot.llm.errors import LLMPermanentProviderError, LLMRateLimitError
from marketpilot.llm.models import (
    LLMFinishReason,
    LLMMessage,
    LLMMessageRole,
    LLMRequest,
    LLMResponse,
    LLMToolCall,
    LLMUsage,
)
from marketpilot.llm.providers.mock import MockLLMClient
from marketpilot.tools.base import ToolArguments


def _request(prompt_name: str = "default") -> LLMRequest:
    return LLMRequest(
        provider="mock",
        model="mock-model",
        messages=[LLMMessage(role=LLMMessageRole.USER, content="hi")],
        metadata={"prompt_name": prompt_name},
    )


def _response(content: str) -> LLMResponse:
    return LLMResponse(
        response_id=str(uuid4()),
        provider="mock",
        model="mock-model",
        finish_reason=LLMFinishReason.STOP,
        content=content,
        usage=LLMUsage(input_tokens=1, output_tokens=1, total_tokens=2, latency_ms=0),
    )


async def test_sequential_responses() -> None:
    client = MockLLMClient(responses=[_response("a"), _response("b")])
    first = await client.generate(_request())
    second = await client.generate(_request())
    assert first.content == "a"
    assert second.content == "b"


async def test_prompt_scoped_responses() -> None:
    client = MockLLMClient(
        responses_by_prompt={
            "market_research": [_response("one"), _response("two")],
            "review_research": [_response("review")],
        }
    )
    assert (await client.generate(_request("market_research"))).content == "one"
    assert (await client.generate(_request("review_research"))).content == "review"
    assert (await client.generate(_request("market_research"))).content == "two"


async def test_scripted_error() -> None:
    client = MockLLMClient(responses=[LLMRateLimitError("slow down")])
    with pytest.raises(LLMRateLimitError):
        await client.generate(_request())


async def test_exhausted_script_raises() -> None:
    client = MockLLMClient(responses=[_response("only")])
    await client.generate(_request())
    with pytest.raises(LLMPermanentProviderError):
        await client.generate(_request())


async def test_tool_call_response() -> None:
    call = LLMToolCall(
        call_id="call-1",
        name="web_search",
        arguments=ToolArguments(query="pet supplies"),
    )
    response = LLMResponse(
        response_id="call-response",
        provider="mock",
        model="mock-model",
        finish_reason=LLMFinishReason.TOOL_CALLS,
        content=None,
        tool_calls=[call],
        usage=LLMUsage(input_tokens=1, output_tokens=0, total_tokens=1, latency_ms=0),
    )
    client = MockLLMClient(responses=[response])
    actual = await client.generate(_request())
    assert actual.tool_calls == [call]
