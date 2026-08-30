"""Typed LLM provider errors."""

from enum import StrEnum


class LLMErrorCategory(StrEnum):
    """Machine-readable provider error categories."""

    TIMEOUT = "TIMEOUT"
    RATE_LIMIT = "RATE_LIMIT"
    AUTHENTICATION = "AUTHENTICATION"
    INVALID_REQUEST = "INVALID_REQUEST"
    TRANSIENT_PROVIDER = "TRANSIENT_PROVIDER"
    PERMANENT_PROVIDER = "PERMANENT_PROVIDER"
    STRUCTURED_OUTPUT = "STRUCTURED_OUTPUT"
    RETRY_EXHAUSTED = "RETRY_EXHAUSTED"


def sanitize_message(message: str, secrets: list[str]) -> str:
    """Remove configured secrets from provider error text."""

    sanitized = message
    for secret in secrets:
        if secret:
            sanitized = sanitized.replace(secret, "[REDACTED]")
    return sanitized


class LLMError(Exception):
    """Base class for normalized LLM failures."""

    category: LLMErrorCategory
    retryable: bool

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class LLMTimeoutError(LLMError):
    category = LLMErrorCategory.TIMEOUT
    retryable = True


class LLMRateLimitError(LLMError):
    category = LLMErrorCategory.RATE_LIMIT
    retryable = True


class LLMAuthenticationError(LLMError):
    category = LLMErrorCategory.AUTHENTICATION
    retryable = False


class LLMInvalidRequestError(LLMError):
    category = LLMErrorCategory.INVALID_REQUEST
    retryable = False


class LLMTransientProviderError(LLMError):
    category = LLMErrorCategory.TRANSIENT_PROVIDER
    retryable = True


class LLMPermanentProviderError(LLMError):
    category = LLMErrorCategory.PERMANENT_PROVIDER
    retryable = False


class LLMStructuredOutputError(LLMError):
    category = LLMErrorCategory.STRUCTURED_OUTPUT
    retryable = False


class LLMRetryExhaustedError(LLMError):
    category = LLMErrorCategory.RETRY_EXHAUSTED
    retryable = False

    def __init__(self, message: str, attempts: int, cause: LLMError) -> None:
        super().__init__(message)
        self.attempts = attempts
        self.cause = cause
