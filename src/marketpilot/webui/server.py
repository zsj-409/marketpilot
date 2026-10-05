"""FastAPI application serving the MarketPilot web workbench.

The API is read-only over project artifacts plus an allow-listed job
submission endpoint. The SPA frontend is served from ``static/``.
"""

import sys
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from marketpilot.config import MarketPilotSettings
from marketpilot.webui import readers
from marketpilot.webui.jobs import JobManager, JobValidationError
from marketpilot.webui.schemas import OverviewStats

STATIC_DIR = Path(__file__).parent / "static"
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.1.0"
    project_root: str


class JobLogResponse(BaseModel):
    job_id: str
    log: str


class DemoJobRequest(BaseModel):
    goal: str = Field(min_length=3, max_length=500)
    mode: str = "mock"
    research_mode: str = "mock"
    provider: str = "openai"
    model: str = ""


class BenchmarkJobRequest(BaseModel):
    strategy: str = "baseline"
    n: int = Field(default=1, ge=1, le=8)
    seed: int = Field(default=42, ge=0)


class DatasetJobRequest(BaseModel):
    seed: int = Field(default=42, ge=0)


class SelectProductJobRequest(BaseModel):
    goal: str = Field(min_length=3, max_length=500)
    max_rounds: int = Field(default=3, ge=1, le=6)


def create_app(settings: MarketPilotSettings | None = None) -> FastAPI:
    settings = settings or MarketPilotSettings()
    app = FastAPI(
        title="MarketPilot Workbench",
        description="Interactive workbench over MarketPilot runs, benchmarks, and datasets.",
        version="1.1.0",
    )
    job_manager = JobManager(
        jobs_dir=PROJECT_ROOT / "work" / "jobs",
        python_executable=sys.executable,
        project_root=PROJECT_ROOT,
    )

    @app.exception_handler(readers.ArtifactNotFoundError)
    async def _artifact_not_found(
        _request: Request, exc: readers.ArtifactNotFoundError
    ) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.get("/api/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(project_root=str(PROJECT_ROOT))

    @app.get("/api/overview", response_model=OverviewStats)
    async def overview() -> Any:
        return readers.load_overview(
            settings.runs_dir, settings.benchmark_runs_dir, settings.datasets_dir
        )

    @app.get("/api/runs")
    async def runs(kind: str | None = None) -> Any:
        items = readers.list_runs(settings.runs_dir)
        if kind in {"research", "selection"}:
            items = [item for item in items if item.kind == kind]
        return items

    @app.get("/api/runs/{run_id}")
    async def run_detail(run_id: str) -> Any:
        try:
            return readers.load_run_detail(settings.runs_dir, run_id)
        except readers.ArtifactNotFoundError:
            selection = _try_selection(settings.runs_dir, run_id)
            if selection is not None:
                return selection
            raise HTTPException(status_code=404, detail=f"run not found: {run_id}") from None

    @app.get("/api/experiments")
    async def experiments() -> Any:
        return readers.list_experiments(settings.benchmark_runs_dir)

    @app.get("/api/experiments/{experiment_id}")
    async def experiment_detail(experiment_id: str) -> Any:
        try:
            return readers.load_experiment_detail(settings.benchmark_runs_dir, experiment_id)
        except readers.ArtifactNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from None

    @app.get("/api/environment")
    async def environment() -> Any:
        try:
            return readers.load_environment(settings.datasets_dir)
        except readers.ArtifactNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from None

    @app.get("/api/environment/products")
    async def environment_products(
        category: str | None = None,
        sort: str = "opportunity_score",
        limit: Annotated[int, Query(ge=1, le=500)] = 200,
    ) -> Any:
        try:
            return readers.load_environment_products(
                settings.datasets_dir, category=category, sort=sort, limit=limit
            )
        except readers.ArtifactNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from None

    @app.post("/api/jobs/demo")
    async def submit_demo(request: DemoJobRequest) -> Any:
        return _submit(job_manager, "demo", request.model_dump())

    @app.post("/api/jobs/benchmark")
    async def submit_benchmark(request: BenchmarkJobRequest) -> Any:
        return _submit(job_manager, "benchmark", request.model_dump())

    @app.post("/api/jobs/dataset")
    async def submit_dataset(request: DatasetJobRequest) -> Any:
        return _submit(job_manager, "dataset", request.model_dump())

    @app.post("/api/jobs/select-product")
    async def submit_select_product(request: SelectProductJobRequest) -> Any:
        return _submit(job_manager, "select-product", request.model_dump())

    @app.get("/api/jobs")
    async def jobs() -> Any:
        return job_manager.list_jobs()

    @app.get("/api/jobs/{job_id}")
    async def job_detail(job_id: str) -> Any:
        record = job_manager.get(job_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"job not found: {job_id}")
        return record

    @app.get("/api/jobs/{job_id}/log", response_model=JobLogResponse)
    async def job_log(
        job_id: str, tail: Annotated[int, Query(ge=1, le=200_000)] = 40_000
    ) -> JobLogResponse:
        record = job_manager.get(job_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"job not found: {job_id}")
        return JobLogResponse(job_id=job_id, log=job_manager.log_tail(job_id, max_chars=tail))

    if STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    return app


def _try_selection(runs_dir: Path, run_id: str) -> Any:
    try:
        return readers.load_selection_detail(runs_dir, run_id)
    except (readers.ArtifactNotFoundError, ValueError):
        return None


def _submit(job_manager: JobManager, kind: str, args: dict[str, Any]) -> Any:
    try:
        return job_manager.submit(kind, args)
    except JobValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


app = create_app()
