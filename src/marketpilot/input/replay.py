"""Tool Replay vs Full Trajectory Replay (Phase 1).

v1 already has an environment-level `ReplayStore` (request key -> payload) in
`research/replay.py`. That is TOOL replay. Phase 1 adds the explicit
distinction and a trajectory-level replay record type, which is what Phase 5
(Dream-RSI Historical Replay Simulator) will consume. The rule is: trajectory
replay only replays *observed* state transitions; unknown actions are rejected
and coverage is reported explicitly.
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ReplayKind(StrEnum):
    """Explicit distinction between tool-level and trajectory-level replay."""

    TOOL = "tool"
    TRAJECTORY = "trajectory"


class ToolReplayRecord(BaseModel):
    """One tool-level replay entry (what v1 ReplayStore already stores)."""

    model_config = ConfigDict(frozen=True)

    kind: ReplayKind = ReplayKind.TOOL
    request_key: str = Field(min_length=1, max_length=128)
    tool_name: str = Field(min_length=1, max_length=100)
    payload: dict[str, Any] = Field(default_factory=dict)


class TrajectoryReplayRecord(BaseModel):
    """One observed state transition that trajectory replay may re-execute."""

    model_config = ConfigDict(frozen=True)

    kind: ReplayKind = ReplayKind.TRAJECTORY
    step_index: int = Field(ge=0)
    action: str = Field(min_length=1, max_length=200)
    state_before_hash: str = Field(min_length=8, max_length=128)
    state_after_hash: str = Field(min_length=8, max_length=128)
    observation: str = Field(default="", max_length=2000)
    outcome: str = Field(default="", max_length=200)
    raw_record: dict[str, Any] = Field(default_factory=dict)


def classify_replay_record(record: dict[str, Any]) -> ReplayKind:
    """Classify a raw replay record as tool-level or trajectory-level."""
    kind = record.get("kind")
    if kind == ReplayKind.TRAJECTORY.value or "state_before_hash" in record:
        return ReplayKind.TRAJECTORY
    if kind == ReplayKind.TOOL.value or "request_key" in record:
        return ReplayKind.TOOL
    # Heuristic fallback: tool replay has request_key; trajectory has step_index.
    if "step_index" in record:
        return ReplayKind.TRAJECTORY
    return ReplayKind.TOOL


def trajectory_replay_coverage(
    records: list[dict[str, Any]],
    *,
    total_steps: int | None = None,
) -> dict[str, int | float]:
    """Report coverage of a trajectory replay archive.

    Coverage = observed steps / total steps (when known). Unknown actions are
    never assumed to be replayable; they simply lower coverage.
    """
    if not records:
        return {"observed_steps": 0, "total_steps": total_steps or 0, "coverage": 0.0}
    observed = sum(
        1
        for record in records
        if classify_replay_record(record) is ReplayKind.TRAJECTORY
    )
    total = total_steps if total_steps is not None else observed
    coverage = observed / total if total else 0.0
    return {
        "observed_steps": observed,
        "total_steps": total,
        "coverage": round(coverage, 4),
    }
