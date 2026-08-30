"""Offline Step 3 research environment integration tests."""

import json
from pathlib import Path

from marketpilot.cli import DEFAULT_GOAL, _build_llm_runtime, _build_research_context, _run_demo
from marketpilot.config import MarketPilotSettings
from marketpilot.domain.state import ResearchState
from marketpilot.research.store import ResearchStore


async def test_mock_research_demo_generates_provenance_artifacts(tmp_path: Path) -> None:
    settings = MarketPilotSettings(
        mode="llm",
        llm_provider="mock",
        research_mode="mock",
        runs_dir=tmp_path,
    )
    tool_registry, research_store, budget, replay_store, deduplicator = _build_research_context(
        settings, "mock"
    )
    agent_registry = _build_llm_runtime(
        settings,
        research_mode="mock",
        tool_registry=tool_registry,
    )
    run_dir = await _run_demo(
        DEFAULT_GOAL,
        tmp_path,
        agent_registry,
        mode="llm",
        provider="mock",
        model="mock-research-model",
        tool_registry=tool_registry,
        research_store=research_store,
        budget=budget,
        replay_store=replay_store,
        research_mode="mock",
        deduplicator=deduplicator,
    )
    assert (run_dir / "sources.jsonl").exists()
    assert (run_dir / "report.html").exists()
    assert (run_dir / "replay.jsonl").exists()
    sources = [
        json.loads(line)
        for line in (run_dir / "sources.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert any(item["kind"] == "source" for item in sources)
    assert any(item["kind"] == "retrieval" for item in sources)
    assert any(item["kind"] == "snapshot" for item in sources)

    state = ResearchState.model_validate_json(
        (run_dir / "final_state.json").read_text(encoding="utf-8")
    )
    assert state.status.value == "COMPLETED"
    assert any(evidence.snapshot_id is not None for evidence in state.evidence.values())


async def test_replay_research_demo_reuses_recorded_sources(tmp_path: Path) -> None:
    settings = MarketPilotSettings(
        mode="llm",
        llm_provider="mock",
        research_mode="mock",
        runs_dir=tmp_path,
    )
    tool_registry, research_store, budget, replay_store, deduplicator = _build_research_context(
        settings, "mock"
    )
    assert replay_store is not None
    agent_registry = _build_llm_runtime(
        settings,
        research_mode="mock",
        tool_registry=tool_registry,
    )
    first = await _run_demo(
        DEFAULT_GOAL,
        tmp_path,
        agent_registry,
        mode="llm",
        provider="mock",
        model="mock-research-model",
        tool_registry=tool_registry,
        research_store=research_store,
        budget=budget,
        replay_store=replay_store,
        research_mode="mock",
        deduplicator=deduplicator,
    )
    settings = settings.model_copy(update={"research_mode": "replay", "replay_run": first.name})
    replay_tools, _, budget2, replay_store_loaded, dedup2 = _build_research_context(
        settings, "replay"
    )
    replay_agents = _build_llm_runtime(
        settings,
        research_mode="replay",
        tool_registry=replay_tools,
    )
    second = await _run_demo(
        DEFAULT_GOAL,
        tmp_path,
        replay_agents,
        mode="llm",
        provider="mock",
        model="mock-research-model",
        tool_registry=replay_tools,
        research_store=ResearchStore(),
        budget=budget2,
        replay_store=replay_store_loaded,
        research_mode="replay",
        deduplicator=dedup2,
    )
    state = ResearchState.model_validate_json(
        (second / "final_state.json").read_text(encoding="utf-8")
    )
    assert state.status.value == "COMPLETED"
    assert (second / "sources.jsonl").exists()
