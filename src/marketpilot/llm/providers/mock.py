"""Deterministic scripted LLM provider."""

from collections.abc import Mapping, Sequence

from marketpilot.llm.base import LLMClient
from marketpilot.llm.errors import LLMError, LLMPermanentProviderError
from marketpilot.llm.models import (
    LLMFinishReason,
    LLMRequest,
    LLMResponse,
    LLMToolCall,
    LLMUsage,
)
from marketpilot.tools.base import ToolArguments


def _usage(input_tokens: int = 10, output_tokens: int = 20) -> LLMUsage:
    return LLMUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        latency_ms=0,
        estimated_cost=0.0,
    )


def _tool_response(prompt_name: str, index: int, calls: list[LLMToolCall]) -> LLMResponse:
    return LLMResponse(
        response_id=f"mock-{prompt_name}-{index}",
        provider="mock",
        model="mock-research-model",
        finish_reason=LLMFinishReason.TOOL_CALLS,
        content=None,
        tool_calls=calls,
        usage=_usage(input_tokens=10, output_tokens=0),
    )


def _final_response(prompt_name: str, index: int, content: str) -> LLMResponse:
    return LLMResponse(
        response_id=f"mock-{prompt_name}-{index}",
        provider="mock",
        model="mock-research-model",
        finish_reason=LLMFinishReason.STOP,
        content=content,
        tool_calls=[],
        usage=_usage(input_tokens=20, output_tokens=40),
    )


class MockLLMClient(LLMClient):
    """A deterministic, offline LLM client.

    Responses can be scripted by prompt name or as a global sequence. The
    prompt-specific mode is useful for multi-turn tool loops because each prompt
    maintains its own cursor.
    """

    def __init__(
        self,
        responses: Sequence[LLMResponse | LLMError] | None = None,
        responses_by_prompt: Mapping[str, Sequence[LLMResponse | LLMError]] | None = None,
    ) -> None:
        self._responses = list(responses or [])
        self._responses_by_prompt = {
            name: list(sequence) for name, sequence in (responses_by_prompt or {}).items()
        }
        self._indices: dict[str, int] = {}

    async def generate(self, request: LLMRequest) -> LLMResponse:
        prompt_name = self._prompt_name(request)
        if prompt_name in self._responses_by_prompt:
            sequence = self._responses_by_prompt[prompt_name]
            index = self._indices.get(prompt_name, 0)
            if index >= len(sequence):
                raise LLMPermanentProviderError(
                    f"mock LLM script exhausted for prompt: {prompt_name}"
                )
            item = sequence[index]
            self._indices[prompt_name] = index + 1
        elif self._responses:
            item = self._responses.pop(0)
        else:
            raise LLMPermanentProviderError("mock LLM has no scripted response")

        if isinstance(item, LLMError):
            raise item
        content = item.content
        if content is not None:
            for key, value in request.metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    content = content.replace(f"__{key.upper()}__", str(value))
        return item.model_copy(update={"attempts": 1, "content": content})

    def _prompt_name(self, request: LLMRequest) -> str:
        value = request.metadata.get("prompt_name")
        if isinstance(value, str):
            return value
        return "default"


def build_demo_llm_responses() -> dict[str, list[LLMResponse | LLMError]]:
    """Build a deterministic script for the offline LLM demo."""

    market_tool = _tool_response(
        "market_research",
        1,
        [
            LLMToolCall(
                call_id="mock-market-tool-1",
                name="get_market_signal",
                arguments=ToolArguments(category="pet supplies", market="US"),
            )
        ],
    )
    market_final = _final_response(
        "market_research",
        2,
        '{"claim":"US demand for pet supplies is moderately rising.","confidence":0.82}',
    )

    product_discovery_tool = _tool_response(
        "product_research",
        1,
        [
            LLMToolCall(
                call_id="mock-product-tool-1",
                name="search_products",
                arguments=ToolArguments(category="pet supplies", market="US"),
            ),
            LLMToolCall(
                call_id="mock-product-tool-2",
                name="get_product_details",
                arguments=ToolArguments(product_id="mock-automatic-pet-feeder"),
            ),
        ],
    )
    product_discovery_final = _final_response(
        "product_research",
        2,
        (
            '{"candidate_name":"Automatic pet feeder",'
            '"provider_product_id":"mock-automatic-pet-feeder",'
            '"claim":"Automatic pet feeder is a viable provider-neutral candidate.",'
            '"confidence":0.78}'
        ),
    )
    product_aggregation_tool = _tool_response(
        "product_research",
        3,
        [
            LLMToolCall(
                call_id="mock-product-tool-3",
                name="estimate_cost",
                arguments=ToolArguments(product_name="automatic pet feeder"),
            ),
            LLMToolCall(
                call_id="mock-product-tool-4",
                name="estimate_margin",
                arguments=ToolArguments(product_name="automatic pet feeder"),
            ),
        ],
    )
    product_aggregation_final = _final_response(
        "product_research",
        4,
        (
            '{"candidate_name":"Automatic pet feeder",'
            '"provider_product_id":"mock-automatic-pet-feeder",'
            '"claim":"Estimated gross margin is above the minimum threshold.",'
            '"confidence":0.74}'
        ),
    )

    review_tool = _tool_response(
        "review_research",
        1,
        [
            LLMToolCall(
                call_id="mock-review-tool-1",
                name="search_reviews",
                arguments=ToolArguments(product_name="automatic pet feeder"),
            )
        ],
    )
    review_final = _final_response(
        "review_research",
        2,
        ('{"claim":"Battery reliability is a recurring customer complaint.","confidence":0.80}'),
    )

    competitor_tool = _tool_response(
        "competitor_research",
        1,
        [
            LLMToolCall(
                call_id="mock-competitor-tool-1",
                name="web_search",
                arguments=ToolArguments(query="pet supplies competitors US"),
            )
        ],
    )
    competitor_final = _final_response(
        "competitor_research",
        2,
        ('{"claim":"Competition for automatic pet feeders is medium-high.","confidence":0.71}'),
    )

    risk_tool = _tool_response(
        "risk_analysis",
        1,
        [
            LLMToolCall(
                call_id="mock-risk-tool-1",
                name="estimate_margin",
                arguments=ToolArguments(product_name="automatic pet feeder"),
            )
        ],
    )
    risk_final = _final_response(
        "risk_analysis",
        2,
        (
            '{"label":"Medium-high competition",'
            '"severity":0.62,'
            '"rationale":"Multiple established sellers and recurring price competition.",'
            '"claim":"Competition creates moderate execution risk.",'
            '"confidence":0.69}'
        ),
    )

    decision_final = _final_response(
        "decision",
        1,
        (
            '{"candidate_id":"__CANDIDATE_ID__",'
            '"decision":"WATCH",'
            '"confidence":0.73,'
            '"rationale":"Demand and margin are acceptable, but competition and '
            'reliability complaints warrant monitoring.",'
            '"scores":{"demand":0.78,"trend":0.72,"estimated_margin":0.68,"competition":0.62,'
            '"customer_pain_opportunity":0.74,"operational_complexity":0.55,'
            '"regulatory_risk":0.22,"overall_score":0.68}}'
        ),
    )

    return {
        "market_research": [market_tool, market_final],
        "product_research": [
            product_discovery_tool,
            product_discovery_final,
            product_aggregation_tool,
            product_aggregation_final,
        ],
        "review_research": [review_tool, review_final],
        "competitor_research": [competitor_tool, competitor_final],
        "risk_analysis": [risk_tool, risk_final],
        "decision": [decision_final],
    }


def build_research_demo_llm_responses() -> dict[str, list[LLMResponse]]:
    """Build a deterministic script for the offline research-tool LLM demo."""

    def search_tool(prompt: str, index: int, query: str) -> LLMResponse:
        return _tool_response(
            prompt,
            index,
            [
                LLMToolCall(
                    call_id=f"mock-search-{prompt}-{index}",
                    name="web_search",
                    arguments=ToolArguments(query=query),
                )
            ],
        )

    def fetch_tool(prompt: str, index: int, url: str) -> LLMResponse:
        return _tool_response(
            prompt,
            index,
            [
                LLMToolCall(
                    call_id=f"mock-fetch-{prompt}-{index}",
                    name="fetch_page",
                    arguments=ToolArguments(url=url),
                )
            ],
        )

    market = [
        search_tool("market_research", 1, "pet supplies market demand US"),
        fetch_tool("market_research", 2, "https://example.com/pet-feeders"),
        _final_response(
            "market_research",
            3,
            '{"claim":"US demand for automatic pet feeders is moderately rising.",'
            '"confidence":0.82}',
        ),
    ]
    product = [
        search_tool("product_research", 1, "automatic pet feeder products"),
        fetch_tool("product_research", 2, "https://example.com/pet-feeders"),
        _final_response(
            "product_research",
            3,
            '{"candidate_name":"Automatic pet feeder",'
            '"provider_product_id":"mock-automatic-pet-feeder",'
            '"claim":"Automatic pet feeder is a viable candidate.","confidence":0.78}',
        ),
        search_tool("product_research", 4, "automatic pet feeder cost margin"),
        fetch_tool("product_research", 5, "https://example.com/pet-feeders"),
        _final_response(
            "product_research",
            6,
            '{"candidate_name":"Automatic pet feeder",'
            '"provider_product_id":"mock-automatic-pet-feeder",'
            '"claim":"Estimated margin is acceptable.","confidence":0.74}',
        ),
    ]
    review = [
        search_tool("review_research", 1, "automatic pet feeder battery complaints"),
        fetch_tool("review_research", 2, "https://example.com/reviews/pet-feeders"),
        _final_response(
            "review_research",
            3,
            '{"claim":"Battery reliability is a recurring customer complaint.","confidence":0.80}',
        ),
    ]
    competitor = [
        search_tool("competitor_research", 1, "pet feeder competitors US"),
        fetch_tool("competitor_research", 2, "https://example.com/pet-feeders"),
        _final_response(
            "competitor_research",
            3,
            '{"claim":"Competition is medium-high.","confidence":0.71}',
        ),
    ]
    risk = [
        search_tool("risk_analysis", 1, "pet feeder margin risk"),
        fetch_tool("risk_analysis", 2, "https://example.com/pet-feeders"),
        _final_response(
            "risk_analysis",
            3,
            '{"label":"Medium-high competition","severity":0.62,'
            '"rationale":"Multiple sellers and price competition.",'
            '"claim":"Competition creates moderate execution risk.","confidence":0.69}',
        ),
    ]
    decision = [
        _final_response(
            "decision",
            1,
            '{"candidate_id":"__CANDIDATE_ID__","decision":"WATCH","confidence":0.73,'
            '"rationale":"Demand is acceptable but competition is medium-high.",'
            '"scores":{"demand":0.78,"trend":0.72,"estimated_margin":0.68,'
            '"competition":0.62,"customer_pain_opportunity":0.74,'
            '"operational_complexity":0.55,"regulatory_risk":0.22,"overall_score":0.68}}',
        )
    ]
    return {
        "market_research": market,
        "product_research": product,
        "review_research": review,
        "competitor_research": competitor,
        "risk_analysis": risk,
        "decision": decision,
    }
