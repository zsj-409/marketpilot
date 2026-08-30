"""Optional live OpenAI smoke test.

This test is intentionally skipped unless MARKETPILOT_LLM_API_KEY is present.
It never runs in normal CI and should not be considered part of offline
verification.
"""

import os
from pathlib import Path

import pytest

from marketpilot.cli import DEFAULT_GOAL, _build_llm_runtime, _run_demo
from marketpilot.config import MarketPilotSettings


@pytest.mark.skipif(
    not os.getenv("MARKETPILOT_LLM_API_KEY"),
    reason="MARKETPILOT_LLM_API_KEY is not set",
)
async def test_openai_live_smoke(tmp_path: Path) -> None:
    settings = MarketPilotSettings(
        mode="llm",
        llm_provider="openai",
        llm_model=os.getenv("MARKETPILOT_LLM_MODEL", "gpt-4o-mini"),
        llm_api_key=os.getenv("MARKETPILOT_LLM_API_KEY"),
        runs_dir=tmp_path,
    )
    agent_registry = _build_llm_runtime(settings)
    run_dir = await _run_demo(
        DEFAULT_GOAL,
        tmp_path,
        agent_registry,
        mode="llm",
        provider="openai",
        model=settings.llm_model,
    )
    assert (run_dir / "trajectory.jsonl").exists()
    assert (run_dir / "final_state.json").exists()
    assert (run_dir / "summary.json").exists()
