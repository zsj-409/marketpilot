"""Provider-neutral LLM client contract."""

from abc import ABC, abstractmethod

from marketpilot.llm.models import LLMRequest, LLMResponse


class LLMClient(ABC):
    """A normalized asynchronous LLM interface."""

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a normalized response for a normalized request."""
