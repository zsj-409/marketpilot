"""Lightweight task DAG with explicit state transitions."""

from collections import deque
from datetime import UTC, datetime
from uuid import UUID

from marketpilot.domain.enums import TaskStatus
from marketpilot.domain.tasks import TaskNode


class TaskDAG:
    """A deterministic in-memory DAG of typed task nodes."""

    def __init__(self, tasks: list[TaskNode]) -> None:
        self._tasks: dict[UUID, TaskNode] = {}
        for task in tasks:
            if task.task_id in self._tasks:
                raise ValueError(f"duplicate task ID: {task.task_id}")
            self._tasks[task.task_id] = task
        self._validate_references()
        self._validate_cycles()
        self.refresh_statuses()

    @property
    def tasks(self) -> tuple[TaskNode, ...]:
        return tuple(self._tasks.values())

    def get(self, task_id: UUID) -> TaskNode:
        try:
            return self._tasks[task_id]
        except KeyError as exc:
            raise KeyError(f"unknown task: {task_id}") from exc

    def _validate_references(self) -> None:
        for task in self._tasks.values():
            for dependency in task.dependencies:
                if dependency not in self._tasks:
                    raise ValueError(
                        f"task {task.task_id} references missing dependency {dependency}"
                    )

    def _validate_cycles(self) -> None:
        pending = {task_id: set(task.dependencies) for task_id, task in self._tasks.items()}
        queue = deque(task_id for task_id, dependencies in pending.items() if not dependencies)
        resolved: set[UUID] = set()
        while queue:
            task_id = queue.popleft()
            resolved.add(task_id)
            for candidate, dependencies in pending.items():
                if task_id in dependencies and candidate not in resolved:
                    dependencies.remove(task_id)
                    if not dependencies:
                        queue.append(candidate)
        if len(resolved) != len(self._tasks):
            unresolved = sorted(str(task_id) for task_id in self._tasks if task_id not in resolved)
            raise ValueError(f"task DAG contains a cycle involving: {unresolved}")

    def refresh_statuses(self) -> None:
        """Propagate ready and blocked states without hidden transitions."""

        changed = True
        while changed:
            changed = False
            for task_id, task in self._tasks.items():
                if task.status not in {TaskStatus.PENDING, TaskStatus.READY, TaskStatus.BLOCKED}:
                    continue
                dependency_statuses = [self._tasks[item].status for item in task.dependencies]
                if all(status is TaskStatus.SUCCEEDED for status in dependency_statuses):
                    if task.status is not TaskStatus.READY:
                        self._tasks[task_id] = task.model_copy(update={"status": TaskStatus.READY})
                        changed = True
                elif (
                    any(
                        status in {TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.BLOCKED}
                        for status in dependency_statuses
                    )
                    and task.status is not TaskStatus.BLOCKED
                ):
                    self._tasks[task_id] = task.model_copy(update={"status": TaskStatus.BLOCKED})
                    changed = True

    def ready_tasks(self) -> list[TaskNode]:
        self.refresh_statuses()
        return sorted(
            (task for task in self._tasks.values() if task.status is TaskStatus.READY),
            key=lambda task: str(task.task_id),
        )

    def mark_running(self, task_id: UUID) -> TaskNode:
        task = self.get(task_id)
        updated = task.model_copy(
            update={
                "status": TaskStatus.RUNNING,
                "attempt_count": task.attempt_count + 1,
                "started_at": task.started_at or datetime.now(UTC),
            }
        )
        self._tasks[task_id] = updated
        return updated

    def mark_succeeded(self, task_id: UUID) -> TaskNode:
        task = self.get(task_id)
        updated = task.model_copy(
            update={
                "status": TaskStatus.SUCCEEDED,
                "completed_at": datetime.now(UTC),
            }
        )
        self._tasks[task_id] = updated
        self.refresh_statuses()
        return updated

    def mark_failed(self, task_id: UUID) -> TaskNode:
        task = self.get(task_id)
        updated = task.model_copy(
            update={
                "status": TaskStatus.FAILED,
                "completed_at": datetime.now(UTC),
            }
        )
        self._tasks[task_id] = updated
        self.refresh_statuses()
        return updated

    def mark_blocked(self, task_id: UUID) -> TaskNode:
        task = self.get(task_id)
        updated = task.model_copy(update={"status": TaskStatus.BLOCKED})
        self._tasks[task_id] = updated
        self.refresh_statuses()
        return updated

    def can_retry(self, task_id: UUID) -> bool:
        task = self.get(task_id)
        return task.status is TaskStatus.FAILED and task.attempt_count < task.max_attempts

    def retry_task(self, task_id: UUID) -> TaskNode:
        if not self.can_retry(task_id):
            raise ValueError(f"task cannot be retried: {task_id}")
        task = self.get(task_id)
        updated = task.model_copy(update={"status": TaskStatus.READY})
        self._tasks[task_id] = updated
        self.refresh_statuses()
        return updated

    def all_succeeded(self) -> bool:
        return bool(self._tasks) and all(
            task.status is TaskStatus.SUCCEEDED for task in self._tasks.values()
        )

    def has_unfinished_tasks(self) -> bool:
        return any(
            task.status
            in {
                TaskStatus.PENDING,
                TaskStatus.READY,
                TaskStatus.RUNNING,
                TaskStatus.BLOCKED,
                TaskStatus.FAILED,
            }
            for task in self._tasks.values()
        )
