"""End-to-end deterministic LLM runtime integration test."""

import json
from pathlib import Path

from marketpilot.cli import DEFAULT_GOAL, _build_llm_runtime, _run_demo
from marketpilot.config import MarketPilotSettings
from marketpilot.domain.state import ResearchState


async def test_llm_runtime_demo_creates_valid_artifacts(tmp_path: Path) -> None:
    settings = MarketPilotSettings(
        mode="llm",
        llm_provider="mock",
        llm_model="mock-research-model",
        llm_api_key="super-secret-test-key",
        runs_dir=tmp_path,
    )
    agent_registry = _build_llm_runtime(settings)
    run_dir = await _run_demo(
        DEFAULT_GOAL,
        tmp_path,
        agent_registry,
        mode="llm",
        provider="mock",
        model="mock-research-model",
    )

    trajectory = run_dir / "trajectory.jsonl"
    final_state = run_dir / "final_state.json"
    summary = run_dir / "summary.json"
    assert trajectory.exists() and final_state.exists() and summary.exists()

    events = [
        json.loads(line) for line in trajectory.read_text(encoding="utf-8").splitlines() if line
    ]
    assert events
    assert [event["sequence_number"] for event in events] == list(range(len(events)))
    assert len({event["event_id"] for event in events}) == len(events)
    event_types = {event["event_type"] for event in events}
    assert {
        "PROMPT_RENDERED",
        "LLM_REQUESTED",
        "LLM_COMPLETED",
        "TOOL_REQUESTED_BY_MODEL",
    }.issubset(event_types)

    state = ResearchState.model_validate_json(final_state.read_text(encoding="utf-8"))
    assert state.status.value == "COMPLETED"
    assert state.metrics.llm_calls > 0
    assert state.metrics.llm_input_tokens > 0
    assert state.recommendations

    summary_data = json.loads(summary.read_text(encoding="utf-8"))
    assert summary_data["status"] == "COMPLETED"
    assert summary_data["evaluation_passed"] is True
    assert summary_data["llm_calls"] > 0
    assert summary_data["decision"] == "WATCH"

    for artifact in (trajectory, final_state, summary):
        assert "super-secret-test-key" not in artifact.read_text(encoding="utf-8")
