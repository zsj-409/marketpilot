"""LLM candidate ranking over a frozen synthetic environment."""

import json
import time
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from marketpilot.config import MarketPilotSettings
from marketpilot.llm.models import (
    LLMMessage,
    LLMMessageRole,
    LLMModelConfig,
    LLMRequest,
    LLMStructuredOutputSpec,
)
from marketpilot.llm.providers.openai import OpenAIChatClient
from marketpilot.llm.structured import parse_structured_output
from marketpilot.research.providers.search import SearchProvider


class CandidateRankingOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    candidate_ids: list[UUID] = Field(min_length=1)
    reasoning: str = Field(min_length=1, max_length=2000)


class LLMCandidateRanker:
    """Ask a real LLM to rank observable candidates without hidden truth."""

    def __init__(
        self,
        settings: MarketPilotSettings,
        *,
        temperature: float,
    ) -> None:
        config = LLMModelConfig(
            provider="openai",
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            timeout_seconds=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
            temperature=temperature,
            max_output_tokens=settings.llm_max_output_tokens,
        )
        self._client = OpenAIChatClient(config)
        self._temperature = temperature
        self._model = settings.llm_model

    async def rank(
        self,
        category: str,
        products: list[dict[str, Any]],
    ) -> tuple[list[UUID], dict[str, Any]]:
        visible = [
            {
                "candidate_id": str(item["product_id"]),
                "title": item["title"],
                "features": {
                    key: item.get(key)
                    for key in (
                        "selling_price",
                        "gross_margin",
                        "monthly_search_volume",
                        "search_growth_3m",
                        "seller_count",
                        "median_competitor_reviews",
                        "rating",
                        "review_count",
                        "return_rate",
                        "complaint_rate",
                        "fragile",
                        "battery",
                        "liquid",
                        "regulatory_risk",
                        "ad_cpc_proxy",
                        "differentiation_score",
                        "demand_score",
                        "competition_score",
                        "risk_score",
                    )
                    if key in item
                },
            }
            for item in products
        ]
        request = LLMRequest(
            provider="openai",
            model=self._model,
            messages=[
                LLMMessage(
                    role=LLMMessageRole.SYSTEM,
                    content=(
                        "Rank product candidates by expected opportunity. "
                        "Prefer higher demand, higher margin, higher differentiation, "
                        "lower competition, and lower risk. Return JSON only."
                    ),
                ),
                LLMMessage(
                    role=LLMMessageRole.USER,
                    content=json.dumps(
                        {"category": category, "candidates": visible}, ensure_ascii=False
                    ),
                ),
            ],
            temperature=self._temperature,
            max_output_tokens=2048,
            structured_output=LLMStructuredOutputSpec(
                name="CandidateRankingOutput",
                json_schema=CandidateRankingOutput.model_json_schema(),
            ),
        )
        started = time.perf_counter()
        response = await self._client.generate(request)
        client_wall_latency_ms = round((time.perf_counter() - started) * 1000, 2)
        output = parse_structured_output(response.content, CandidateRankingOutput)
        metrics = {
            "response_id": response.response_id,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "provider_latency_ms": response.usage.latency_ms,
            "client_wall_latency_ms": client_wall_latency_ms,
            "estimated_cost": response.usage.estimated_cost,
        }
        return output.candidate_ids, metrics

    async def rank_research(
        self,
        category: str,
        products: list[dict[str, Any]],
        policy: str,
        sources: list[dict[str, Any]],
        search_provider: SearchProvider | None = None,
    ) -> tuple[list[UUID], dict[str, Any], str]:
        from marketpilot.synthetic.providers import SyntheticSearchProvider

        query = _policy_query(policy, category)
        provider = search_provider or SyntheticSearchProvider(sources)
        search_results = await provider.search(query, 3)
        evidence = "\n".join(item.snippet for item in search_results)
        objectives = {
            "static-ranking": "general opportunity",
            "constraint-first": "hard constraints and feasibility",
            "evidence-gap-first": "decision-critical evidence gaps",
            "risk-first": "downside risk and failure modes",
        }
        request = LLMRequest(
            provider="openai",
            model=self._model,
            messages=[
                LLMMessage(
                    role=LLMMessageRole.SYSTEM,
                    content="Rank product candidates by expected opportunity. Return JSON only.",
                ),
                LLMMessage(
                    role=LLMMessageRole.USER,
                    content=(
                        "Research objective: "
                        + objectives.get(policy, "general opportunity")
                        + ".\nEvidence:\n"
                        + evidence
                        + "\n"
                        + json.dumps(
                            {"category": category, "candidates": _visible_candidates(products)},
                            ensure_ascii=False,
                        )
                    ),
                ),
            ],
            temperature=self._temperature,
            max_output_tokens=2048,
            structured_output=LLMStructuredOutputSpec(
                name="CandidateRankingOutput",
                json_schema=CandidateRankingOutput.model_json_schema(),
            ),
        )
        started = time.perf_counter()
        response = await self._client.generate(request)
        client_wall_latency_ms = round((time.perf_counter() - started) * 1000, 2)
        output = parse_structured_output(response.content, CandidateRankingOutput)
        metrics = {
            "response_id": response.response_id,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "provider_latency_ms": response.usage.latency_ms,
            "client_wall_latency_ms": client_wall_latency_ms,
            "search_results": len(search_results),
            "query": query,
        }
        return output.candidate_ids, metrics, evidence


def _visible_candidates(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "candidate_id": str(item["product_id"]),
            "title": item["title"],
            "features": {
                key: item.get(key)
                for key in (
                    "selling_price",
                    "gross_margin",
                    "monthly_search_volume",
                    "search_growth_3m",
                    "seller_count",
                    "median_competitor_reviews",
                    "rating",
                    "review_count",
                    "return_rate",
                    "complaint_rate",
                    "fragile",
                    "battery",
                    "liquid",
                    "regulatory_risk",
                    "ad_cpc_proxy",
                    "differentiation_score",
                    "demand_score",
                    "competition_score",
                    "risk_score",
                )
                if key in item
            },
        }
        for item in products
    ]


def _policy_query(policy: str, category: str) -> str:
    if policy == "constraint-first":
        return f"margin risk constraints {category}"
    if policy == "evidence-gap-first":
        return f"review depth return rate evidence {category}"
    if policy == "risk-first":
        return f"downside risk complaints {category}"
    return f"best opportunity {category}"
