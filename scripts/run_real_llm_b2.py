"""Release Gate Task B2: real-LLM vs deterministic paired experiment.

24 frozen worlds (W0-W5 x seeds 7-10): each world is run by
- Fixed deterministic controller (existing ParameterizedPolicy)
- REAL LLM agent (volcengine-ark / deepseek-v4-flash, key from Hermes .env)

Records: model id, prompt hash, provider, tool calls, tokens, cost
estimate, latency, schema success, pre-gate unsupported GO, gate
interceptions, post-gate supported GO, abstention, failure reasons.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from run_real_llm_smoke import _build_client, run_smoke_task

from marketpilot.evaluation.outcomes import classify_outcome
from marketpilot.optimization.dream_rsi import ParameterizedPolicy
from marketpilot.world.core import AgentWorldView, WorldOracle, build_diagnostic_world

OUT = Path("artifacts/milestone_b")
WORLDS = [(kind, seed) for kind in ("W0", "W1", "W2", "W3", "W4", "W5")
          for seed in (7, 8, 9, 10)]

PROMPT_TEXT = (
    "You are a product research agent. You MUST use the research_facet "
    "tool to gather evidence (margin, demand, risk) for candidate products "
    "before making any decision. Do not answer without researching first. "
    "After research, call final_recommendation with the product_id you "
    "recommend. If evidence is insufficient, call final_recommendation "
    "with product_id 'REFUSED'."
)
PROMPT_HASH = hashlib.sha256(PROMPT_TEXT.encode()).hexdigest()[:16]


def _run_deterministic(kind: str, seed: int) -> dict:
    world = build_diagnostic_world(kind=kind, seed=seed, world_id=f"{kind}-{seed}")
    oracle = WorldOracle(world)
    pol = ParameterizedPolicy(strategy="fixed", name="fixed")
    result = pol.execute(AgentWorldView(world))
    outcome = classify_outcome(result, oracle)
    return {
        "world_id": f"{kind}-{seed}",
        "decision": result.decision,
        "selected": result.selected_id,
        "cost": round(result.total_cost, 2),
        "outcome": outcome.outcome_status.value,
        "reason": outcome.reason_code,
        "evidence_sufficient": outcome.evidence_sufficient,
        "n_steps": len(result.steps),
    }


async def main() -> None:
    client = _build_client()
    rows = []
    for kind, seed in WORLDS:
        det = _run_deterministic(kind, seed)
        llm = await run_smoke_task(client, kind, seed)
        rows.append({
            "world_id": f"{kind}-{seed}",
            "deterministic": det,
            "llm": {
                "decision": llm["decision"],
                "selected": llm["selected"],
                "calls": llm["calls"],
                "tool_calls": llm["tool_calls"],
                "tokens_in": llm["tokens_in"],
                "tokens_out": llm["tokens_out"],
                "latency_ms": llm["latency_ms"],
                "errors": llm["errors"],
                "schema_ok": llm["schema_ok"],
                "gate": llm["gate"],
                "gate_reason_codes": llm["gate_reason_codes"],
                "post_gate_outcome": llm["post_gate_outcome"],
            },
        })
        print(f"{kind}-{seed}: det={det['decision']} llm={llm['decision']} "
              f"llm_gate={llm['gate']} tools={llm['tool_calls']} "
              f"tokens={llm['tokens_in'] + llm['tokens_out']}")

    # Aggregates.
    n = len(rows)
    det_go = sum(1 for r in rows if r["deterministic"]["decision"] == "GO")
    llm_go = sum(1 for r in rows if r["llm"]["decision"] == "GO")
    llm_gate_pass = sum(1 for r in rows if r["llm"]["gate"] == "PASS")
    llm_intercepted = sum(
        1 for r in rows
        if r["llm"]["decision"] == "GO" and r["llm"]["gate"] == "REFUSED"
    )
    total_tokens = sum(r["llm"]["tokens_in"] + r["llm"]["tokens_out"] for r in rows)
    total_calls = sum(r["llm"]["calls"] for r in rows)
    total_tools = sum(r["llm"]["tool_calls"] for r in rows)
    all_lat = [ms for r in rows for ms in r["llm"]["latency_ms"]]
    all_lat.sort()
    p50 = all_lat[len(all_lat) // 2] if all_lat else 0
    p95 = all_lat[int(len(all_lat) * 0.95)] if all_lat else 0

    report = {
        "status": "REAL_LLM_EXECUTED",
        "provider": "volcengine-ark", "model": "deepseek-v4-flash",
        "base_url": "https://ark.cn-beijing.volces.com/api/plan/v3",
        "prompt_hash": PROMPT_HASH,
        "n_worlds": n,
        "temperature": 0.0,
        "max_output_tokens": 800,
        "max_turns": 6,
        "totals": {
            "deterministic_go": det_go,
            "llm_go": llm_go,
            "llm_gate_pass": llm_gate_pass,
            "llm_gate_interceptions": llm_intercepted,
            "llm_calls": total_calls,
            "llm_tool_calls": total_tools,
            "llm_tokens_in": sum(r["llm"]["tokens_in"] for r in rows),
            "llm_tokens_out": sum(r["llm"]["tokens_out"] for r in rows),
            "llm_total_tokens": total_tokens,
            "llm_schema_failures": sum(1 for r in rows if not r["llm"]["schema_ok"]),
            "llm_latency_p50_ms": p50,
            "llm_latency_p95_ms": p95,
            "llm_estimated_cost_usd": None,  # no pricing table for this provider
        },
        "per_world": rows,
        "note": "key read from Hermes .env (ARK_API_KEY), never persisted; "
                "cost estimate unavailable (no provider pricing table)",
    }
    (OUT / "real_llm_vs_deterministic.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nwrote real_llm_vs_deterministic.json: {n} worlds, "
          f"tokens={total_tokens}, calls={total_calls}, tools={total_tools}, "
          f"p50={p50}ms p95={p95}ms")


if __name__ == "__main__":
    asyncio.run(main())
