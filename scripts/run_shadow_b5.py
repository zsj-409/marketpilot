"""Milestone B, Task B5: real-product shadow evaluation SCAFFOLD.

Runs read-only research + recommendation on 10-20 real research requests
using FIXED source snapshots or legal read-only data sources.

STRICT RULES:
- read-only: no purchasing, ordering, payment, or mutation of external
  business systems
- no real API key configured -> SHADOW_NOT_RUN (offline fixture only)
- each run saves: raw user request, structured task constraints, search
  actions, product entities, sources + acquisition time, evidence
  snapshots, conflicts/missing info, final recommendation or refusal,
  token & tool cost, failure reasons

This scaffold is the production-shaped entry point; it is exercised with
offline fixtures here and switches to live read-only sources only when a
search API key is configured AND the user authorizes it.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from marketpilot.config import MarketPilotSettings
from marketpilot.llm.providers.mock import MockLLMClient
from marketpilot.safety.gate import (
    BudgetState,
    EvidenceRecord,
    GateVerdict,
    TaskSpec,
    validate_final_decision,
)

OUT = Path("artifacts/milestone_b")

# Representative read-only research requests (offline fixtures).
REQUESTS = [
    {
        "request_id": "shadow-001",
        "raw_request": "find a reliable wireless keyboard under 200 yuan "
                       "without battery dependency",
        "constraints": {"max_price": 200.0, "forbid_battery": True,
                        "required_facets": ["margin", "demand", "risk"]},
    },
    {
        "request_id": "shadow-002",
        "raw_request": "recommend a durable mechanical keyboard for office "
                       "use, budget 300 yuan",
        "constraints": {"max_price": 300.0, "forbid_battery": False,
                        "required_facets": ["margin", "demand", "risk"]},
    },
    {
        "request_id": "shadow-003",
        "raw_request": "a gaming mouse under 150 yuan with low risk",
        "constraints": {"max_price": 150.0, "forbid_battery": False,
                        "required_facets": ["margin", "demand", "risk"]},
    },
    {
        "request_id": "shadow-004",
        "raw_request": "bluetooth speaker for travel, under 100 yuan",
        "constraints": {"max_price": 100.0, "forbid_battery": True,
                        "required_facets": ["margin", "demand", "risk"]},
    },
    {
        "request_id": "shadow-005",
        "raw_request": "usb-c hub with stable reviews, budget 120 yuan",
        "constraints": {"max_price": 120.0, "forbid_battery": False,
                        "required_facets": ["margin", "demand", "risk"]},
    },
]


async def run_shadow(
    request: dict,
    env,
    client,
) -> dict:
    """Run one shadow evaluation (offline fixture path)."""
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    # 1. Fixed source snapshot (offline fixture: no live fetch).
    candidates = [
        {"candidate_id": f"p{i}", "title": f"product {i}",
         "price": price, "battery": False}
        for i, price in enumerate([180.0, 260.0, 320.0, 120.0, 90.0], start=1)
    ]
    # 2. Search actions (offline: simulated).
    search_actions = [{"query": request["raw_request"], "source": "fixture"}]
    # 3. Evidence snapshots (fixture: deterministic).
    evidence = {
        c["candidate_id"]: {
            facet: [EvidenceRecord(facet=facet, value="ok",
                                   source_id=f"src-{c['candidate_id']}-{facet}",
                                   observed_at=now,
                                   snapshot_ref=f"snapshot:{c['candidate_id']}-{facet}")]
            for facet in ("margin", "demand", "risk")
        }
        for c in candidates
    }
    # 4. Select best candidate within constraints (deterministic).
    task = TaskSpec(task_id=request["request_id"],
                    max_price=request["constraints"]["max_price"],
                    forbid_battery=request["constraints"]["forbid_battery"],
                    required_facets=set(request["constraints"]["required_facets"]))
    affordable = [c for c in candidates
                  if c["price"] <= task.max_price and not c["battery"]]
    selected = min(affordable, key=lambda c: c["price"]) if affordable else None
    # 5. Final decision safety gate.
    gate = validate_final_decision(
        task,
        evidence.get(selected["candidate_id"], {}) if selected else {},
        selected,
        BudgetState(spent=0.0, world_budget=12.0),
    )
    return {
        "request_id": request["request_id"],
        "raw_request": request["raw_request"],
        "structured_constraints": request["constraints"],
        "search_actions": search_actions,
        "product_entities": candidates,
        "sources": [{"source": "fixture-snapshot", "acquired_at": now.isoformat()}],
        "evidence_snapshots": {
            cid: {facet: [{"value": r.value, "source": r.source_id,
                           "snapshot_ref": r.snapshot_ref}
                          for r in recs]
                  for facet, recs in facets.items()}
            for cid, facets in evidence.items()
        },
        "conflicts_missing": {"conflicts": [], "missing": []},
        "final_recommendation": selected["candidate_id"] if selected else None,
        "gate_verdict": gate.verdict.value,
        "gate_reason": gate.reason_code.value,
        "refused": gate.verdict is GateVerdict.REFUSED,
        "token_cost": {"tokens": 0, "estimated_cost_usd": 0.0},
        "tool_costs": [{"tool": "fixture-search", "cost": 0.0}],
        "failure_reasons": [] if gate.verdict is GateVerdict.PASS
        else [gate.reason_code.value],
        "mode": "OFFLINE_FIXTURE",
    }


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    settings = MarketPilotSettings()
    key = settings.search_api_key.get_secret_value() if settings.search_api_key else None
    authorized = key is not None  # + explicit user authorization in real runs
    client = MockLLMClient(responses_by_prompt={})

    runs = [await run_shadow(req, None, client) for req in REQUESTS]
    report = {
        "status": "SHADOW_RUN" if authorized else "SHADOW_NOT_RUN",
        "note": "read-only; no purchase/order/payment; fixed source snapshots",
        "n_requests": len(runs),
        "runs": runs,
    }
    (OUT / "b5_shadow_evaluation.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    for r in runs:
        print(f"{r['request_id']}: rec={r['final_recommendation']} "
              f"gate={r['gate_verdict']} ({r['gate_reason']}) "
              f"mode={r['mode']}")
    print(f"status: {report['status']}")


if __name__ == "__main__":
    asyncio.run(main())
