"""Structured-output parsing and validation."""

import json
from typing import Any

from pydantic import BaseModel, ValidationError

from marketpilot.llm.errors import LLMStructuredOutputError


def parse_structured_output[ModelT: BaseModel](
    content: str | None,
    output_model: type[ModelT],
) -> ModelT:
    """Parse and validate JSON content into a typed model."""

    if content is None or not content.strip():
        raise LLMStructuredOutputError("LLM returned empty structured output")
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LLMStructuredOutputError(f"invalid JSON from LLM: {exc.msg}") from exc
    try:
        return output_model.model_validate(payload)
    except ValidationError as exc:
        first_error: Any = exc.errors()[0] if exc.errors() else {}
        raise LLMStructuredOutputError(
            "structured output schema validation failed: "
            f"{exc.error_count()} error(s); first={first_error}"
        ) from exc
