"""OpenAI chat-completions adapter."""

from typing import Any, cast

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    RateLimitError,
)
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionMessageParam,
    ChatCompletionToolParam,
)
from openai.types.chat.completion_create_params import ResponseFormat

from marketpilot.llm.base import LLMClient
from marketpilot.llm.errors import (
    LLMAuthenticationError,
    LLMInvalidRequestError,
    LLMPermanentProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMTransientProviderError,
    sanitize_message,
)
from marketpilot.llm.models import (
    LLMFinishReason,
    LLMMessage,
    LLMMessageRole,
    LLMModelConfig,
    LLMRequest,
    LLMResponse,
    LLMToolCall,
    LLMToolDefinition,
    LLMUsage,
)
from marketpilot.llm.pricing import PricingCalculator
from marketpilot.tools.base import ToolArguments


class OpenAIChatClient(LLMClient):
    """Adapter that translates MarketPilot requests to OpenAI chat completions."""

    def __init__(
        self,
        config: LLMModelConfig,
        pricing: PricingCalculator | None = None,
    ) -> None:
        if config.provider != "openai":
            raise ValueError("OpenAIChatClient requires provider='openai'")
        api_key = config.api_key.get_secret_value() if config.api_key else None
        if api_key is None:
            raise LLMAuthenticationError("OpenAI API key is not configured")
        self._config = config
        self._pricing = pricing
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=config.base_url,
            timeout=config.timeout_seconds,
            max_retries=0,
        )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        messages = self._convert_messages(request.messages)
        tools = self._convert_tools(request.tools)
        response_format = self._convert_structured_output(request)
        secrets = [self._config.api_key.get_secret_value() if self._config.api_key else ""]

        try:
            create_kwargs: dict[str, object] = {
                "model": request.model,
                "messages": messages,
                "tools": tools,
                "temperature": request.temperature,
                "max_tokens": request.max_output_tokens,
            }
            if tools:
                create_kwargs["tool_choice"] = "auto"
            if response_format is not None and not tools:
                create_kwargs["response_format"] = response_format
            completion = await self._client.chat.completions.create(
                **cast("Any", create_kwargs),
            )
        except AuthenticationError as exc:
            raise LLMAuthenticationError(sanitize_message(str(exc), secrets)) from exc
        except RateLimitError as exc:
            raise LLMRateLimitError(sanitize_message(str(exc), secrets)) from exc
        except APITimeoutError as exc:
            raise LLMTimeoutError(sanitize_message(str(exc), secrets)) from exc
        except APIConnectionError as exc:
            raise LLMTransientProviderError(sanitize_message(str(exc), secrets)) from exc
        except BadRequestError as exc:
            raise LLMInvalidRequestError(sanitize_message(str(exc), secrets)) from exc
        except InternalServerError as exc:
            raise LLMTransientProviderError(sanitize_message(str(exc), secrets)) from exc
        except APIStatusError as exc:
            raise LLMPermanentProviderError(sanitize_message(str(exc), secrets)) from exc
        except Exception as exc:
            raise LLMPermanentProviderError(sanitize_message(str(exc), secrets)) from exc

        return self._convert_response(completion, request)

    def _convert_messages(
        self,
        messages: list[LLMMessage],
    ) -> list[ChatCompletionMessageParam]:
        converted: list[ChatCompletionMessageParam] = []
        for message in messages:
            if message.role is LLMMessageRole.SYSTEM:
                converted.append(
                    cast(
                        "ChatCompletionMessageParam",
                        {"role": "system", "content": message.content or ""},
                    )
                )
            elif message.role is LLMMessageRole.USER:
                converted.append(
                    cast(
                        "ChatCompletionMessageParam",
                        {"role": "user", "content": message.content or ""},
                    )
                )
            elif message.role is LLMMessageRole.ASSISTANT:
                converted.append(
                    cast(
                        "ChatCompletionMessageParam",
                        {
                            "role": "assistant",
                            "content": message.content,
                            "tool_calls": [
                                {
                                    "id": call.call_id,
                                    "type": "function",
                                    "function": {
                                        "name": call.name,
                                        "arguments": call.arguments.model_dump_json(
                                            exclude_none=True
                                        ),
                                    },
                                }
                                for call in message.tool_calls
                            ],
                        },
                    )
                )
            else:
                converted.append(
                    cast(
                        "ChatCompletionMessageParam",
                        {
                            "role": "tool",
                            "tool_call_id": message.tool_call_id or "",
                            "content": message.content or "",
                        },
                    )
                )
        return converted

    def _convert_tools(
        self,
        tools: list[LLMToolDefinition],
    ) -> list[ChatCompletionToolParam]:
        if not tools:
            return []
        return [
            cast(
                "ChatCompletionToolParam",
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.input_schema,
                    },
                },
            )
            for tool in tools
        ]

    def _convert_structured_output(
        self,
        request: LLMRequest,
    ) -> ResponseFormat | None:
        if request.structured_output is None:
            return None
        return cast(
            "ResponseFormat",
            {
                "type": "json_schema",
                "json_schema": {
                    "name": request.structured_output.name,
                    "schema": request.structured_output.json_schema,
                    "strict": True,
                },
            },
        )

    def _convert_response(
        self,
        completion: ChatCompletion,
        request: LLMRequest,
    ) -> LLMResponse:
        if not completion.choices:
            raise LLMPermanentProviderError("OpenAI returned an empty response")
        choice = completion.choices[0]
        message = choice.message
        tool_calls: list[LLMToolCall] = []
        for call in message.tool_calls or []:
            if call.type != "function" or call.function is None:
                continue
            try:
                arguments = ToolArguments.model_validate_json(call.function.arguments)
            except Exception as exc:
                raise LLMInvalidRequestError(
                    f"invalid OpenAI tool-call arguments for {call.function.name}"
                ) from exc
            tool_calls.append(
                LLMToolCall(
                    call_id=call.id,
                    name=call.function.name,
                    arguments=arguments,
                )
            )

        usage = completion.usage
        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0
        total_tokens = usage.total_tokens if usage else input_tokens + output_tokens
        normalized_usage = LLMUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cached_tokens=None,
            latency_ms=0,
            estimated_cost=None,
        )
        if self._pricing is not None:
            normalized_usage = normalized_usage.model_copy(
                update={"estimated_cost": self._pricing.estimate(request.model, normalized_usage)}
            )

        return LLMResponse(
            response_id=completion.id,
            provider="openai",
            model=completion.model,
            finish_reason=self._finish_reason(choice.finish_reason),
            content=message.content,
            tool_calls=tool_calls,
            usage=normalized_usage,
        )

    def _finish_reason(self, reason: str | None) -> LLMFinishReason:
        if reason == "stop":
            return LLMFinishReason.STOP
        if reason == "tool_calls":
            return LLMFinishReason.TOOL_CALLS
        if reason == "length":
            return LLMFinishReason.LENGTH
        if reason == "content_filter":
            return LLMFinishReason.CONTENT_FILTER
        return LLMFinishReason.UNKNOWN
