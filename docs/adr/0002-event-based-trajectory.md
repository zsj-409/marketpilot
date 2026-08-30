# ADR-0002: Event-based Trajectory Logging

## Context

Agent debugging, evaluation, and future training require an exact record of what happened, in what order, and with what inputs and outputs.

## Decision

Every meaningful runtime action emits a typed `AgentEvent` with a sequence number, run ID, task ID, actor, event type, input/output summaries and hashes, metadata, duration, and structured error information. Events are written to `trajectory.jsonl`.

## Alternatives

1. Log only final results.
2. Store unstructured chat transcripts.
3. Use provider-specific tracing only.

## Consequences

### Positive

- replay
- debugging
- training data generation
- evaluation
- RL trajectory analysis
- failure analysis

### Negative

- More events must be modeled and maintained.
- Artifacts require validation and retention policy.

## Status

Accepted.
