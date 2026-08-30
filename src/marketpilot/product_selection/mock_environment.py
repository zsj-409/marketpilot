"""Deterministic mock research environment for closed-loop tests."""

from typing import Any
from uuid import UUID, uuid4

from marketpilot.product_selection.workers import ResearchEnvironment


class MockResearchEnvironment(ResearchEnvironment):
    def __init__(self, candidates: list[dict[str, Any]]) -> None:
        self._candidates = candidates
        self._evidence: dict[UUID, dict[str, list[str]]] = {
            UUID(str(candidate["candidate_id"])): {
                "demand": [candidate.get("demand", "moderate demand")],
                "competition": [candidate.get("competition", "medium competition")],
                "risk": [candidate.get("risk", "low risk")],
            }
            for candidate in candidates
        }
        self.followups: list[str] = []

    def candidates(self) -> list[dict[str, Any]]:
        return self._candidates

    def evidence(self, candidate_id: UUID) -> dict[str, list[str]]:
        return self._evidence.get(candidate_id, {})

    def add_evidence(self, candidate_id: UUID, facet: str, observation: str) -> None:
        self._evidence.setdefault(candidate_id, {}).setdefault(facet, []).append(observation)


def make_environment() -> MockResearchEnvironment:
    return MockResearchEnvironment(
        [
            {
                "candidate_id": str(uuid4()),
                "title": "Candidate A",
                "price": 40.0,
                "battery": False,
            },
            {
                "candidate_id": str(uuid4()),
                "title": "Candidate B",
                "price": 55.0,
                "battery": False,
            },
        ]
    )
