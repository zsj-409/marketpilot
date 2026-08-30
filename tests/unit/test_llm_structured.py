"""Structured output parsing tests."""

import pytest
from pydantic import BaseModel, Field

from marketpilot.llm.errors import LLMStructuredOutputError
from marketpilot.llm.structured import parse_structured_output


class SampleOutput(BaseModel):
    claim: str = Field(min_length=3)
    confidence: float = Field(ge=0, le=1)


def test_valid_output_is_parsed() -> None:
    output = parse_structured_output('{"claim":"valid claim","confidence":0.8}', SampleOutput)
    assert output.claim == "valid claim"
    assert output.confidence == 0.8


def test_invalid_json_is_rejected() -> None:
    with pytest.raises(LLMStructuredOutputError):
        parse_structured_output('{"claim":', SampleOutput)


def test_schema_violation_is_rejected() -> None:
    with pytest.raises(LLMStructuredOutputError):
        parse_structured_output('{"claim":"x","confidence":1.5}', SampleOutput)


def test_empty_output_is_rejected() -> None:
    with pytest.raises(LLMStructuredOutputError):
        parse_structured_output("", SampleOutput)
