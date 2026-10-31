"""Typed input errors and deterministic error classification (Phase 1)."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class InputErrorCategory(StrEnum):
    """Machine-readable category for input-layer failures."""

    PARSE = "PARSE"
    VALIDATION = "VALIDATION"
    NORMALIZATION = "NORMALIZATION"
    UNTRUSTED_CONTENT = "UNTRUSTED_CONTENT"
    REPLAY_MISS = "REPLAY_MISS"
    BUDGET = "BUDGET"
    TIMEOUT = "TIMEOUT"
    PERMANENT = "PERMANENT"


class InputError(Exception):
    """A typed input-layer failure with a machine-readable category."""

    def __init__(self, category: str, message: str) -> None:
        super().__init__(message)
        self.category = InputErrorCategory(category)
        self.message = message


class ErrorClassification(BaseModel):
    """Deterministic classification of one failure."""

    model_config = ConfigDict(frozen=True)

    category: InputErrorCategory
    retryable: bool
    message: str = Field(default="", max_length=2000)


def classify_error(error: Exception) -> ErrorClassification:
    """Map any exception to a deterministic error classification.

    Used by the input layer and by Phase 4's controller to decide retry,
    stop, or human-review routing.
    """
    if isinstance(error, InputError):
        return ErrorClassification(
            category=error.category,
            retryable=error.category
            in {
                InputErrorCategory.PARSE,
                InputErrorCategory.NORMALIZATION,
                InputErrorCategory.TIMEOUT,
            },
            message=error.message[:2000],
        )
    message = str(error) or type(error).__name__
    lowered = message.lower()
    if "timeout" in lowered or "timed out" in lowered:
        return ErrorClassification(
            category=InputErrorCategory.TIMEOUT, retryable=True, message=message[:2000]
        )
    if "replay miss" in lowered or "replay_miss" in lowered:
        return ErrorClassification(
            category=InputErrorCategory.REPLAY_MISS, retryable=False, message=message[:2000]
        )
    if "budget" in lowered or "exhausted" in lowered:
        return ErrorClassification(
            category=InputErrorCategory.BUDGET, retryable=False, message=message[:2000]
        )
    if "parse" in lowered or "cannot" in lowered or "invalid" in lowered:
        return ErrorClassification(
            category=InputErrorCategory.VALIDATION, retryable=False, message=message[:2000]
        )
    return ErrorClassification(
        category=InputErrorCategory.PERMANENT, retryable=False, message=message[:2000]
    )


class ErrorClassifier:
    """Small wrapper for classify_error to match the v1 utility-object pattern."""

    def classify(self, error: Exception) -> ErrorClassification:
        return classify_error(error)
