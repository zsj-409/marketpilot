# ADR-0001: Framework-independent Agent Core

## Context

MarketPilot will eventually need LLM providers, orchestration frameworks, web tools, memory systems, and evaluation infrastructure. Agent frameworks and provider APIs change frequently. If domain logic directly depends on them, the project becomes difficult to test, replay, and migrate.

## Decision

The core domain, agent contracts, tool contracts, state model, and orchestration runner remain framework-independent. Provider or framework integrations will be added as adapters in later phases.

## Alternatives

1. Build directly on LangGraph.
2. Call an LLM provider SDK inside agents.
3. Use prompt-level orchestration only.

## Consequences

### Positive

- deterministic offline tests
- clearer architecture
- easier provider migration
- portable domain model
- reproducible trajectories

### Negative

- Step 1 requires more explicit contracts.
- Some framework conveniences must be implemented later.

## Status

Accepted.
