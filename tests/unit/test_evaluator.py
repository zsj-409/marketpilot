"""Evaluator tests."""

from marketpilot.domain.enums import RunStatus, TaskStatus
from marketpilot.evaluation.evaluator import SystemEvaluator
from tests.conftest import add_valid_recommendation, make_state


def test_evaluator_accepts_valid_mock_run(goal, run_id: str) -> None:
    state, task, evidence = make_state(goal, run_id)
    add_valid_recommendation(state, task, evidence)
    state.update_task(task.model_copy(update={"status": TaskStatus.SUCCEEDED}))
    state.status = RunStatus.COMPLETED

    result = SystemEvaluator().evaluate(state)
    assert result.passed
    assert result.metrics.task_success_rate == 1.0
    assert result.metrics.evidence_coverage == 1.0


def test_evaluator_detects_missing_evidence(goal, run_id: str) -> None:
    state, task, evidence = make_state(goal, run_id)
    add_valid_recommendation(state, task, evidence)
    state.status = RunStatus.COMPLETED

    result = SystemEvaluator().evaluate(state)
    assert not result.passed
    assert any(check.name == "all_required_tasks_completed" for check in result.checks)
