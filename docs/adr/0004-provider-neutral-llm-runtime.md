# ADR-0004: Provider-Neutral LLM Runtime Boundary

## Context

MarketPilot must eventually support real models, structured outputs, tool calls, retries, usage accounting, and provider replacement. Coupling agents directly to a provider SDK would make tests network-dependent and make provider migration invasive.

## Decision

Introduce `src/marketpilot/llm/` as a provider-neutral boundary. Agents depend on `LLMClient` and normalized models only. Provider SDKs live in `llm/providers/`. Structured output, prompts, retry, and cost accounting are normalized and typed.

## Alternatives

1. Call provider SDKs directly inside agents.
2. Adopt LangChain/LangGraph for LLM orchestration.
3. Add a thin HTTP wrapper with no typed contract.

## Consequences

### Positive

- deterministic offline tests with a fake provider
- provider replacement without changing agent business logic
- typed structured-output and error handling
- consistent trajectory metadata
- CI remains offline

### Negative

- More normalization code at the adapter boundary
- Provider-specific features must be intentionally mapped into the normalized contract

## Status

Accepted.
