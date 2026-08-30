"""Selective research worker dispatch."""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FollowUpTask(BaseModel):
    model_config = ConfigDict(frozen=True)

    task_id: UUID
    candidate_id: UUID
    facet: str
    worker_role: str = Field(min_length=1, max_length=100)
    objective: str = Field(min_length=1, max_length=1000)
    priority: int = Field(default=1, ge=1)
    originating_round: int = Field(ge=0)


class ResearchWorker(ABC):
    role = "worker"

    @abstractmethod
    def execute(self, task: FollowUpTask, environment: "ResearchEnvironment") -> None:
        """Perform research and mutate authoritative evidence state."""


class ReviewRiskWorker(ResearchWorker):
    role = "review-risk"

    def execute(self, task: FollowUpTask, environment: "ResearchEnvironment") -> None:
        environment.add_evidence(task.candidate_id, task.facet, "negative review/return signal")


class MarketCompetitorWorker(ResearchWorker):
    role = "market-competitor"

    def execute(self, task: FollowUpTask, environment: "ResearchEnvironment") -> None:
        environment.add_evidence(task.candidate_id, task.facet, "competitive pressure signal")


class ProductWorker(ResearchWorker):
    role = "product"

    def execute(self, task: FollowUpTask, environment: "ResearchEnvironment") -> None:
        environment.add_evidence(task.candidate_id, task.facet, "product specification signal")


class WorkerRegistry:
    def __init__(self, workers: list[ResearchWorker] | None = None) -> None:
        self._workers = {worker.role: worker for worker in (workers or default_workers())}

    def dispatch(self, task: FollowUpTask, environment: "ResearchEnvironment") -> str:
        worker = self._workers.get(task.worker_role)
        if worker is None:
            raise ValueError(f"unknown worker role: {task.worker_role}")
        worker.execute(task, environment)
        return worker.role


def default_workers() -> list[ResearchWorker]:
    return [
        ReviewRiskWorker(),
        MarketCompetitorWorker(),
        ProductWorker(),
    ]


class ResearchEnvironment(ABC):
    @abstractmethod
    def candidates(self) -> list[dict[str, Any]]:
        """Return current candidates."""

    @abstractmethod
    def evidence(self, candidate_id: UUID) -> dict[str, list[str]]:
        """Return evidence facets for a candidate."""

    @abstractmethod
    def add_evidence(self, candidate_id: UUID, facet: str, observation: str) -> None:
        """Append new evidence to authoritative state."""
