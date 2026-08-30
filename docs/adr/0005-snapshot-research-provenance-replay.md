# ADR-0005: Snapshot-Based Research Provenance and Replay

## Context

Real web research is non-deterministic: pages change, providers vary, and network calls are expensive. Experiments must compare models, prompts, and strategies against the same environment.

## Decision

Distinguish `Source`, `Retrieval`, and `SourceSnapshot` as separate typed concepts. Evidence traces to an immutable snapshot. Live research records normalized snapshots into a replay store; replay mode strictly reuses them and never falls back to the network.

## Alternatives

1. Re-fetch live pages for every run.
2. Store raw HTTP responses.
3. Use a vector database for semantic caching.

## Consequences

### Positive

- reproducible comparisons
- auditable provenance
- offline CI
- explicit replay miss
- bounded artifacts

### Negative

- Normalization and snapshot lifecycle must be maintained.
- Replay keys must remain deterministic.

## Status

Accepted.
