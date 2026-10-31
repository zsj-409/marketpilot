"""Milestone B, Task B4.1: real-LLM vs deterministic strategy comparison.

Design:
- ~24 representative Generation-DEV worlds (not used in the independent
  final statistics) covering: simple research, hidden risk, evidence
  conflict, stale data, multi-candidate tradeoff, scarce budget, source
  anomaly, tool failure.
- A real LLM (when an API key exists) decides research actions and final
  recommendation; tool responses come from the FROZEN synthetic world.
- When no API key is configured this script runs the same harness with
  the deterministic MockLLMClient and marks results REAL_LLM_NOT_RUN —
  it never fabricates real-LLM numbers.
- Real-LLM call costs are accounted separately from synthetic tool costs.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from marketpilot.config import MarketPilotSettings
from marketpilot.llm.models import LLMMessage, LLMMessageRole, LLMRequest
from marketpilot.llm.providers.mock import MockLLMClient
from marketpilot.llm.providers.openai import OpenAIChatClient
from marketpilot.llm.retry import RetryableLLMClient
from marketpilot.optimization.dream_rsi import ParameterizedPolicy
from marketpilot.world.core import AgentWorldView, WorldOracle, build_diagnostic_world

OUT = Path("artifacts/milestone_b")
KINDS = ["W0", "W1", "W2", "W3", "W4", "W5"]
SEEDS = [7, 8, 9, 10]
STATIC_STRATEGIES = ["fixed", "missing-evidence", "uncertainty",
                     "adaptive-voi", "contextual-hybrid"]


@dataclass
class LLMAgentResult:
    world_id: str
    n_calls: int = 0
    n_tool_calls: int = 0
    decision: str = ""
    selected_id: str | None = None
    total_tokens: int = 0
    estimated_cost: float = 0.0
    final_message: str = ""


@dataclass
class WorldRun:
    world_id: str
    kind: str
    strategy_results: dict[str, dict] = field(default_factory=dict)
    llm_result: LLMAgentResult | None = None
    oracle_best: str | None = None


class SyntheticToolEnvironment:
    """Expose the frozen synthetic world as a tool response source.

    The LLM requests research actions; responses come from the world's
    deterministic evidence, NOT from the model's imagination.
    """

    _FACET_TO_ACTION: ClassVar[dict[str, str]] = {
        "margin": "SEARCH_MARGIN",
        "demand": "SEARCH_DEMAND",
        "risk": "SEARCH_RISK",
        "competition": "SEARCH_COMPETITION",
        "reliability": "SEARCH_RELIABILITY",
        "market": "SEARCH_MARKET",
    }

    def __init__(self, world) -> None:
        self.world = world
        self.view = AgentWorldView(world)
        self.actions: list[dict] = []

    def tool_schema(self) -> list[dict]:
        return [
            {
                "name": "research_facet",
                "description": "Research a facet for a candidate product.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string"},
                        "facet": {"type": "string",
                                  "enum": ["margin", "demand", "risk",
                                           "competition", "reliability"]},
                    },
                    "required": ["product_id", "facet"],
                },
            },
            {
                "name": "final_recommendation",
                "description": "Output the final recommendation.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string"},
                        "reasoning": {"type": "string"},
                        "confidence": {"type": "string",
                                       "enum": ["high", "medium", "low"]},
                    },
                    "required": ["product_id", "reasoning", "confidence"],
                },
            },
        ]

    def execute_tool(self, name: str, args: dict) -> str:
        self.actions.append({"name": name, "args": args})
        if name == "research_facet":
            pid = args["product_id"]
            facet = args.get("facet") or args.get("query") or "margin"
            from marketpilot.world.core import ResearchAction

            action = ResearchAction[self._FACET_TO_ACTION.get(facet, "SEARCH_MARKET")]
            self.view.take_action(action, pid)
            # Return the observed evidence for that facet.
            values = self.view.revealed_facets(pid)
            return json.dumps({"product_id": pid, "facet": facet,
                               "evidence": list(values)})
        if name == "final_recommendation":
            return json.dumps({"accepted": True})
        return json.dumps({"error": "unknown tool"})


async def run_llm_agent(
    env: SyntheticToolEnvironment,
    client,
    task_prompt: str,
    max_turns: int = 4,
) -> LLMAgentResult:
    """Run a tool-calling loop with the LLM client."""
    result = LLMAgentResult(world_id=env.world.world_id)
    messages: list[LLMMessage] = [
        LLMMessage(role=LLMMessageRole.SYSTEM,
                   content="You are a product research agent. Use the tools to "
                           "research evidence; call final_recommendation when "
                           "you have enough evidence."),
        LLMMessage(role=LLMMessageRole.USER, content=task_prompt),
    ]
    tools = env.tool_schema()
    from marketpilot.llm.models import LLMToolDefinition

    tool_defs = [LLMToolDefinition(name=t["name"], description=t["description"],
                                   input_schema=t["input_schema"]) for t in tools]
    # Deterministic offline fixture: the mock "LLM" researches the three
    # required facets for the first candidate then recommends it. This is
    # the REAL_LLM_NOT_RUN fallback — no fabricated real-model numbers.
    if isinstance(client, MockLLMClient):
        cid = env.world.products[0].product_id
        for facet in ("margin", "demand", "risk"):
            from marketpilot.llm.models import LLMToolCall
            from marketpilot.tools.base import ToolArguments

            call = LLMToolCall(
                call_id=f"mock-{facet}", name="research_facet",
                arguments=ToolArguments(product_id=cid, query=facet),
            )
            result.n_calls += 1
            result.n_tool_calls += 1
            tool_result = env.execute_tool(
                call.name, call.arguments.model_dump()
            )
            messages.append(LLMMessage(role=LLMMessageRole.ASSISTANT,
                                       tool_calls=[call], content=None))
            messages.append(LLMMessage(role=LLMMessageRole.TOOL,
                                       tool_call_id=call.call_id,
                                       content=tool_result))
        from marketpilot.llm.models import LLMToolCall
        from marketpilot.tools.base import ToolArguments

        final_call = LLMToolCall(
            call_id="mock-final", name="final_recommendation",
            arguments=ToolArguments(product_id=cid, query="fixture"),
        )
        result.n_calls += 1
        result.n_tool_calls += 1
        env.execute_tool(final_call.name, final_call.arguments.model_dump())
        result.decision = "GO"
        result.selected_id = cid
        result.final_message = f"final_recommendation product_id={cid}"
        result.total_tokens = 60
        result.estimated_cost = 0.0
        return result

    for _ in range(max_turns):
        request = LLMRequest(
            provider="mock" if isinstance(client, MockLLMClient) else "openai",
            model="mock-research-model" if isinstance(client, MockLLMClient)
            else "gpt-4o-mini",
            messages=messages,
            tools=tool_defs,
            temperature=0.0,
        )
        response = await client.generate(request)
        result.n_calls += 1
        result.total_tokens += response.usage.total_tokens
        result.estimated_cost += response.usage.estimated_cost or 0.0
        if response.finish_reason.value == "tool_calls":
            for call in response.tool_calls:
                result.n_tool_calls += 1
                tool_result = env.execute_tool(call.name, call.arguments)
                messages.append(LLMMessage(
                    role=LLMMessageRole.ASSISTANT,
                    tool_calls=[call],
                    content=None,
                ))
                messages.append(LLMMessage(
                    role=LLMMessageRole.TOOL,
                    tool_call_id=call.call_id,
                    content=tool_result,
                ))
            continue
        result.final_message = response.content or ""
        result.decision = "GO" if "final_recommendation" in result.final_message or \
            result.final_message else "REFUSED"
        # Parse the final recommendation product id if present.
        import re

        m = re.search(r"product_id.?[:=]?[\"']?([A-Za-z0-9_-]+)", result.final_message)
        if m:
            result.selected_id = m.group(1)
        break
    return result


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    settings = MarketPilotSettings()
    key = settings.llm_api_key.get_secret_value() if settings.llm_api_key else None
    real_llm = key is not None
    if real_llm:
        from marketpilot.llm.models import LLMModelConfig

        client = RetryableLLMClient(OpenAIChatClient(LLMModelConfig(
            provider="openai", model=settings.llm_model,
            api_key=settings.llm_api_key,
            timeout_seconds=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )))
        print("REAL_LLM_RUN: using", settings.llm_model)
    else:
        client = MockLLMClient(responses_by_prompt={})  # offline fallback
        print("REAL_LLM_NOT_RUN: no API key — using deterministic MockLLMClient "
              "(results are offline fixtures only)")

    runs: list[WorldRun] = []
    for kind in KINDS:
        for seed in SEEDS:
            world = build_diagnostic_world(kind=kind, seed=seed, world_id=f"{kind}-{seed}")
            oracle = WorldOracle(world)
            wr = WorldRun(world_id=f"{kind}-{seed}", kind=kind,
                          oracle_best=oracle.best_product_id())
            # Deterministic strategies.
            for strategy in STATIC_STRATEGIES:
                pol = ParameterizedPolicy(strategy=strategy, name=strategy)
                r = pol.execute(AgentWorldView(world))
                wr.strategy_results[strategy] = {
                    "decision": r.decision,
                    "selected_id": r.selected_id,
                    "cost": round(r.total_cost, 2),
                    "steps": len(r.steps),
                }
            # LLM agent (real or mock).
            env = SyntheticToolEnvironment(world)
            prompt = (
                f"Research products to find a safe recommendation. "
                f"Available products: {[p.product_id for p in world.products]}. "
                f"Required facets: margin, demand, risk. "
                f"Max price 100, no battery. "
                f"Call final_recommendation only with sufficient evidence."
            )
            llm_result = await run_llm_agent(env, client, prompt)
            wr.llm_result = llm_result
            runs.append(wr)

    # Save.
    summary = {
        "real_llm": real_llm,
        "n_worlds": len(runs),
        "n_calls": sum(r.llm_result.n_calls for r in runs),
        "n_tool_calls": sum(r.llm_result.n_tool_calls for r in runs),
        "total_tokens": sum(r.llm_result.total_tokens for r in runs),
        "estimated_cost": round(sum(r.llm_result.estimated_cost for r in runs), 4),
        "per_world": [
            {
                "world_id": r.world_id,
                "kind": r.kind,
                "oracle_best": r.oracle_best,
                "strategies": r.strategy_results,
                "llm": {
                    "decision": r.llm_result.decision,
                    "selected_id": r.llm_result.selected_id,
                    "n_calls": r.llm_result.n_calls,
                    "n_tool_calls": r.llm_result.n_tool_calls,
                    "tokens": r.llm_result.total_tokens,
                    "cost": r.llm_result.estimated_cost,
                },
            }
            for r in runs
        ],
        "status": "REAL_LLM_RUN" if real_llm else "REAL_LLM_NOT_RUN",
    }
    (OUT / "b41_llm_vs_strategies.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"wrote b41_llm_vs_strategies.json "
          f"({len(runs)} worlds, calls={summary['n_calls']}, "
          f"tokens={summary['total_tokens']}, cost=${summary['estimated_cost']})")


if __name__ == "__main__":
    asyncio.run(main())
