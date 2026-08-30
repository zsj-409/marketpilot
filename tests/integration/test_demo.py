"""End-to-end offline demo tests."""

import json
from pathlib import Path

from marketpilot.cli import DEFAULT_GOAL, _run_demo
from marketpilot.domain.state import ResearchState


async def test_demo_creates_valid_artifacts(tmp_path: Path) -> None:
    run_dir = await _run_demo(DEFAULT_GOAL, tmp_path)

    trajectory_path = run_dir / "trajectory.jsonl"
    final_state_path = run_dir / "final_state.json"
    summary_path = run_dir / "summary.json"

    assert trajectory_path.exists()
    assert final_state_path.exists()
    assert summary_path.exists()

    events = [
        json.loads(line)
        for line in trajectory_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    assert events
    assert [event["sequence_number"] for event in events] == list(range(len(events)))

    state = ResearchState.model_validate_json(final_state_path.read_text(encoding="utf-8"))
    assert state.status.value == "COMPLETED"
    assert state.recommendations

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["status"] == "COMPLETED"
    assert summary["evaluation_passed"] is True
    assert summary["decision"] == "WATCH"
