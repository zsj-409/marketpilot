"""Memory contract tests."""

from uuid import uuid4

from marketpilot.domain.enums import MemoryScope
from marketpilot.memory.base import MemoryQuery, MemoryRecord
from marketpilot.memory.in_memory import InMemoryMemoryStore


async def test_store_and_retrieve() -> None:
    store = InMemoryMemoryStore()
    run_id = uuid4()
    record = MemoryRecord(
        scope=MemoryScope.EPISODIC,
        run_id=run_id,
        key="run-summary",
        content="completed",
        tags=frozenset({"pet"}),
    )
    await store.store(record)
    results = await store.retrieve(
        MemoryQuery(scope=MemoryScope.EPISODIC, run_id=run_id, key="run-summary")
    )
    assert results == [record]


async def test_run_isolation() -> None:
    store = InMemoryMemoryStore()
    first_run = uuid4()
    second_run = uuid4()
    await store.store(
        MemoryRecord(
            scope=MemoryScope.EPISODIC,
            run_id=first_run,
            key="run-summary",
            content="first",
        )
    )
    results = await store.retrieve(
        MemoryQuery(scope=MemoryScope.EPISODIC, run_id=second_run, key="run-summary")
    )
    assert results == []
