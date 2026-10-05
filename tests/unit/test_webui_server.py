"""Tests for the webui job manager and FastAPI server."""

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from marketpilot.webui.jobs import JobManager, JobValidationError


@pytest.fixture()
def job_manager(tmp_path: Path) -> JobManager:
    return JobManager(
        jobs_dir=tmp_path / "jobs",
        python_executable=sys.executable,
        project_root=Path(__file__).resolve().parents[2],
    )


def test_submit_rejects_unknown_kind(job_manager: JobManager) -> None:
    with pytest.raises(JobValidationError):
        job_manager.submit("rm-rf", {})


def test_submit_rejects_bad_strategy(job_manager: JobManager) -> None:
    with pytest.raises(JobValidationError):
        job_manager.submit("benchmark", {"strategy": "nuke", "n": 1, "seed": 42})


def test_submit_rejects_short_goal(job_manager: JobManager) -> None:
    with pytest.raises(JobValidationError):
        job_manager.submit("demo", {"goal": "ab", "mode": "mock"})


def test_submit_runs_command_and_records_log(
    job_manager: JobManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    import time

    import marketpilot.webui.jobs as jobs_module

    def fake_run_subprocess(self: JobManager, record: object) -> tuple[int, None]:
        log_path = Path(self._jobs_dir) / f"{record.job_id}.log"  # type: ignore[attr-defined]
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("fake output\n", encoding="utf-8")
        return 0, None

    monkeypatch.setattr(jobs_module.JobManager, "_run_subprocess", fake_run_subprocess)
    record = job_manager.submit("demo", {"goal": "Find promising pet products", "mode": "mock"})
    # The command should target the CLI entry point.
    assert "marketpilot.cli" in record.command
    assert record.command[record.command.index("--mode") + 1] == "mock"

    current = job_manager.get(record.job_id)
    deadline = 100
    for _ in range(deadline):
        current = job_manager.get(record.job_id)
        assert current is not None
        if current.status in {"SUCCEEDED", "FAILED"}:
            break
        time.sleep(0.05)
    assert current is not None
    assert current.status == "SUCCEEDED"
    assert current.return_code == 0
    assert "fake output" in job_manager.log_tail(record.job_id)


def test_job_manager_marks_interrupted_jobs_failed(tmp_path: Path) -> None:
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()
    record = {
        "job_id": "20260101000000-abcd1234",
        "kind": "demo",
        "args": {},
        "status": "RUNNING",
        "command": ["python"],
        "created_at": "2026-01-01T00:00:00Z",
        "started_at": None,
        "finished_at": None,
        "return_code": None,
        "log_path": str(jobs_dir / "x.log"),
        "error": None,
    }
    (jobs_dir / f"{record['job_id']}.json").write_text(json.dumps(record), encoding="utf-8")
    manager = JobManager(jobs_dir=jobs_dir, python_executable=sys.executable, project_root=tmp_path)
    loaded = manager.get(record["job_id"])
    assert loaded is not None
    assert loaded.status == "FAILED"
    assert loaded.error is not None


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "runs").mkdir()
    (tmp_path / "benchmark_runs").mkdir()
    (tmp_path / "datasets").mkdir()
    # Point PROJECT_ROOT-derived jobs dir away from the real repo in tests.
    import marketpilot.webui.server as server_module

    monkeypatch.setattr(server_module, "PROJECT_ROOT", tmp_path)
    return TestClient(server_module.create_app())


def test_api_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_api_runs_empty(client: TestClient) -> None:
    assert client.get("/api/runs").json() == []
    assert client.get("/api/experiments").json() == []


def test_api_run_detail_404(client: TestClient) -> None:
    response = client.get("/api/runs/00000000-0000-5000-8000-000000000009")
    assert response.status_code == 404
    response = client.get("/api/runs/not-a-uuid")
    assert response.status_code == 404


def test_api_job_validation(client: TestClient) -> None:
    response = client.post("/api/jobs/benchmark", json={"strategy": "bogus"})
    assert response.status_code == 422
    response = client.post("/api/jobs/demo", json={"goal": "hi"})
    assert response.status_code == 422


def test_api_environment_missing_dataset(client: TestClient) -> None:
    response = client.get("/api/environment")
    assert response.status_code == 404


def test_api_environment_products_missing(client: TestClient) -> None:
    response = client.get("/api/environment/products")
    assert response.status_code == 404


def test_api_jobs_roundtrip(client: TestClient) -> None:
    response = client.post(
        "/api/jobs/dataset", json={"seed": 7}
    )
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    detail = client.get(f"/api/jobs/{job_id}")
    assert detail.status_code == 200
    log = client.get(f"/api/jobs/{job_id}/log")
    assert log.status_code == 200
    assert "log" in log.json()
