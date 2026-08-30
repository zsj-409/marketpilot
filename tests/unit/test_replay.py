"""Replay store tests."""

from pathlib import Path

import pytest

from marketpilot.research.errors import ReplayMissError
from marketpilot.research.replay import ReplayStore


def test_record_lookup_and_miss(tmp_path: Path) -> None:
    store = ReplayStore()
    key = ReplayStore.key(["web_search", "pet products"])
    store.record(key, {"output": {"summary": "ok"}})
    assert store.lookup(key)["output"]["summary"] == "ok"
    with pytest.raises(ReplayMissError):
        store.lookup("missing")


def test_roundtrip_file(tmp_path: Path) -> None:
    store = ReplayStore()
    key = ReplayStore.key(["fetch_page", "https://example.com"])
    store.record(key, {"output": {"summary": "page"}})
    path = tmp_path / "replay.jsonl"
    store.write(path)
    loaded = ReplayStore()
    loaded.load(path)
    assert loaded.lookup(key)["output"]["summary"] == "page"


def test_committed_recorded_fixture_loads() -> None:
    fixture = Path(__file__).parent.parent / "fixtures" / "replay.jsonl"
    store = ReplayStore()
    store.load(fixture)
    search_key = ReplayStore.key(["web_search", "pet supplies market demand US"])
    fetch_key = ReplayStore.key(["fetch_page", "https://example.com/pet-feeders"])
    assert store.lookup(search_key)["output"]["summary"] == "search returned 1 results"
    assert store.lookup(fetch_key)["output"]["summary"] == "Pet feeder demand"
