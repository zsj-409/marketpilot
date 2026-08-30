"""In-memory research provenance store."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

from marketpilot.research.models import RetrievalRecord, SourceRecord, SourceSnapshot


class ResearchStore:
    """Collect sources, retrievals, and snapshots for one run."""

    def __init__(self) -> None:
        self._sources: dict[UUID, SourceRecord] = {}
        self._retrievals: dict[UUID, RetrievalRecord] = {}
        self._snapshots: dict[UUID, SourceSnapshot] = {}

    def add_source(self, source: SourceRecord) -> SourceRecord:
        self._sources[source.source_id] = source
        return source

    def add_retrieval(self, retrieval: RetrievalRecord) -> RetrievalRecord:
        self._retrievals[retrieval.retrieval_id] = retrieval
        return retrieval

    def add_snapshot(self, snapshot: SourceSnapshot) -> SourceSnapshot:
        self._snapshots[snapshot.snapshot_id] = snapshot
        return snapshot

    @property
    def sources(self) -> tuple[SourceRecord, ...]:
        return tuple(self._sources.values())

    @property
    def retrievals(self) -> tuple[RetrievalRecord, ...]:
        return tuple(self._retrievals.values())

    @property
    def snapshots(self) -> tuple[SourceSnapshot, ...]:
        return tuple(self._snapshots.values())
