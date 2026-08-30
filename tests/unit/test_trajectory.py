"""Trajectory event tests."""

import json
from pathlib import Path
from uuid import uuid4

from marketpilot.domain.enums import EventType
from marketpilot.observability.trajectory import TrajectoryRecorder


def test_trajectory_sequence_and_jsonl(tmp_path: Path) -> None:
    run_id = uuid4()
    recorder = TrajectoryRecorder(run_id=run_id)
    recorder.record(EventType.RUN_STARTED, actor="DAGRunner", input_summary="goal")
    recorder.record(EventType.TASK_STARTED, actor="MarketResearch", output_summary="task")
    recorder.record(EventType.RUN_COMPLETED, actor="DAGRunner", output_summary="done")

    assert [event.sequence_number for event in recorder.events] == [0, 1, 2]
    assert len({event.event_id for event in recorder.events}) == 3

    path = tmp_path / "trajectory.jsonl"
    recorder.write_trajectory(path)
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(events) == 3
    assert all(event["run_id"] == str(run_id) for event in events)
    assert all("event_id" in event and "timestamp" in event for event in events)
