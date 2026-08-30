"""Bounded retry policy for LLM calls."""

import asyncio
from collections.abc import Awaitable, Callable

from pydantic import BaseModel, ConfigDict, Field

from marketpilot.llm.base import LLMClient
from marketpilot.llm.errors import LLMError, LLMRetryExhaustedError
from marketpilot.llm.models import LLMRequest, LLMResponse

Sleeper = Callable[[float], Awaitable[None]]


class RetryPolicy(BaseModel):
    """Retry limits and backoff configuration."""

    model_config = ConfigDict(frozen=True)

    max_attempts: int = Field(default=3, ge=1)
    initial_delay_seconds: float = Field(default=0.0, ge=0)
    backoff_factor: float = Field(default=1.0, ge=1)


async def _default_sleep(seconds: float) -> None:
    await asyncio.sleep(seconds)


class RetryableLLMClient(LLMClient):
    """Wrap an LLM client with bounded, typed retries."""

    def __init__(
        self,
        client: LLMClient,
        policy: RetryPolicy | None = None,
        sleeper: Sleeper | None = None,
    ) -> None:
        self._client = client
        self._policy = policy or RetryPolicy()
        self._sleeper = sleeper or _default_sleep

    async def generate(self, request: LLMRequest) -> LLMResponse:
        attempts = 0
        delay = self._policy.initial_delay_seconds
        last_error: LLMError | None = None
        while attempts < self._policy.max_attempts:
            attempts += 1
            try:
                response = await self._client.generate(request)
                return response.model_copy(update={"attempts": attempts})
            except LLMError as exc:
                last_error = exc
                if not exc.retryable:
                    raise
                if attempts >= self._policy.max_attempts:
                    break
                await self._sleeper(delay)
                delay *= self._policy.backoff_factor
        assert last_error is not None
        raise LLMRetryExhaustedError(
            f"LLM retry exhausted after {attempts} attempts: {last_error.message}",
            attempts=attempts,
            cause=last_error,
        )
