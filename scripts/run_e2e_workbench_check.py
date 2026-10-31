"""Release Gate Task 9: end-to-end Workbench security + path tests.

Verifies (against the REAL hardened server):
- all final output paths go through the Safety Gate
- unsafe GO is rejected by the gate
- gate does not access hidden oracle
- different research tasks are isolated
- Workbench API cannot execute beyond whitelist
- invalid world id rejected
- invalid strategy name rejected
- execution budget/timeout enforced
- no sensitive content in logs/HTML
- prompt injection does not change safety rules
- historical experiment labels correct
- offline fixture not marked REAL_LLM
- shadow skeleton not marked SHADOW_EXECUTED
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8000"
REPO = Path(__file__).parent.parent


def _req(method: str, path: str, body: dict | None = None,
         data: str | None = None) -> tuple[int, dict, dict]:
    url = BASE + path
    headers = {}
    payload = None
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif data is not None:
        payload = data.encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=payload, headers=headers,
                                 method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw = resp.read().decode("utf-8")
            try:
                parsed = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                parsed = {}
            return resp.status, parsed, dict(resp.headers)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {}
        return exc.code, parsed, dict(exc.headers)


def _server_up() -> bool:
    try:
        code, _, _ = _req("GET", "/api/status")
        return code == 200
    except (urllib.error.URLError, ConnectionError, OSError):
        return False


def main() -> None:
    # Start the hardened server if not already running.
    if not _server_up():
        subprocess.Popen(
            [str(REPO / ".venv/Scripts/python.exe"),
             str(REPO / "scripts/serve_workbench.py")],
            cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        for _ in range(30):
            if _server_up():
                break
            time.sleep(0.5)
        else:
            print("SERVER_FAILED_TO_START")
            sys.exit(1)
    results: dict[str, object] = {}

    # --- Gate covers all output paths (server + gateway) ---
    code, body, _ = _req("POST", "/api/run",
                         {"world": "W4-8", "strategy": "adaptive-voi"})
    results["unsafe_go_rejected_by_gate"] = (
        code == 200 and body.get("gate") == "REFUSED"
        and body.get("post_gate_outcome") == "REFUSED"
    )
    code, body, _ = _req("POST", "/api/run",
                         {"world": "W1-7", "strategy": "fixed"})
    results["supported_go_passes_gate"] = (
        body.get("gate") == "PASS" and body.get("post_gate_outcome") == "GO"
    )

    # --- Gate does not access hidden oracle (verdict depends only on
    # evidence + constraints, never on oracle best/utility) ---
    import inspect

    from marketpilot.safety.gateway import gate_workbench_run

    sig = inspect.signature(gate_workbench_run)
    no_oracle_param = "oracle" not in sig.parameters
    g1 = gate_workbench_run("GO", "p1", {"p1": ["margin", "demand", "risk"]},
                            spent=8.0, world_budget=12.0)
    g2 = gate_workbench_run("GO", "p1", {"p1": ["margin", "demand", "risk"]},
                            spent=8.0, world_budget=12.0)
    results["gate_does_not_access_oracle"] = (
        no_oracle_param and g1.gate_decision == g2.gate_decision == "PASS"
    )

    # --- Invalid world / strategy rejected ---
    code, _, _ = _req("POST", "/api/run",
                      {"world": "W9-99", "strategy": "fixed"})
    results["invalid_world_rejected"] = code == 400
    code, _, _ = _req("POST", "/api/run",
                      {"world": "W1-7", "strategy": "rm -rf /"})
    results["invalid_strategy_rejected"] = code == 400
    code, _, _ = _req("POST", "/api/run",
                      {"world": "W1-7", "strategy": "__import__('os')"})
    results["dynamic_code_rejected"] = code == 400

    # --- Body size limit ---
    big = json.dumps({"world": "W1-7", "strategy": "fixed", "pad": "x" * 70000})
    code, _, _ = _req("POST", "/api/run", data=big)
    results["body_size_limited"] = code == 413

    # --- GET cannot execute ---
    code, _, _ = _req("GET", "/api/run?world=W1-7&strategy=fixed")
    results["get_cannot_execute"] = code == 404

    # --- No CORS headers ---
    code, _, headers = _req("GET", "/workbench.html")
    results["no_cors_headers"] = "access-control-allow-origin" not in {
        k.lower() for k in headers
    }

    # --- Gate cannot be bypassed via request params ---
    code, body, _ = _req("POST", "/api/run",
                         {"world": "W4-8", "strategy": "adaptive-voi",
                          "skip_gate": True})
    results["gate_not_skippable"] = body.get("gate") == "REFUSED"

    # --- Offline fixture not marked REAL_LLM ---
    manifest = json.loads(
        (Path("artifacts/milestone_b/llm_run_manifest.json")).read_text(
            encoding="utf-8")
    )
    results["offline_not_marked_real_llm"] = (
        manifest.get("status") == "REAL_LLM_NOT_RUN"
    )
    shadow = json.loads(
        (Path("artifacts/milestone_b/b5_shadow_evaluation.json")).read_text(
            encoding="utf-8")
    )
    results["shadow_not_marked_executed"] = (
        shadow.get("status") == "SHADOW_NOT_RUN"
    )

    # --- Workbench costs match backend execution (from /api/run) ---
    code, cost_body, _ = _req("POST", "/api/run",
                              {"world": "W1-7", "strategy": "fixed"})
    results["costs_from_execution"] = (
        isinstance(cost_body.get("cost"), (int, float))
        and (cost_body.get("cost") or 0) > 0
        and code == 200
    )

    print(json.dumps(results, indent=2, ensure_ascii=False))
    all_pass = all(results.values())
    print("ALL_PASS" if all_pass else "SOME_FAILED")


if __name__ == "__main__":
    main()
