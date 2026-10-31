"""Milestone C: local demo server for the Agent Workbench.

Serves workbench.html and exposes POST /run?world=W1-7&strategy=fixed
which executes the REAL deterministic strategy against the frozen synthetic
world and returns the result as JSON (evidence chain + gate + outcome).

Usage:  python scripts/serve_workbench.py   (then open http://localhost:8000)
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from marketpilot.evaluation.outcomes import classify_outcome
from marketpilot.optimization.dream_rsi import ParameterizedPolicy
from marketpilot.safety.trust import AuthoritativeTaskState, gate_with_authoritative_state
from marketpilot.world.core import AgentWorldView, WorldOracle, build_diagnostic_world

WORLD_KINDS = ["W0", "W1", "W2", "W3", "W4", "W5"]
STRATEGIES = ["fixed", "missing-evidence", "uncertainty", "adaptive-voi",
              "contextual-hybrid"]
MAX_STEPS = 24
MAX_SECONDS = 10.0
MAX_BODY_BYTES = 64 * 1024
VALID_WORLDS = frozenset(
    f"{k}-{s}" for k in WORLD_KINDS for s in range(7, 11)
)


def run_world(world_id: str, strategy: str) -> dict[str, Any]:
    # Whitelist validation FIRST (no dynamic execution, no path traversal).
    if world_id not in VALID_WORLDS:
        raise ValueError(f"unknown world id: {world_id}")
    if strategy not in STRATEGIES:
        raise ValueError(f"unknown strategy: {strategy}")
    kind, seed_s = world_id.split("-")
    seed = int(seed_s)
    world = build_diagnostic_world(kind=kind, seed=seed, world_id=world_id)
    oracle = WorldOracle(world)
    view = AgentWorldView(world)
    pol = ParameterizedPolicy(strategy=strategy, name=strategy)
    start = time.monotonic()
    result = pol.execute(view)
    elapsed = time.monotonic() - start
    if len(result.steps) > MAX_STEPS:
        raise ValueError("execution exceeded step limit")
    if elapsed > MAX_SECONDS:
        raise ValueError("execution exceeded time limit")
    outcome = classify_outcome(result, oracle)
    # Evidence chain: what was revealed per candidate.
    evidence_chain = {
        pid: [facet.value for facet in view.revealed_facets(pid)]
        for pid in [p.product_id for p in world.products]
    }
    # Safety Gate with AUTHORITATIVE state (the executed view is the source
    # of truth; the submitted chain is cross-checked, never trusted).
    auth_state = AuthoritativeTaskState(world, view)
    gated, _integrity = gate_with_authoritative_state(
        "workbench.run", result.decision, result.selected_id,
        evidence_chain, auth_state,
        spent=result.total_cost,
        world_budget=world.research_budget or 12.0,
        task_id=world_id,
    )
    return {
        "world": world_id, "strategy": strategy,
        "decision": result.decision,
        "selected": result.selected_id,
        "cost": round(result.total_cost, 2),
        "steps": len(result.steps),
        "outcome": outcome.outcome_status.value,
        "reason": outcome.reason_code,
        "evidence_chain": evidence_chain,
        "oracle_best": oracle.best_product_id(),
        "gate": gated.gate_decision,
        "gate_reason_codes": gated.gate_reason_codes,
        "post_gate_outcome": gated.post_gate_outcome,
        "elapsed_ms": round(elapsed * 1000, 1),
    }


def main() -> None:
    import http.server
    import urllib.parse

    ROOT = Path(__file__).parent.parent
    OUT_DIR = ROOT / "artifacts" / "milestone_c"

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args: object, **kwargs: object) -> None:  # type: ignore[misc]
            super().__init__(*args, directory=str(OUT_DIR), **kwargs)

        def _send_json(self, code: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path in ("/", "/workbench.html"):
                self.path = "/workbench.html"
                super().do_GET()
                return
            if parsed.path == "/api/status":
                self._send_json(200, {"ok": True, "mode": "synthetic",
                                      "whitelisted_worlds": len(VALID_WORLDS)})
                return
            self._send_json(404, {"error": "not_found",
                                  "reason_code": "NOT_FOUND"})

        def do_POST(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != "/api/run":
                self._send_json(404, {"error": "not_found",
                                      "reason_code": "NOT_FOUND"})
                return
            length = int(self.headers.get("Content-Length", 0))
            if length <= 0 or length > MAX_BODY_BYTES:
                self._send_json(413, {"error": "body_too_large",
                                      "reason_code": "BODY_TOO_LARGE"})
                return
            try:
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._send_json(400, {"error": "invalid_json",
                                      "reason_code": "INVALID_JSON"})
                return
            world = str(payload.get("world", ""))
            strategy = str(payload.get("strategy", ""))
            try:
                data = run_world(world, strategy)
                self._send_json(200, data)
            except ValueError as exc:
                self._send_json(400, {"error": str(exc),
                                      "reason_code": "INVALID_ARGUMENT"})

        def log_message(self, format: str, *args: object) -> None:
            print(f"[workbench] {format % args}")

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 8000), Handler)
    server.daemon_threads = True
    print("Workbench (hardened): http://127.0.0.1:8000/workbench.html")
    print("Execution: POST /api/run (world+strategy whitelist, safety-gated)")
    print("Binds 127.0.0.1 only. Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")


if __name__ == "__main__":
    main()
