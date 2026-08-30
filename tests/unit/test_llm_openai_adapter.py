"""OpenAI adapter conversion and error-sanitization tests."""

from types import SimpleNamespace

import httpx
import pytest
from openai import BadRequestError
from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_function_tool_call import (
    ChatCompletionMessageFunctionToolCall,
    Function,
)
from openai.types.completion_usage import CompletionUsage

from marketpilot.llm.errors import LLMInvalidRequestError
from marketpilot.llm.models import (
    LLMFinishReason,
    LLMMessage,
    LLMMessageRole,
    LLMModelConfig,
    LLMRequest,
    LLMStructuredOutputSpec,
    LLMToolDefinition,
)
from marketpilot.llm.providers.openai import OpenAIChatClient


def _completion(content: str | None = None, tool_calls: list | None = None) -> ChatCompletion:
    return ChatCompletion(
        id="chatcmpl-test",
        choices=[
            Choice(
                index=0,
                finish_reason="tool_calls" if tool_calls else "stop",
                message=ChatCompletionMessage(
                    role="assistant",
                    content=content,
                    tool_calls=tool_calls or None,
                ),
            )
        ],
        created=1,
        model="gpt-4o-mini",
        object="chat.completion",
        usage=CompletionUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )


def _client(completion: ChatCompletion) -> OpenAIChatClient:
    config = LLMModelConfig(
        provider="openai",
        model="gpt-4o-mini",
        api_key="super-secret-test-key",  # type: ignore[arg-type]
    )
    adapter = OpenAIChatClient(config)
    captured: dict[str, object] = {}

    async def create(**kwargs: object) -> ChatCompletion:
        captured.update(kwargs)
        return completion

    adapter._client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    adapter._captured = captured  # type: ignore[attr-defined]
    return adapter


def _request(tools: bool = False, structured: bool = False) -> LLMRequest:
    request = LLMRequest(
        provider="openai",
        model="gpt-4o-mini",
        messages=[LLMMessage(role=LLMMessageRole.USER, content="hi")],
    )
    if tools:
        request = request.model_copy(
            update={
                "tools": [
                    LLMToolDefinition(
                        name="web_search", description="search", input_schema={"type": "object"}
                    )
                ]
            }
        )
    if structured:
        request = request.model_copy(
            update={
                "structured_output": LLMStructuredOutputSpec(
                    name="SampleOutput",
                    json_schema={"type": "object", "properties": {}},
                )
            }
        )
    return request


async def test_text_response_conversion() -> None:
    adapter = _client(_completion(content="hello"))
    response = await adapter.generate(_request())
    assert response.content == "hello"
    assert response.finish_reason is LLMFinishReason.STOP
    assert response.usage.input_tokens == 10
    assert response.usage.output_tokens == 5
    assert response.usage.total_tokens == 15


async def test_tool_call_normalization() -> None:
    tool_call = ChatCompletionMessageFunctionToolCall(
        id="call-1",
        type="function",
        function=Function(name="web_search", arguments='{"query":"pet supplies"}'),
    )
    adapter = _client(_completion(content=None, tool_calls=[tool_call]))
    response = await adapter.generate(_request(tools=True))
    assert response.tool_calls[0].name == "web_search"
    assert response.tool_calls[0].arguments.query == "pet supplies"


async def test_invalid_tool_call_arguments_are_typed() -> None:
    tool_call = ChatCompletionMessageFunctionToolCall(
        id="call-1",
        type="function",
        function=Function(name="web_search", arguments="{bad json"),
    )
    adapter = _client(_completion(content=None, tool_calls=[tool_call]))
    with pytest.raises(LLMInvalidRequestError):
        await adapter.generate(_request(tools=True))


async def test_request_conversion_includes_tools_and_response_format() -> None:
    adapter = _client(_completion(content="ok"))
    await adapter.generate(_request(tools=True, structured=True))
    captured = adapter._captured  # type: ignore[attr-defined]
    assert captured["model"] == "gpt-4o-mini"
    assert captured["tools"]
    assert "response_format" not in captured


async def test_request_conversion_includes_response_format_without_tools() -> None:
    adapter = _client(_completion(content="ok"))
    await adapter.generate(_request(tools=False, structured=True))
    captured = adapter._captured  # type: ignore[attr-defined]
    assert captured["response_format"]["type"] == "json_schema"


async def test_provider_error_is_sanitized() -> None:
    config = LLMModelConfig(
        provider="openai",
        model="gpt-4o-mini",
        api_key="super-secret-test-key",  # type: ignore[arg-type]
    )
    adapter = OpenAIChatClient(config)
    response = httpx.Response(
        400,
        request=httpx.Request("POST", "https://api.openai.com"),
    )
    error = BadRequestError("bad request super-secret-test-key", response=response, body=None)

    async def create(**kwargs: object) -> ChatCompletion:
        raise error

    adapter._client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    with pytest.raises(LLMInvalidRequestError) as excinfo:
        await adapter.generate(_request())
    assert "super-secret-test-key" not in str(excinfo.value)
