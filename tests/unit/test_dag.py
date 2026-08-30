"""Task DAG behavior tests."""

from uuid import uuid4

import pytest

from marketpilot.domain.enums import TaskStatus
from marketpilot.orchestration.dag import TaskDAG
from tests.conftest import make_task


def test_dependency_ordering_and_completion_propagation(run_id: str) -> None:
    first = make_task(run_id)
    second = make_task(run_id, dependencies={first.task_id})
    dag = TaskDAG([first, second])

    assert [task.task_id for task in dag.ready_tasks()] == [first.task_id]
    dag.mark_running(first.task_id)
    dag.mark_succeeded(first.task_id)
    assert [task.task_id for task in dag.ready_tasks()] == [second.task_id]


def test_failed_dependency_blocks_dependent(run_id: str) -> None:
    first = make_task(run_id)
    first = first.model_copy(update={"max_attempts": 1})
    second = make_task(run_id, dependencies={first.task_id})
    dag = TaskDAG([first, second])

    dag.mark_running(first.task_id)
    dag.mark_failed(first.task_id)
    assert dag.get(first.task_id).status is TaskStatus.FAILED
    assert dag.get(second.task_id).status is TaskStatus.BLOCKED
    assert not dag.can_retry(first.task_id)


def test_retry_behavior(run_id: str) -> None:
    task = make_task(run_id)
    dag = TaskDAG([task])
    running = dag.mark_running(task.task_id)
    assert running.attempt_count == 1
    dag.mark_failed(task.task_id)
    assert dag.can_retry(task.task_id)
    retried = dag.retry_task(task.task_id)
    assert retried.status is TaskStatus.READY


def test_cycle_is_rejected(run_id: str) -> None:
    first_id = uuid4()
    second_id = uuid4()
    first = make_task(run_id, task_id=first_id, dependencies={second_id})
    second = make_task(run_id, task_id=second_id, dependencies={first_id})
    with pytest.raises(ValueError, match="cycle"):
        TaskDAG([first, second])
