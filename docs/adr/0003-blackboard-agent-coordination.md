# ADR-0003: Blackboard Coordination Instead of Free Agent Chat

## Context

Multi-agent systems often coordinate through unstructured conversation. This can produce hidden state, redundant token usage, ambiguous ownership, and difficult debugging.

## Decision

Agents coordinate through:

```text
Task DAG
+ Shared ResearchState
+ Evidence Store
+ Structured Events
```

Agents do not directly message each other as the primary coordination mechanism.

## Alternatives

1. Agent group chat.
2. Direct agent-to-agent calls.
3. Single monolithic agent.

## Consequences

### Positive

- lower communication noise
- explicit state transitions
- better auditability
- deterministic replay
- more reliable coordination
- future training compatibility

### Negative

- Requires disciplined typed contracts.
- Less flexible than free-form discussion.

## Status

Accepted.
