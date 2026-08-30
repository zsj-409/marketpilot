"""Structured episodic memory."""

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class Episode:
    episode_id: str
    category: str
    task_type: str
    constraints: frozenset[str] = field(default_factory=frozenset)
    evidence_patterns: tuple[str, ...] = field(default_factory=tuple)
    failure_reason: str | None = None
    verifier_feedback: tuple[str, ...] = field(default_factory=tuple)
    decision_outcome: str = "UNKNOWN"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class EpisodicMemory:
    """Transparent structured retrieval, not neural semantic memory."""

    def __init__(self) -> None:
        self._episodes: dict[str, Episode] = {}

    def store(self, episode: Episode) -> Episode:
        self._episodes[episode.episode_id] = episode
        return episode

    def retrieve(
        self,
        *,
        category: str | None = None,
        task_type: str | None = None,
        constraints: set[str] | None = None,
    ) -> list[Episode]:
        scored: list[tuple[float, Episode]] = []
        for episode in self._episodes.values():
            score = 0.0
            if category is not None and episode.category == category:
                score += 3.0
            if task_type is not None and episode.task_type == task_type:
                score += 2.0
            if constraints is not None:
                overlap = constraints & set(episode.constraints)
                if constraints:
                    score += 2.0 * len(overlap) / len(constraints)
            if score > 0:
                scored.append((score, episode))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [episode for _, episode in scored]

    def all(self) -> list[Episode]:
        return list(self._episodes.values())

    def __len__(self) -> int:
        return len(self._episodes)
