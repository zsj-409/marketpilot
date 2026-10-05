"""Background job execution for the web workbench.

Jobs run MarketPilot CLI commands in isolated subprocesses, capture their
output to log files, and persist job records to disk so history survives
server restarts. Only allow-listed command kinds can be submitted.
"""

import json
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

JOB_STATUSES = ("QUEUED", "RUNNING", "SUCCEEDED", "FAILED")
MAX_LOG_TAIL_CHARS = 40_000
MAX_GOAL_LENGTH = 500
JOB_TIMEOUT_SECONDS = 1800

STRATEGIES = (
    "baseline",
    "best-of-n",
    "verifier-best-of-n",
    "adaptive-planner",
    "episodic-memory",
    "skill-memory",
)


class JobValidationError(Exception):
    """Raised when a job submission has invalid arguments."""


class JobRecord(BaseModel):
    model_config = ConfigDict(frozen=False)

    job_id: str
    kind: str
    args: dict[str, Any] = Field(default_factory=dict)
    status: str = "QUEUED"
    command: list[str] = Field(default_factory=list)
    created_at: str = ""
    started_at: str | None = None
    finished_at: str | None = None
    return_code: int | None = None
    log_path: str = ""
    error: str | None = None


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class JobManager:
    """Runs allow-listed MarketPilot CLI commands as tracked background jobs."""

    def __init__(self, jobs_dir: Path, python_executable: str, project_root: Path) -> None:
        self._jobs_dir = jobs_dir
        self._python = python_executable
        self._project_root = project_root
        self._jobs: dict[str, JobRecord] = {}
        self._lock = threading.Lock()
        self._queue: list[str] = []
        self._drain_lock = threading.Lock()
        self._load_existing()

    # -- public API ---------------------------------------------------------

    def submit(self, kind: str, args: dict[str, Any]) -> JobRecord:
        command = self._build_command(kind, args)
        job_id = f"{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
        record = JobRecord(
            job_id=job_id,
            kind=kind,
            args=dict(args),
            command=command,
            created_at=_now_iso(),
            log_path=str(self._jobs_dir / f"{job_id}.log"),
        )
        with self._lock:
            self._jobs[job_id] = record
            self._queue.append(job_id)
        self._persist(record)
        threading.Thread(target=self._drain, daemon=True).start()
        return record

    def list_jobs(self) -> list[JobRecord]:
        with self._lock:
            records = list(self._jobs.values())
        records.sort(key=lambda item: item.created_at, reverse=True)
        return records

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

    def log_tail(self, job_id: str, max_chars: int = MAX_LOG_TAIL_CHARS) -> str:
        record = self.get(job_id)
        if record is None or not record.log_path:
            return ""
        path = Path(record.log_path)
        if not path.exists():
            return ""
        text = path.read_text(encoding="utf-8", errors="replace")
        return text[-max_chars:]

    # -- command construction -----------------------------------------------

    def _build_command(self, kind: str, args: dict[str, Any]) -> list[str]:
        base = [self._python, "-m", "marketpilot.cli"]
        if kind == "demo":
            goal = self._clean_goal(args.get("goal"))
            mode = str(args.get("mode", "mock"))
            if mode not in {"mock", "llm"}:
                raise JobValidationError("mode must be mock or llm")
            research_mode = str(args.get("research_mode", "mock"))
            if research_mode not in {"mock", "live", "replay"}:
                raise JobValidationError("research_mode must be mock, live, or replay")
            command = [*base, "--goal", goal, "--mode", mode]
            if mode == "llm":
                provider = str(args.get("provider", "openai"))
                command += ["--provider", provider]
                model = str(args.get("model", "")).strip()
                if model:
                    command += ["--model", model]
            command += ["--research-mode", research_mode]
            return command
        if kind == "benchmark":
            strategy = str(args.get("strategy", "baseline"))
            if strategy not in STRATEGIES:
                raise JobValidationError(f"unknown strategy: {strategy}")
            n = self._clean_int(args.get("n"), default=1, lo=1, hi=8, name="n")
            seed = self._clean_int(args.get("seed"), default=42, lo=0, hi=2**31 - 1, name="seed")
            return [
                *base,
                "benchmark",
                "run",
                "--suite",
                "marketpilot-synthetic-v1",
                "--strategy",
                strategy,
                "--provider",
                "mock",
                "--n",
                str(n),
                "--seed",
                str(seed),
            ]
        if kind == "dataset":
            seed = self._clean_int(args.get("seed"), default=42, lo=0, hi=2**31 - 1, name="seed")
            return [
                *base,
                "dataset",
                "generate",
                "--dataset",
                "synthetic-market-v1",
                "--seed",
                str(seed),
            ]
        if kind == "select-product":
            goal = self._clean_goal(args.get("goal"))
            max_rounds = self._clean_int(
                args.get("max_rounds"), default=3, lo=1, hi=6, name="max_rounds"
            )
            return [
                *base,
                "select-product",
                "--goal",
                goal,
                "--mode",
                "mock",
                "--max-rounds",
                str(max_rounds),
            ]
        raise JobValidationError(f"unknown job kind: {kind}")

    def _clean_goal(self, value: Any) -> str:
        goal = str(value or "").strip()
        if len(goal) < 3:
            raise JobValidationError("goal must be at least 3 characters")
        if len(goal) > MAX_GOAL_LENGTH:
            raise JobValidationError(f"goal must be at most {MAX_GOAL_LENGTH} characters")
        return goal

    def _clean_int(self, value: Any, *, default: int, lo: int, hi: int, name: str) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            number = default
        if number < lo or number > hi:
            raise JobValidationError(f"{name} must be between {lo} and {hi}")
        return number

    # -- execution ----------------------------------------------------------

    def _drain(self) -> None:
        # Single drain loop: jobs execute sequentially in submission order.
        with self._drain_lock:
            while True:
                with self._lock:
                    if not self._queue:
                        return
                    job_id = self._queue.pop(0)
                    record = self._jobs.get(job_id)
                if record is not None:
                    self._execute(record)

    def _execute(self, record: JobRecord) -> None:
        record.status = "RUNNING"
        record.started_at = _now_iso()
        self._persist(record)
        code, error = self._run_subprocess(record)
        record.return_code = code
        record.status = "SUCCEEDED" if code == 0 else "FAILED"
        record.finished_at = _now_iso()
        if error:
            record.error = error
        self._persist(record)

    def _run_subprocess(self, record: JobRecord) -> tuple[int, str | None]:
        import subprocess

        log_path = Path(record.log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(f"$ {' '.join(record.command)}\n")
                handle.flush()
                completed = subprocess.run(
                    record.command,
                    cwd=str(self._project_root),
                    stdout=handle,
                    stderr=subprocess.STDOUT,
                    check=False,
                    timeout=JOB_TIMEOUT_SECONDS,
                )
            return completed.returncode, None
        except subprocess.TimeoutExpired:
            return 124, f"job timed out after {JOB_TIMEOUT_SECONDS}s"
        except OSError as exc:
            return 127, f"failed to start process: {exc}"

    # -- persistence --------------------------------------------------------

    def _persist(self, record: JobRecord) -> None:
        self._jobs_dir.mkdir(parents=True, exist_ok=True)
        path = self._jobs_dir / f"{record.job_id}.json"
        path.write_text(
            json.dumps(record.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load_existing(self) -> None:
        if not self._jobs_dir.exists():
            return
        for path in sorted(self._jobs_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                record = JobRecord.model_validate(payload)
            except (json.JSONDecodeError, OSError, ValueError):
                continue
            if record.status in {"QUEUED", "RUNNING"}:
                record.status = "FAILED"
                record.error = "interrupted by server restart"
                record.finished_at = record.finished_at or _now_iso()
                self._persist(record)
            self._jobs[record.job_id] = record
