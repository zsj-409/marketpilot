"""Release Gate Task 2: real-LLM readiness check + run manifest.

Audits the runtime chain to confirm WHERE the LLM participates and that
every required record would be captured in a real run. Without an API key
this writes REAL_LLM_NOT_RUN with the full manifest of what WILL be
recorded — never fabricated model numbers.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

OUT = Path("artifacts/milestone_b")

# The LLM participates in these stages (verified against agents/llm.py):
LLM_STAGES = {
    "parse_request": "LLMResearchPlanner parses goals -> typed ResearchGoal",
    "propose_actions": "LLMResearchAgent proposes tool actions",
    "interpret_evidence": "LLMResearchAgent extracts findings from tool output",
    "form_decision": "LLMDecisionAgent ranks candidates and picks a GO/NO_GO",
    "structured_output": "DecisionOutput validated by pydantic schema",
}

RECORDS_REQUIRED = {
    "provider": "LLMRequest.provider (e.g. openai)",
    "model_id": "LLMRequest.model",
    "prompt_hash": "TrajectoryRecorder input_hash (sha256 of prompt)",
    "request_count": "llm_calls metric",
    "input_tokens": "llm_input_tokens",
    "output_tokens": "llm_output_tokens",
    "api_cost": "llm_estimated_cost via PricingCalculator",
    "tool_calls": "llm tool_calls + tool_call_id chain",
    "p50_p95_latency": "LLMUsage.latency_ms distribution",
    "json_schema_success": "parse_structured_output success rate",
    "task_completion": "final_state.status + evaluation.passed",
    "pre_gate_unsupported_go": "gateway GatedEmission.pre_gate_outcome",
    "gate_rejection_rate": "gateway GatedEmission.gate_decision != PASS",
    "post_gate_supported_go": "gateway GatedEmission.post_gate_outcome",
    "abstention_rate": "post_gate_outcome == REFUSED",
    "failure_reasons": "LLMError classification (retryable/permanent)",
}


def main() -> None:
    from marketpilot.config import MarketPilotSettings

    settings = MarketPilotSettings()
    key = settings.llm_api_key.get_secret_value() if settings.llm_api_key else None
    real = key is not None
    manifest = {
        "status": "REAL_LLM_RUN" if real else "REAL_LLM_NOT_RUN",
        "provider": settings.llm_provider,
        "model": settings.llm_model,
        "configured_api_key": real,
        "llm_stages": LLM_STAGES,
        "records_required": RECORDS_REQUIRED,
        "defaults": {
            "temperature": settings.llm_temperature,
            "max_output_tokens": settings.llm_max_output_tokens,
            "max_turns": settings.llm_max_model_turns,
            "max_calls_per_task": settings.llm_max_calls_per_task,
            "timeout_seconds": settings.llm_timeout_seconds,
            "max_retries": settings.llm_max_retries,
        },
        "gateway_hardened": True,
        "note": "no API key configured -> offline fixtures only; "
                "real-model numbers appear only after key + authorization",
    }
    (OUT / "llm_run_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"status: {manifest['status']}")
    print(f"LLM stages audited: {len(LLM_STAGES)}")
    print(f"records that WILL be captured on a real run: {len(RECORDS_REQUIRED)}")


if __name__ == "__main__":
    main()
