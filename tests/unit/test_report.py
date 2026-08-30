"""Run report tests."""

from pathlib import Path

from marketpilot.reporting.report import build_run_report, render_report_html


def test_report_build_and_render_from_run_dir(tmp_path: Path) -> None:
    import asyncio

    from marketpilot.cli import DEFAULT_GOAL, _build_llm_runtime, _run_demo
    from marketpilot.config import MarketPilotSettings

    settings = MarketPilotSettings(mode="llm", llm_provider="mock", runs_dir=tmp_path)
    agent_registry = _build_llm_runtime(settings)
    run_dir = asyncio.run(
        _run_demo(
            DEFAULT_GOAL,
            tmp_path,
            agent_registry,
            mode="llm",
            provider="mock",
            model="mock-research-model",
        )
    )
    report_path = run_dir / "report.html"
    assert report_path.exists()
    report = build_run_report(run_dir)
    assert report.run_id
    assert report.task_count == 8
    assert report.status == "COMPLETED"
    render_report_html(report, tmp_path / "copy.html")
    assert "MarketPilot Run Report" in (tmp_path / "copy.html").read_text(encoding="utf-8")
