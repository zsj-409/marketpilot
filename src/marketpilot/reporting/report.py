"""Build and render a static run report."""

# ruff: noqa: E501

import html
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TaskSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    task_id: str
    task_type: str
    role: str
    status: str
    description: str
    attempt_count: int


class SourceSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    url: str
    canonical_url: str
    domain: str
    title: str | None
    published_at: str | None
    duplicate: bool = False
    snapshot_id: str | None = None


class EvidenceLink(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_id: str
    source_uri: str
    snapshot_id: str | None
    finding_ids: list[str]


class ErrorSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_type: str
    actor: str
    message: str


class RunReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    goal: str
    status: str
    decision: str
    start_time: str | None = None
    end_time: str | None = None
    duration_ms: int = 0
    task_count: int = 0
    source_count: int = 0
    unique_source_count: int = 0
    llm_calls: int = 0
    llm_total_tokens: int = 0
    tool_calls: int = 0
    estimated_cost: float | None = None
    evaluation_passed: bool = False
    tasks: list[TaskSummary] = Field(default_factory=list)
    sources: list[SourceSummary] = Field(default_factory=list)
    evidence: list[EvidenceLink] = Field(default_factory=list)
    errors: list[ErrorSummary] = Field(default_factory=list)


def build_run_report(run_dir: Path) -> RunReport:
    """Build a typed report from run artifacts."""

    trajectory = _read_jsonl(run_dir / "trajectory.jsonl")
    final_state = _read_json(run_dir / "final_state.json")
    summary = _read_json(run_dir / "summary.json")
    sources = _read_jsonl(run_dir / "sources.jsonl")

    tasks = [
        TaskSummary(
            task_id=str(item["task_id"]),
            task_type=item["task_type"],
            role=item["assigned_role"],
            status=item["status"],
            description=item["description"],
            attempt_count=item["attempt_count"],
        )
        for item in final_state.get("tasks", {}).values()
    ]
    source_records = [item for item in sources if item.get("kind") == "source"]
    snapshot_by_source = {
        str(item["source_id"]): str(item["snapshot_id"])
        for item in sources
        if item.get("kind") == "snapshot"
    }
    source_summaries = [
        SourceSummary(
            source_id=str(item["source_id"]),
            url=item["url"],
            canonical_url=item["canonical_url"],
            domain=item["domain"],
            title=item.get("title"),
            published_at=item.get("published_at"),
            snapshot_id=snapshot_by_source.get(str(item["source_id"])),
        )
        for item in source_records
    ]
    evidence = [
        EvidenceLink(
            evidence_id=str(item["evidence_id"]),
            source_uri=item["source_uri"],
            snapshot_id=str(item["snapshot_id"]) if item.get("snapshot_id") else None,
            finding_ids=[],
        )
        for item in final_state.get("evidence", {}).values()
    ]
    for finding in final_state.get("findings", {}).values():
        for evidence_id in finding.get("evidence_ids", []):
            for link in evidence:
                if link.evidence_id == str(evidence_id):
                    link.finding_ids.append(str(finding["finding_id"]))
                    break

    errors = [
        ErrorSummary(
            event_type=item["event_type"],
            actor=item["actor"],
            message=str(item.get("error") or item.get("output_summary") or ""),
        )
        for item in trajectory
        if item["event_type"].endswith("_FAILED") or item.get("error") is not None
    ]

    start_event = next((item for item in trajectory if item["event_type"] == "RUN_STARTED"), None)
    end_event = next(
        (item for item in trajectory if item["event_type"] in {"RUN_COMPLETED", "RUN_FAILED"}),
        None,
    )
    duration_ms = 0
    if start_event and end_event:
        duration_ms = max(
            int(end_event.get("sequence_number", 0)) - int(start_event.get("sequence_number", 0)), 0
        )

    return RunReport(
        run_id=str(final_state["run_id"]),
        goal=final_state["goal"]["objective"],
        status=final_state["status"],
        decision=summary.get("decision", "NONE"),
        start_time=start_event.get("timestamp") if start_event else None,
        end_time=end_event.get("timestamp") if end_event else None,
        duration_ms=duration_ms,
        task_count=len(tasks),
        source_count=len(source_summaries),
        unique_source_count=len({item.source_id for item in source_summaries}),
        llm_calls=summary.get("llm_calls", 0),
        llm_total_tokens=summary.get("llm_total_tokens", 0),
        tool_calls=summary.get("tool_calls", 0),
        estimated_cost=summary.get("llm_estimated_cost"),
        evaluation_passed=bool(summary.get("evaluation_passed", False)),
        tasks=tasks,
        sources=source_summaries,
        evidence=evidence,
        errors=errors,
    )


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return dict(json.load(handle))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return [dict(json.loads(line)) for line in handle if line.strip()]


def render_report_html(report: RunReport, output_path: Path) -> None:
    """Render a self-contained HTML report."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    esc = html.escape
    task_rows = "\n".join(
        f"<tr><td>{esc(t.task_id)}</td><td>{esc(t.task_type)}</td>"
        f"<td>{esc(t.role)}</td><td>{esc(t.status)}</td><td>{esc(t.description)}</td></tr>"
        for t in report.tasks
    )
    source_rows = "\n".join(
        f"<tr><td>{esc(s.source_id)}</td><td>{esc(s.domain)}</td>"
        f"<td>{esc(s.title or '')}</td><td>{esc(s.url)}</td></tr>"
        for s in report.sources
    )
    evidence_rows = "\n".join(
        f"<tr><td>{esc(e.evidence_id)}</td><td>{esc(e.source_uri)}</td>"
        f"<td>{esc(', '.join(e.finding_ids))}</td></tr>"
        for e in report.evidence
    )
    error_rows = "\n".join(
        f"<tr><td>{esc(e.event_type)}</td><td>{esc(e.actor)}</td><td>{esc(e.message)}</td></tr>"
        for e in report.errors
    )
    document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>MarketPilot Run {esc(report.run_id)}</title>
<style>
body{{font-family:system-ui,sans-serif;margin:2rem;color:#1f2933}}
h1,h2{{font-weight:600}}
table{{border-collapse:collapse;width:100%;margin:1rem 0}}
th,td{{border:1px solid #d9e2ec;padding:.45rem;text-align:left;font-size:.9rem}}
th{{background:#f0f4f8}}
.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem}}
.metric{{border:1px solid #d9e2ec;border-radius:.4rem;padding:.8rem}}
.metric .label{{color:#52606d;font-size:.8rem}}
.metric .value{{font-size:1.4rem;font-weight:600}}
</style>
</head>
<body>
<h1>MarketPilot Run Report</h1>
<div class="grid">
<div class="metric"><div class="label">Run ID</div><div class="value">{esc(report.run_id)}</div></div>
<div class="metric"><div class="label">Status</div><div class="value">{esc(report.status)}</div></div>
<div class="metric"><div class="label">Decision</div><div class="value">{esc(report.decision)}</div></div>
<div class="metric"><div class="label">Evaluation</div><div class="value">{"PASS" if report.evaluation_passed else "FAIL"}</div></div>
</div>
<h2>Overview</h2>
<p><strong>Goal:</strong> {esc(report.goal)}</p>
<p>Tasks: {report.task_count} | Sources: {report.source_count} | Unique sources: {report.unique_source_count}</p>
<p>LLM calls: {report.llm_calls} | LLM tokens: {report.llm_total_tokens} | Tool calls: {report.tool_calls}</p>
<h2>Task DAG</h2>
<table><tr><th>Task</th><th>Type</th><th>Agent</th><th>Status</th><th>Description</th></tr>{task_rows}</table>
<h2>Sources</h2>
<table><tr><th>Source</th><th>Domain</th><th>Title</th><th>URL</th></tr>{source_rows}</table>
<h2>Evidence</h2>
<table><tr><th>Evidence</th><th>Source</th><th>Findings</th></tr>{evidence_rows}</table>
<h2>Errors</h2>
<table><tr><th>Event</th><th>Actor</th><th>Message</th></tr>{error_rows}</table>
</body>
</html>
"""
    output_path.write_text(document, encoding="utf-8")
