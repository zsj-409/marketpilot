"""Trajectory dataset export with typed reward components."""

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class RewardComponents(BaseModel):
    model_config = ConfigDict(frozen=True)

    task_success: float = Field(ge=0)
    decision_quality: float = Field(ge=0)
    evidence_quality: float = Field(ge=0)
    constraint_score: float = Field(ge=0)
    risk_score: float = Field(ge=0)
    verifier_score: float = Field(ge=0)
    cost_penalty: float = Field(ge=0)
    tool_penalty: float = Field(ge=0)
    latency_penalty: float = Field(ge=0)

    @property
    def aggregate(self) -> float:
        return round(
            self.task_success
            + self.decision_quality
            + self.evidence_quality
            + self.constraint_score
            + self.risk_score
            + self.verifier_score
            - self.cost_penalty
            - self.tool_penalty
            - self.latency_penalty,
            4,
        )


def export_trajectories(run_dir: Path, output_path: Path) -> int:
    """Export a provider-neutral trajectory-learning example set."""

    trajectory_path = run_dir / "trajectory.jsonl"
    if not trajectory_path.exists():
        return 0
    events = [
        json.loads(line)
        for line in trajectory_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    summary_path = run_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    examples = []
    for event in events:
        reward = RewardComponents(
            task_success=1.0 if summary.get("status") == "COMPLETED" else 0.0,
            decision_quality=0.0,
            evidence_quality=1.0 if summary.get("evidence_coverage", 0.0) > 0 else 0.0,
            constraint_score=1.0 if summary.get("evaluation_passed") else 0.0,
            risk_score=0.0,
            verifier_score=0.0,
            cost_penalty=0.0,
            tool_penalty=0.0,
            latency_penalty=0.0,
        )
        examples.append(
            {
                "task": event.get("task_id"),
                "state": {},
                "action": event.get("event_type"),
                "observation": event.get("output_summary"),
                "tool_result": event.get("metadata"),
                "verifier_feedback": [],
                "outcome": summary.get("decision", "NONE"),
                "reward_components": reward.model_dump(),
                "aggregate_reward": reward.aggregate,
            }
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for example in examples:
            handle.write(json.dumps(example, ensure_ascii=False) + "\n")
    return len(examples)
