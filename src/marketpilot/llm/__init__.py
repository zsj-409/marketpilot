"""Provider-neutral LLM runtime contracts."""

from marketpilot.llm.base import LLMClient
from marketpilot.llm.errors import (
    LLMAuthenticationError,
    LLMError,
    LLMInvalidRequestError,
    LLMPermanentProviderError,
    LLMRateLimitError,
    LLMRetryExhaustedError,
    LLMStructuredOutputError,
    LLMTimeoutError,
    LLMTransientProviderError,
)
from marketpilot.llm.models import (
    LLMFinishReason,
    LLMMessage,
    LLMMessageRole,
    LLMModelConfig,
    LLMRequest,
    LLMResponse,
    LLMStructuredOutputSpec,
    LLMToolCall,
    LLMToolDefinition,
    LLMUsage,
)
from marketpilot.llm.pricing import ModelPrice, PricingCalculator
from marketpilot.llm.registry import LLMClientRegistry, build_default_llm_client_registry
from marketpilot.llm.retry import RetryableLLMClient, RetryPolicy
from marketpilot.llm.structured import parse_structured_output

__all__ = [
    "LLMAuthenticationError",
    "LLMClient",
    "LLMClientRegistry",
    "LLMError",
    "LLMFinishReason",
    "LLMInvalidRequestError",
    "LLMMessage",
    "LLMMessageRole",
    "LLMModelConfig",
    "LLMPermanentProviderError",
    "LLMRateLimitError",
    "LLMRequest",
    "LLMResponse",
    "LLMRetryExhaustedError",
    "LLMStructuredOutputError",
    "LLMStructuredOutputSpec",
    "LLMTimeoutError",
    "LLMToolCall",
    "LLMToolDefinition",
    "LLMTransientProviderError",
    "LLMUsage",
    "ModelPrice",
    "PricingCalculator",
    "RetryPolicy",
    "RetryableLLMClient",
    "build_default_llm_client_registry",
    "parse_structured_output",
]
