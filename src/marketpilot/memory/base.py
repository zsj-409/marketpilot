"""Framework-independent memory contracts."""

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from marketpilot.domain.enums import MemoryScope


class MemoryRecord(BaseModel):
    """A normalized memory record."""

    model_config = ConfigDict(frozen=True)

    record_id: UUID = Field(default_factory=uuid4)
    scope: MemoryScope
    run_id: UUID
    key: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=4000)
    tags: frozenset[str] = frozenset()
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MemoryQuery(BaseModel):
    """A typed memory lookup."""

    model_config = ConfigDict(frozen=True)

    scope: MemoryScope
    run_id: UUID | None = None
    key: str | None = Field(default=None, min_length=1, max_length=200)
    tags: frozenset[str] = frozenset()


class MemoryStore(ABC):
    """Provider-neutral memory interface.

    Implementations may use in-process storage, PostgreSQL, pgvector, or another
    retrieval backend. The domain and agents depend only on this contract.
    """

    @abstractmethod
    async def store(self, record: MemoryRecord) -> MemoryRecord:
        """Persist a record and return the stored value."""

    @abstractmethod
    async def retrieve(self, query: MemoryQuery) -> list[MemoryRecord]:
        """Return records matching the query."""

    @abstractmethod
    async def delete(self, record_id: UUID) -> bool:
        """Delete a record by ID and report whether it existed."""
