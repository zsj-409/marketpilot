"""API budget enforcement for LLM calls."""

from marketpilot.llm.base import LLMClient
from marketpilot.llm.errors import LLMAuthenticationError, LLMError, LLMPermanentProviderError
from marketpilot.llm.models import LLMRequest, LLMResponse


class LLMBudgetGuard(LLMClient):
    """Enforce call, token, and output-token limits around an LLM client."""

    def __init__(
        self,
        client: LLMClient,
        *,
        max_calls: int,
        max_output_tokens: int,
    ) -> None:
        self._client = client
        self._max_calls = max_calls
        self._max_output_tokens = max_output_tokens
        self.calls = 0

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if self.calls >= self._max_calls:
            raise LLMPermanentProviderError("LLM call budget exhausted")
        self.calls += 1
        bounded_request = request.model_copy(
            update={"max_output_tokens": min(request.max_output_tokens, self._max_output_tokens)}
        )
        response = await self._client.generate(bounded_request)
        return response

    def reset(self) -> None:
        self.calls = 0

    def sanitize(self, error: LLMError) -> LLMError:
        if isinstance(error, LLMAuthenticationError):
            return LLMAuthenticationError("[REDACTED] authentication failure")
        return error
