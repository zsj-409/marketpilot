"""LLM retry policy tests."""

import pytest

from marketpilot.llm.base import LLMClient
from marketpilot.llm.errors import (
    LLMAuthenticationError,
    LLMError,
    LLMRateLimitError,
    LLMRetryExhaustedError,
)
from marketpilot.llm.models import (
    LLMFinishReason,
    LLMRequest,
    LLMResponse,
    LLMUsage,
)
from marketpilot.llm.retry import RetryableLLMClient, RetryPolicy


class ScriptedErrorClient(LLMClient):
    def __init__(self, errors: list[LLMError]) -> None:
        self._errors = errors

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if self._errors:
            raise self._errors.pop(0)
        return LLMResponse(
            response_id="ok",
            provider="mock",
            model="mock-model",
            finish_reason=LLMFinishReason.STOP,
            content="ok",
            usage=LLMUsage(input_tokens=1, output_tokens=1, total_tokens=2, latency_ms=0),
        )


def _request() -> LLMRequest:
    from marketpilot.llm.models import LLMMessage, LLMMessageRole

    return LLMRequest(
        provider="mock",
        model="mock-model",
        messages=[LLMMessage(role=LLMMessageRole.USER, content="hi")],
    )


async def test_retryable_error_is_retried() -> None:
    client = RetryableLLMClient(
        ScriptedErrorClient([LLMRateLimitError("slow down")]),
        policy=RetryPolicy(max_attempts=3, initial_delay_seconds=0),
    )
    response = await client.generate(_request())
    assert response.attempts == 2
    assert response.content == "ok"


async def test_permanent_error_is_not_retried() -> None:
    client = RetryableLLMClient(
        ScriptedErrorClient([LLMAuthenticationError("bad key")]),
        policy=RetryPolicy(max_attempts=3, initial_delay_seconds=0),
    )
    with pytest.raises(LLMAuthenticationError):
        await client.generate(_request())


async def test_retry_exhaustion_is_typed() -> None:
    client = RetryableLLMClient(
        ScriptedErrorClient([LLMRateLimitError("slow down"), LLMRateLimitError("still slow")]),
        policy=RetryPolicy(max_attempts=2, initial_delay_seconds=0),
    )
    with pytest.raises(LLMRetryExhaustedError) as excinfo:
        await client.generate(_request())
    assert excinfo.value.attempts == 2
