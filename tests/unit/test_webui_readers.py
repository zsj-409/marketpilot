"""Tests for webui artifact readers."""

import json
from pathlib import Path

from marketpilot.webui import readers


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def _minimal_final_state(run_id: str) -> dict:
    from marketpilot.cli import DEFAULT_GOAL, _parse_goal

    goal = _parse_goal(DEFAULT_GOAL)
    return {
        "run_id": run_id,
        "goal": goal.model_dump(mode="json"),
        "status": "COMPLETED",
        "tasks": {},
        "evidence": {},
        "findings": {},
        "candidates": {},
        "risk_flags": {},
        "recommendations": {},
        "budget": goal.budget.model_dump(),
        "metrics": {
            "tasks_total": 0,
            "tasks_successful": 0,
            "tasks_failed": 0,
            "tool_calls": 0,
            "tool_failures": 0,
            "evidence_count": 0,
        },
    }


def _trajectory_row(sequence: int, event_type: str, timestamp: str) -> dict:
    return {
        "event_id": f"00000000-0000-5000-8000-{sequence:012d}",
        "sequence_number": sequence,
        "timestamp": timestamp,
        "run_id": "00000000-0000-5000-8000-000000000001",
        "task_id": None,
        "actor": "DAGRunner",
        "event_type": event_type,
        "parent_event_id": None,
        "input_summary": None,
        "input_hash": None,
        "output_summary": None,
        "output_hash": None,
        "metadata": {},
        "duration_ms": 0,
        "error": None,
    }


def test_list_runs_reads_summary_and_selection(tmp_path: Path) -> None:
    final_state = _minimal_final_state("00000000-0000-5000-8000-000000000001")
    run_dir = tmp_path / "00000000-0000-5000-8000-000000000001"
    _write_json(run_dir / "final_state.json", final_state)
    _write_json(
        run_dir / "summary.json",
        {
            "run_id": final_state["run_id"],
            "status": "COMPLETED",
            "market": "US",
            "category": "pet supplies",
            "decision": "WATCH",
            "evaluation_passed": True,
            "task_success_rate": 1.0,
            "evidence_coverage": 1.0,
            "tool_success_rate": 1.0,
            "llm_calls": 2,
            "llm_total_tokens": 100,
            "tool_calls": 5,
            "recommendation": "ok",
            "mode": "mock",
            "research_mode": "mock",
            "llm_provider": "mock",
            "llm_model": "m",
        },
    )
    _write_jsonl(
        run_dir / "trajectory.jsonl",
        [
            _trajectory_row(0, "RUN_STARTED", "2026-01-01T00:00:00Z"),
            _trajectory_row(1, "RUN_COMPLETED", "2026-01-01T00:00:02Z"),
        ],
    )

    selection_dir = tmp_path / "select-finish"
    _write_json(
        selection_dir / "recommendation.json",
        {
            "final_candidate_id": None,
            "final_verdict": "ACCEPT",
            "termination": "FINISH",
            "rounds": [],
            "followup_events": [],
            "research_rounds": 2,
            "initial_candidates": 3,
            "followup_investigations": 1,
            "unresolved_gaps": 0,
        },
    )

    summaries = readers.list_runs(tmp_path)
    assert len(summaries) == 2
    research = next(item for item in summaries if item.kind == "research")
    assert research.status == "COMPLETED"
    assert research.duration_ms == 2000
    assert research.decision == "WATCH"
    selection = next(item for item in summaries if item.kind == "selection")
    assert selection.termination == "FINISH"
    assert selection.research_rounds == 2


def test_load_run_detail_parses_state_and_evaluation(tmp_path: Path) -> None:
    run_id = "00000000-0000-5000-8000-000000000002"
    run_dir = tmp_path / run_id
    final_state = _minimal_final_state(run_id)
    _write_json(run_dir / "final_state.json", final_state)
    _write_json(run_dir / "summary.json", {"run_id": run_id, "status": "COMPLETED"})
    evaluation_payload = {
        "passed": True,
        "checks": [{"name": "run_completed", "passed": True, "details": "ok"}],
        "metrics": {"task_success_rate": 1.0},
    }
    evaluation_event = _trajectory_row(0, "EVALUATION_COMPLETED", "2026-01-01T00:00:01Z")
    evaluation_event["output_summary"] = json.dumps(evaluation_payload)
    _write_jsonl(
        run_dir / "trajectory.jsonl",
        [
            _trajectory_row(0, "RUN_STARTED", "2026-01-01T00:00:00Z"),
            evaluation_event,
        ],
    )
    _write_jsonl(
        run_dir / "sources.jsonl",
        [
            {"source_id": "s1", "url": "https://example.com", "kind": "source"},
            {"snapshot_id": "sn1", "source_id": "s1", "kind": "snapshot"},
            {"retrieval_id": "r1", "source_id": "s1", "kind": "retrieval"},
        ],
    )

    detail = readers.load_run_detail(tmp_path, run_id)
    assert detail.kind == "research"
    assert detail.status == "COMPLETED"
    assert detail.goal.market == "US"
    assert detail.evaluation is not None
    assert detail.evaluation.passed is True
    assert len(detail.evaluation.checks) == 1
    assert len(detail.sources) == 1
    assert len(detail.snapshots) == 1
    assert len(detail.retrievals) == 1


def test_load_run_detail_missing_run(tmp_path: Path) -> None:
    try:
        readers.load_run_detail(tmp_path, "00000000-0000-5000-8000-000000000009")
        raised = False
    except readers.ArtifactNotFoundError:
        raised = True
    assert raised


def test_load_run_detail_rejects_invalid_id(tmp_path: Path) -> None:
    try:
        readers.load_run_detail(tmp_path, "../escape")
        raised = False
    except readers.ArtifactNotFoundError:
        raised = True
    assert raised


def test_experiment_readers(tmp_path: Path) -> None:
    experiment_id = "00000000-0000-5000-8000-000000000003"
    experiment_dir = tmp_path / experiment_id
    manifest = {
        "experiment_id": experiment_id,
        "name": "suite-baseline",
        "git_commit": "0" * 40,
        "dataset": "synthetic-market-v1",
        "dataset_version": "v1",
        "generator_version": "1.0.0",
        "seed": 42,
        "benchmark_suite": "marketpilot-synthetic-v1",
        "strategy": "baseline",
        "model": "synthetic-baseline",
        "provider": "mock",
        "prompt_versions": {},
        "research_budget": {},
        "started_at": "2026-01-01T00:00:00Z",
        "completed_at": "2026-01-01T00:01:00Z",
    }
    _write_json(experiment_dir / "manifest.json", manifest)
    _write_json(experiment_dir / "metrics.json", {"task_count": 48, "mean_regret": 0.05})
    _write_jsonl(
        experiment_dir / "results.jsonl",
        [
            {
                "task_key": "opportunity-discovery-pet-supplies",
                "family": "Opportunity Discovery",
                "difficulty": "easy",
                "category": "pet supplies",
                "strategy": "baseline",
                "status": "COMPLETED",
            }
        ],
    )
    _write_jsonl(experiment_dir / "failures.jsonl", [])

    summaries = readers.list_experiments(tmp_path)
    assert len(summaries) == 1
    assert summaries[0].strategy == "baseline"

    detail = readers.load_experiment_detail(tmp_path, experiment_id)
    assert detail.metrics["task_count"] == 48
    assert len(detail.results) == 1


def test_strategy_table_weighted(tmp_path: Path) -> None:
    def _experiment(experiment_id: str, strategy: str, regret: float, tasks: int) -> dict:
        return {
            "experiment_id": experiment_id,
            "name": f"exp-{experiment_id}",
            "strategy": strategy,
            "model": "m",
            "provider": "mock",
            "seed": 42,
            "dataset": "synthetic-market-v1",
            "benchmark_suite": "suite",
            "git_commit": "",
            "started_at": "2026-01-01T00:00:00Z",
            "completed_at": None,
            "metrics": {"task_count": tasks, "mean_regret": regret},
        }

    from marketpilot.webui.schemas import ExperimentSummary

    items = [
        ExperimentSummary(**_experiment("a", "baseline", 0.04, 48)),
        ExperimentSummary(**_experiment("b", "baseline", 0.06, 48)),
        ExperimentSummary(**_experiment("c", "best-of-n", 0.08, 48)),
    ]
    rows = readers.build_strategy_table(items)
    baseline = next(row for row in rows if row.strategy == "baseline")
    assert baseline.experiment_count == 2
    assert baseline.mean_regret == 0.05
    assert rows[0].strategy == "baseline"
