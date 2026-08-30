"""Deterministic in-process memory implementation."""

from uuid import UUID

from marketpilot.domain.enums import MemoryScope
from marketpilot.memory.base import MemoryQuery, MemoryRecord, MemoryStore


class InMemoryMemoryStore(MemoryStore):
    """A deterministic store used for offline tests and demos.

    Working and episodic records are isolated by run ID. Semantic and skill
    records are intentionally shared across runs.
    """

    def __init__(self) -> None:
        self._records: dict[UUID, MemoryRecord] = {}

    async def store(self, record: MemoryRecord) -> MemoryRecord:
        self._records[record.record_id] = record
        return record

    async def retrieve(self, query: MemoryQuery) -> list[MemoryRecord]:
        results: list[MemoryRecord] = []
        for record in self._records.values():
            if record.scope != query.scope:
                continue
            if record.scope in {MemoryScope.WORKING, MemoryScope.EPISODIC} and (
                query.run_id is None or record.run_id != query.run_id
            ):
                continue
            if query.key is not None and record.key != query.key:
                continue
            if query.tags and not query.tags.issubset(record.tags):
                continue
            results.append(record)
        return sorted(results, key=lambda item: (item.created_at, str(item.record_id)))

    async def delete(self, record_id: UUID) -> bool:
        return self._records.pop(record_id, None) is not None
