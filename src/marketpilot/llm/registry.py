"""LLM client registry and provider factories."""

from collections.abc import Callable

from marketpilot.llm.base import LLMClient
from marketpilot.llm.models import LLMModelConfig

LLMClientFactory = Callable[[LLMModelConfig], LLMClient]


class LLMClientRegistry:
    """Register and create provider clients by provider name."""

    def __init__(self) -> None:
        self._factories: dict[str, LLMClientFactory] = {}

    def register(self, provider: str, factory: LLMClientFactory) -> None:
        if provider in self._factories:
            raise ValueError(f"LLM provider already registered: {provider}")
        self._factories[provider] = factory

    def create(self, config: LLMModelConfig) -> LLMClient:
        try:
            factory = self._factories[config.provider]
        except KeyError as exc:
            raise ValueError(f"unknown LLM provider: {config.provider}") from exc
        return factory(config)

    def providers(self) -> list[str]:
        return sorted(self._factories)


def build_default_llm_client_registry() -> LLMClientRegistry:
    """Build the default mock and OpenAI provider registry."""

    from marketpilot.llm.providers.mock import MockLLMClient, build_demo_llm_responses
    from marketpilot.llm.providers.openai import OpenAIChatClient

    registry = LLMClientRegistry()
    registry.register(
        "mock", lambda config: MockLLMClient(responses_by_prompt=build_demo_llm_responses())
    )
    registry.register("openai", lambda config: OpenAIChatClient(config))
    return registry
