"""Typed, provider-neutral LLM request and response models."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

from marketpilot.tools.base import ToolArguments


class LLMMessageRole(StrEnum):
    """Normalized chat roles."""

    SYSTEM = "SYSTEM"
    USER = "USER"
    ASSISTANT = "ASSISTANT"
    TOOL = "TOOL"


class LLMFinishReason(StrEnum):
    """Normalized completion reasons."""

    STOP = "STOP"
    TOOL_CALLS = "TOOL_CALLS"
    LENGTH = "LENGTH"
    CONTENT_FILTER = "CONTENT_FILTER"
    UNKNOWN = "UNKNOWN"


class LLMToolCall(BaseModel):
    """A normalized model-requested tool invocation."""

    model_config = ConfigDict(frozen=True)

    call_id: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=100)
    arguments: ToolArguments


class LLMToolDefinition(BaseModel):
    """A provider-neutral tool contract exposed to the model."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=2000)
    input_schema: dict[str, object] = Field(default_factory=dict)


class LLMStructuredOutputSpec(BaseModel):
    """A normalized JSON-schema output contract."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1, max_length=200)
    json_schema: dict[str, object] = Field(min_length=1)


class LLMMessage(BaseModel):
    """A normalized chat message."""

    model_config = ConfigDict(frozen=True)

    role: LLMMessageRole
    content: str | None = Field(default=None, max_length=20000)
    tool_calls: list[LLMToolCall] = Field(default_factory=list)
    tool_call_id: str | None = Field(default=None, min_length=1, max_length=200)
    tool_name: str | None = Field(default=None, min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_tool_message(self) -> "LLMMessage":
        if self.role is LLMMessageRole.TOOL and self.tool_call_id is None:
            raise ValueError("tool messages require tool_call_id")
        return self


class LLMUsage(BaseModel):
    """Normalized usage and cost metadata for one model call."""

    model_config = ConfigDict(frozen=True)

    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    cached_tokens: int | None = Field(default=None, ge=0)
    latency_ms: int = Field(ge=0)
    estimated_cost: float | None = Field(default=None, ge=0)


class LLMRequest(BaseModel):
    """A provider-neutral model request."""

    model_config = ConfigDict(frozen=True)

    provider: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=200)
    messages: list[LLMMessage] = Field(min_length=1)
    temperature: float = Field(default=0.0, ge=0, le=2)
    max_output_tokens: int = Field(default=1024, ge=1)
    tools: list[LLMToolDefinition] = Field(default_factory=list)
    structured_output: LLMStructuredOutputSpec | None = None
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    """A provider-neutral model response."""

    model_config = ConfigDict(frozen=True)

    response_id: str = Field(min_length=1, max_length=200)
    provider: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=200)
    finish_reason: LLMFinishReason
    content: str | None = Field(default=None, max_length=20000)
    tool_calls: list[LLMToolCall] = Field(default_factory=list)
    usage: LLMUsage
    attempts: int = Field(default=1, ge=1)


class LLMModelConfig(BaseModel):
    """Runtime configuration for one LLM provider/model."""

    model_config = ConfigDict(frozen=True)

    provider: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=200)
    api_key: SecretStr | None = None
    base_url: str | None = None
    timeout_seconds: float = Field(default=30.0, gt=0)
    max_retries: int = Field(default=2, ge=0)
    temperature: float = Field(default=0.0, ge=0, le=2)
    max_output_tokens: int = Field(default=1024, ge=1)


class LLMMetrics(BaseModel):
    """Aggregated LLM metrics for one agent execution."""

    model_config = ConfigDict(frozen=True)

    llm_calls: int = Field(default=0, ge=0)
    llm_input_tokens: int = Field(default=0, ge=0)
    llm_output_tokens: int = Field(default=0, ge=0)
    llm_total_tokens: int = Field(default=0, ge=0)
    llm_latency_ms: int = Field(default=0, ge=0)
    llm_estimated_cost: float | None = Field(default=None, ge=0)
    llm_failed_calls: int = Field(default=0, ge=0)
    llm_retry_count: int = Field(default=0, ge=0)
