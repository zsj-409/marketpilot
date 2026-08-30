"""Persistence repositories for benchmark and experiment data."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from marketpilot.persistence.models import (
    BenchmarkRunRow,
    BenchmarkSuiteRow,
    BenchmarkTaskRow,
    ExperimentRow,
)


class BenchmarkRepository:
    """Persist benchmark suites, tasks, and runs."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save_suite(self, name: str, version: str, manifest: dict[str, Any]) -> str:
        existing = self.get_suite(name)
        if existing is not None:
            return existing.suite_id
        suite_id = str(uuid4())
        self._session.add(
            BenchmarkSuiteRow(suite_id=suite_id, name=name, version=version, manifest=manifest)
        )
        return suite_id

    def save_task(self, suite_id: str, task: dict[str, Any]) -> str:
        existing = self._session.execute(
            select(BenchmarkTaskRow).where(
                BenchmarkTaskRow.suite_id == suite_id,
                BenchmarkTaskRow.task_key == str(task["task_key"]),
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing.task_id
        task_id = str(uuid4())
        self._session.add(
            BenchmarkTaskRow(
                task_id=task_id,
                suite_id=suite_id,
                task_key=str(task["task_key"]),
                goal=str(task["goal"]),
                market=str(task["market"]),
                category=str(task["category"]),
                constraints=dict(task.get("constraints", {})),
                environment_id=str(task["environment_id"]),
                allowed_budget=dict(task.get("allowed_budget", {})),
                rubric=dict(task.get("rubric", {})),
                hidden_ground_truth_ref=dict(task.get("hidden_ground_truth_ref", {})),
            )
        )
        return task_id

    def save_run(
        self,
        suite_id: str,
        task_id: str,
        strategy: str,
        model: str,
        provider: str,
        seed: int,
        status: str,
        metrics: dict[str, Any],
    ) -> str:
        run_id = str(uuid4())
        self._session.add(
            BenchmarkRunRow(
                benchmark_run_id=run_id,
                suite_id=suite_id,
                task_id=task_id,
                strategy=strategy,
                model=model,
                provider=provider,
                seed=seed,
                status=status,
                metrics=metrics,
                started_at=datetime.now(UTC),
            )
        )
        return run_id

    def get_suite(self, name: str) -> BenchmarkSuiteRow | None:
        return self._session.execute(
            select(BenchmarkSuiteRow).where(BenchmarkSuiteRow.name == name)
        ).scalar_one_or_none()


class ExperimentRepository:
    """Persist experiment manifests."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, experiment: dict[str, Any]) -> str:
        experiment_id = str(uuid4())
        self._session.add(
            ExperimentRow(
                experiment_id=experiment_id,
                name=str(experiment.get("name", "experiment")),
                git_commit=str(experiment.get("git_commit", "unknown")),
                dataset=str(experiment.get("dataset", "")),
                dataset_version=str(experiment.get("dataset_version", "")),
                generator_version=str(experiment.get("generator_version", "")),
                seed=int(experiment.get("seed", 42)),
                benchmark_suite=str(experiment.get("benchmark_suite", "")),
                strategy=str(experiment.get("strategy", "baseline")),
                model=str(experiment.get("model", "")),
                provider=str(experiment.get("provider", "mock")),
                prompt_versions=dict(experiment.get("prompt_versions", {})),
                research_budget=dict(experiment.get("research_budget", {})),
            )
        )
        return experiment_id


class RunRepository:
    """Small persistence boundary for completed research runs."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def count_runs(self) -> int:
        from marketpilot.persistence.models import ResearchRunRow

        return len(self._session.execute(select(ResearchRunRow)).scalars().all())


class SourceRepository:
    """Future source persistence boundary."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def count_sources(self) -> int:
        from marketpilot.persistence.models import SourceRow

        return len(self._session.execute(select(SourceRow)).scalars().all())
