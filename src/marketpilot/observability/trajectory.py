"""Event-sourced trajectory recording and run artifact persistence."""

import json
from hashlib import sha256
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from marketpilot.domain.enums import EventType
from marketpilot.domain.state import ResearchState
from marketpilot.observability.events import AgentEvent, ErrorInfo


def _digest(value: str | None) -> str | None:
    if value is None:
        return None
    return sha256(value.encode()).hexdigest()


class TrajectoryRecorder:
    """Record ordered events and write machine-readable run artifacts."""

    def __init__(self, run_id: UUID) -> None:
        self.run_id = run_id
        self._events: list[AgentEvent] = []

    @property
    def events(self) -> tuple[AgentEvent, ...]:
        return tuple(self._events)

    def record(
        self,
        event_type: EventType,
        actor: str,
        task_id: UUID | None = None,
        parent_event_id: UUID | None = None,
        input_summary: str | None = None,
        output_summary: str | None = None,
        metadata: dict[str, str | int | float | bool | None] | None = None,
        duration_ms: int = 0,
        error: ErrorInfo | None = None,
    ) -> AgentEvent:
        sequence = len(self._events)
        event = AgentEvent(
            event_id=uuid5(NAMESPACE_URL, f"marketpilot:event:{self.run_id}:{sequence}"),
            sequence_number=sequence,
            run_id=self.run_id,
            task_id=task_id,
            actor=actor,
            event_type=event_type,
            parent_event_id=parent_event_id,
            input_summary=input_summary,
            input_hash=_digest(input_summary),
            output_summary=output_summary,
            output_hash=_digest(output_summary),
            metadata=metadata or {},
            duration_ms=duration_ms,
            error=error,
        )
        self._events.append(event)
        return event

    def write_trajectory(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for event in self._events:
                handle.write(event.model_dump_json() + "\n")

    def write_final_state(self, path: Path, state: ResearchState) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(state.model_dump_json(indent=2), encoding="utf-8")

    def write_summary(self, path: Path, summary: dict[str, str | int | float | bool]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
