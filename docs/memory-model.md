# Memory Model

MarketPilot separates memory into four conceptual scopes.

## Working memory

The current `ResearchState` for one run:

- goal
- task DAG
- evidence
- findings
- candidates
- risks
- recommendations
- metrics

## Episodic memory

Historical research runs and outcomes:

```text
Previously analyzed:
automatic pet feeder

Observed:
medium-high competition

Decision:
WATCH
```

Episodic records are isolated by `run_id`.

## Semantic memory

Reusable factual, product, and market knowledge derived from evidence.

Examples:

- normalized product attributes
- market definitions
- stable supplier constraints
- verified category relationships

## Skill memory

Reserved for later phases:

- research strategies
- useful search patterns
- known failure recovery procedures

## Memory contract

```python
class MemoryStore(ABC):
    async def store(self, record: MemoryRecord) -> MemoryRecord: ...
    async def retrieve(self, query: MemoryQuery) -> list[MemoryRecord]: ...
    async def delete(self, record_id: UUID) -> bool: ...
```

Step 1 provides `InMemoryMemoryStore`. A future PostgreSQL + pgvector implementation can replace it without changing agent code.
