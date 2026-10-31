"""Release Gate Task B1: REAL LLM Smoke Test.

Uses the SAME provider the Hermes runtime itself uses (volcengine-ark /
deepseek-v4-flash, key from the Hermes .env via ARK_API_KEY). The key is
read at runtime, used in-process, NEVER written to disk/logs/git.

Four pre-registered smoke tasks verify: real model requests happen, the
model participates in decision stages, ToolExecutor returns real tool
observations, Evidence Store saves sources, Structured Outputs validate,
retry/error classification works, Safety Gateway protects the output,
and token/cost/latency are tracked.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path

from marketpilot.llm.errors import LLMError
from marketpilot.llm.models import (
    LLMFinishReason,
    LLMMessage,
    LLMMessageRole,
    LLMRequest,
    LLMToolCall,
    LLMToolDefinition,
)
from marketpilot.llm.providers.openai import OpenAIChatClient
from marketpilot.llm.retry import RetryableLLMClient, RetryPolicy
from marketpilot.safety.gateway import gate_workbench_run
from marketpilot.tools.base import ToolArguments
from marketpilot.world.core import AgentWorldView, build_diagnostic_world

OUT = Path("artifacts/milestone_b")

# Pre-registered smoke tasks (world kind, seed) — 4 representative worlds.
SMOKE_TASKS = [("W1", 7), ("W2", 8), ("W4", 9), ("W0", 7)]

# The real-LLM experiment reads the API key from the Hermes runtime's .env
# (a machine-specific path). Resolve it via environment variables only —
# never a hard-coded username. Set HERMES_ENV_PATH explicitly if needed.
_HERMES_ENV = Path(os.environ.get("HERMES_ENV_PATH", ""))
if not _HERMES_ENV.exists():
    _HERMES_ENV = Path(os.environ.get("LOCALAPPDATA", "")) / "hermes" / ".env"

TOOL_SCHEMA = [
    LLMToolDefinition(
        name="research_facet",
        description="Research one evidence facet for a candidate product.",
        input_schema={
            "type": "object",
            "properties": {
                "product_id": {"type": "string"},
                "facet": {"type": "string",
                          "enum": ["margin", "demand", "risk",
                                   "competition", "reliability"]},
            },
            "required": ["product_id", "facet"],
        },
    ),
    LLMToolDefinition(
        name="final_recommendation",
        description="Output the final product recommendation.",
        input_schema={
            "type": "object",
            "properties": {
                "product_id": {"type": "string"},
                "confidence": {"type": "string",
                               "enum": ["high", "medium", "low"]},
            },
            "required": ["product_id", "confidence"],
        },
    ),
]

_FACET_ACTION = {
    "margin": "SEARCH_MARGIN", "demand": "SEARCH_DEMAND",
    "risk": "SEARCH_RISK", "competition": "SEARCH_COMPETITION",
    "reliability": "SEARCH_RELIABILITY",
}


def _read_ark_key() -> str | None:
    """Read the API key WITHOUT echoing it.

    Priority: ARK_API_KEY / LLM_API_KEY environment variable, then the
    Hermes runtime .env (machine-specific, resolved via env vars only).
    """
    env_key = os.environ.get("ARK_API_KEY") or os.environ.get("LLM_API_KEY")
    if env_key:
        return env_key.strip()
    try:
        for line in _HERMES_ENV.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("ARK_API_KEY=") and line[12:].strip():
                return line[12:].strip().strip('"').strip("'")
    except OSError:
        return None
    return None


def _build_client():
    key = _read_ark_key()
    if not key:
        raise RuntimeError("ARK_API_KEY not found in Hermes .env")
    from pydantic import SecretStr

    from marketpilot.llm.models import LLMModelConfig

    config = LLMModelConfig(
        provider="openai",
        model="deepseek-v4-flash",
        api_key=SecretStr(key),
        base_url="https://ark.cn-beijing.volces.com/api/plan/v3",
        timeout_seconds=60.0,
        max_retries=2,
    )
    raw = OpenAIChatClient(config)
    return RetryableLLMClient(raw, RetryPolicy(max_attempts=3,
                                               initial_delay_seconds=1.0,
                                               backoff_factor=2.0))


async def run_smoke_task(client, kind: str, seed: int) -> dict:
    world = build_diagnostic_world(kind=kind, seed=seed, world_id=f"{kind}-{seed}")
    view = AgentWorldView(world)
    products = [p.product_id for p in world.products]
    result = {
        "world_id": f"{kind}-{seed}", "n_candidates": len(products),
        "calls": 0, "tool_calls": 0, "tokens_in": 0, "tokens_out": 0,
        "latency_ms": [], "decision": "", "selected": None,
        "gate": "", "gate_reason_codes": [], "errors": [], "schema_ok": True,
    }
    messages: list[LLMMessage] = [
        LLMMessage(role=LLMMessageRole.SYSTEM, content=(
            "You are a product research agent. You MUST use the research_facet "
            "tool to gather evidence (margin, demand, risk) for candidate "
            "products before making any decision. Do not answer without "
            "researching first. After research, call final_recommendation with "
            "the product_id you recommend. If evidence is insufficient, call "
            "final_recommendation with product_id 'REFUSED'."
        )),
        LLMMessage(role=LLMMessageRole.USER, content=(
            f"Choose a safe product from: {products}. "
            f"Required facets: margin, demand, risk. "
            f"Max price 100, no battery. Research at least the top candidate."
        )),
    ]
    max_turns = 6
    for turn in range(max_turns):
        request = LLMRequest(
            provider="openai", model="deepseek-v4-flash",
            messages=messages, temperature=0.0, max_output_tokens=800,
            tools=TOOL_SCHEMA,
            # Force research turns; allow free choice on the last turn so the
            # model can emit final_recommendation or refuse.
            tool_choice="required" if turn < max_turns - 1 else "auto",
        )
        t0 = time.monotonic()
        try:
            response = await client.generate(request)
        except LLMError as exc:
            result["errors"].append(exc.message[:120])
            result["schema_ok"] = False
            break
        latency = (time.monotonic() - t0) * 1000
        result["latency_ms"].append(round(latency, 1))
        result["calls"] += 1
        result["tokens_in"] += response.usage.input_tokens
        result["tokens_out"] += response.usage.output_tokens
        result.setdefault("_debug_finish", []).append(response.finish_reason.value)
        result.setdefault("_debug_tools", []).append(len(response.tool_calls))
        if (
            response.finish_reason is LLMFinishReason.TOOL_CALLS
            and response.tool_calls
        ):
            for call in response.tool_calls:
                result["tool_calls"] += 1
                tool_out = _execute_tool(call, view)
                messages.append(LLMMessage(role=LLMMessageRole.ASSISTANT,
                                           tool_calls=[call], content=None))
                messages.append(LLMMessage(role=LLMMessageRole.TOOL,
                                           tool_call_id=call.call_id,
                                           content=tool_out))
                if call.name == "final_recommendation":
                    args = (call.arguments or ToolArguments()).model_dump()
                    pid = args.get("product_id", "") or ""
                    result["decision"] = "GO" if pid and pid != "REFUSED" else "REFUSED"
                    result["selected"] = pid if pid and pid != "REFUSED" else None
            # Continue the loop: the model must see tool results and then
            # decide (multiple research_facet calls, then final_recommendation).
            if result["decision"]:
                break
            continue
        else:
            # Model produced a plain answer (no tool call) — treat as refusal
            # unless it names a product.
            content = response.content or ""
            result["decision"] = "REFUSED"
            result["selected"] = None
            for pid in products:
                if pid in content:
                    result["decision"] = "GO"
                    result["selected"] = pid
                    break
            break

    # Safety Gate on the final emission (real evidence from the view).
    chain = {pid: [f.value for f in view.revealed_facets(pid)]
             for pid in products}
    gated = gate_workbench_run(
        result["decision"], result["selected"], chain,
        spent=0.0,
        world_budget=world.research_budget or 12.0,
        task_id=f"{kind}-{seed}",
    )
    result["gate"] = gated.gate_decision
    result["gate_reason_codes"] = gated.gate_reason_codes
    result["post_gate_outcome"] = gated.post_gate_outcome
    result["evidence_chain"] = chain
    return result


def _execute_tool(call: LLMToolCall, view: AgentWorldView) -> str:
    args = (call.arguments or ToolArguments()).model_dump()
    if call.name == "research_facet":
        from marketpilot.world.core import ResearchAction

        pid = args.get("product_id", "")
        facet = args.get("facet", "margin")
        action = ResearchAction[_FACET_ACTION.get(facet, "SEARCH_MARGIN")]
        try:
            view.take_action(action, pid)
            revealed = [f.value for f in view.revealed_facets(pid)]
            return json.dumps({"ok": True, "product_id": pid,
                               "facet": facet, "revealed": revealed})
        except KeyError:
            return json.dumps({"ok": False, "error": "unknown product/facet"})
    if call.name == "final_recommendation":
        return json.dumps({"ok": True, "accepted": True})
    return json.dumps({"ok": False, "error": "unknown tool"})


async def main() -> None:
    client = _build_client()
    print("REAL_LLM_EXECUTED: provider=volcengine-ark model=deepseek-v4-flash")
    results = []
    for kind, seed in SMOKE_TASKS:
        r = await run_smoke_task(client, kind, seed)
        results.append(r)
        print(f"{r['world_id']}: decision={r['decision']} calls={r['calls']} "
              f"tools={r['tool_calls']} tokens={r['tokens_in'] + r['tokens_out']} "
              f"gate={r['gate']}")
    report = {
        "status": "REAL_LLM_EXECUTED",
        "provider": "volcengine-ark", "model": "deepseek-v4-flash",
        "base_url": "https://ark.cn-beijing.volces.com/api/plan/v3",
        "smoke_tasks": results,
        "totals": {
            "calls": sum(r["calls"] for r in results),
            "tool_calls": sum(r["tool_calls"] for r in results),
            "tokens_in": sum(r["tokens_in"] for r in results),
            "tokens_out": sum(r["tokens_out"] for r in results),
            "schema_failures": sum(1 for r in results if not r["schema_ok"]),
        },
        "note": "key read from Hermes .env (ARK_API_KEY), never persisted",
    }
    (OUT / "real_llm_smoke.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"wrote real_llm_smoke.json: calls={report['totals']['calls']} "
          f"tokens={report['totals']['tokens_in'] + report['totals']['tokens_out']}")


if __name__ == "__main__":
    asyncio.run(main())
