# MarketPilot Step 2 Completion Report

## Completed

Step 2 introduces a provider-neutral LLM runtime on top of the unchanged Step 1 architecture. The deterministic planner, task DAG, shared blackboard, evidence provenance, deterministic evidence verifier, ToolExecutor boundary, trajectory format, and offline test strategy remain intact.

Implemented capabilities:

- typed LLM request, response, message, tool-call, usage, and model-config models
- provider-neutral `LLMClient` contract and client registry
- typed provider errors with sanitized messages
- bounded retry policy with `LLMRetryExhaustedError`
- deterministic scripted mock LLM provider
- one OpenAI chat-completions adapter
- structured-output parsing and Pydantic validation
- LLM-backed market, product, review, competitor, risk, and decision agents
- LLM-driven tool calls routed through the existing `ToolExecutor`
- versioned prompt system with deterministic hashing
- LLM token, latency, cost, failed-call, and retry metrics
- LLM lifecycle trajectory events
- `mock` and `llm` CLI execution modes
- offline tests plus an optional live OpenAI smoke test
- updated architecture documentation and ADR-0004

## Architecture

```text
Research Goal
      ↓
Deterministic Planner
      ↓
Task DAG
      ↓
LLM-backed Research Agents
      ↓
LLM Agent Runtime
      ├── LLM Client
      │     └── Provider Adapter
      └── Tool Executor
            └── Tool Registry → Mock Tools
      ↓
AgentResult
      ↓
ResearchState
      ↓
Evidence / Findings / Candidates / Risks
      ↓
Decision
      ↓
Deterministic Evidence Validation
      ↓
Evaluation
      ↓
trajectory.jsonl / final_state.json / summary.json
```

Dependency direction:

```text
Domain → Agents → LLM abstraction → Provider adapters
```

Provider SDK objects never appear in `domain/`.

## Major Changes

### LLM Runtime

New package `src/marketpilot/llm/` with:

- `models.py`
- `base.py`
- `errors.py`
- `pricing.py`
- `retry.py`
- `registry.py`
- `structured.py`
- `providers/mock.py`
- `providers/openai.py`

### Provider Adapter

`OpenAIChatClient` converts MarketPilot requests to OpenAI chat completions and normalizes responses, usage, tool calls, and errors. The OpenAI SDK is the only new runtime dependency and is isolated at the adapter boundary.

### Prompt System

`src/marketpilot/prompts/` stores six versioned role templates. Each render records `name`, `version`, and a SHA-256 hash in trajectory metadata without storing full prompts.

### Agent Runtime

`LLMAgent` implements a bounded prompt/LLM/tool/parse loop. Role-specific agents define prompt, output schema, and allowed tools. The deterministic `MockEvidenceVerifierAgent` remains authoritative.

### Tool Calling

The LLM never calls Python directly. Normalized `LLMToolCall` objects pass through `ToolExecutor` and `ToolRegistry` to the existing mock tools.

### Structured Output

Malformed JSON, missing fields, invalid enums, and schema violations are converted to `LLMStructuredOutputError` and rejected before `ResearchState` mutation.

### Error / Retry Policy

Retryable failures include timeout, rate limit, and transient provider errors. Authentication, invalid request, and structured-output failures are permanent and re-raise immediately. Retry exhaustion raises `LLMRetryExhaustedError`.

### Trajectory Changes

New event types:

```text
PROMPT_RENDERED
LLM_REQUESTED
LLM_COMPLETED
LLM_FAILED
LLM_RETRIED
STRUCTURED_OUTPUT_VALIDATED
STRUCTURED_OUTPUT_REJECTED
TOOL_REQUESTED_BY_MODEL
```

The existing event envelope, monotonic sequence numbers, unique event IDs, and JSONL output are preserved.

### Metrics

`ExecutionMetrics` and `EvaluationMetrics` now include LLM call count, input/output/total tokens, latency, estimated cost, failed calls, and retry count.

## Tests

Final command results:

```bash
uv sync
```

```text
Resolved 33 packages in 0.88ms
Checked 33 packages in 1ms
```

```bash
uv run ruff format .
```

```text
89 files left unchanged
```

```bash
uv run ruff check .
```

```text
All checks passed!
```

```bash
uv run mypy src
```

```text
Success: no issues found in 53 source files
```

```bash
uv run pytest
```

```text
54 passed, 1 skipped in 0.92s
```

The skipped test is the optional live OpenAI smoke test, which requires `MARKETPILOT_LLM_API_KEY`.

## Demo

Deterministic mock-agent demo:

```bash
uv run marketpilot demo \
  --mode mock \
  --goal "Find promising pet products in the US market"
```

Result:

```text
Run directory: D:\codex\_output\marketpilot\runs\9f0db1d0-fc27-43e5-b150-0cad1d0b5705
status: COMPLETED
```

Deterministic LLM runtime demo:

```bash
uv run marketpilot demo \
  --mode llm \
  --provider mock \
  --goal "Find promising pet products in the US market"
```

Result:

```text
Run directory: D:\codex\_output\marketpilot\runs\7ad7ea30-fc96-4190-b05f-19ce6dcf9d56
status: COMPLETED
evaluation passed: true
decision: WATCH
```

## Generated Artifacts

LLM runtime demo artifacts:

```text
runs/7ad7ea30-fc96-4190-b05f-19ce6dcf9d56/
├── trajectory.jsonl
├── final_state.json
└── summary.json
```

Programmatic validation:

```text
trajectory events: 125
sequence numbers: valid 0..124
event IDs: unique
run IDs: consistent
recommendations: 1
LLM calls: 13
LLM input tokens: 200
LLM output tokens: 280
LLM total tokens: 480
LLM failed calls: 0
LLM retries: 0
LLM estimated cost: 0.0
```

No credential appeared in any generated artifact.

## Repository Changes

Important files added or modified:

```text
pyproject.toml
uv.lock
.env.example
.github/workflows/ci.yml
README.md
docs/architecture.md
docs/agent-contracts.md
docs/tool-contracts.md
docs/evaluation-plan.md
docs/adr/0004-provider-neutral-llm-runtime.md
docs/devlog/STEP2_EXECUTION_LOG.md
src/marketpilot/config.py
src/marketpilot/cli.py
src/marketpilot/llm/
src/marketpilot/prompts/
src/marketpilot/agents/llm.py
src/marketpilot/agents/llm_runtime.py
src/marketpilot/agents/llm_outputs.py
src/marketpilot/agents/base.py
src/marketpilot/orchestration/runner.py
src/marketpilot/domain/enums.py
src/marketpilot/domain/state.py
src/marketpilot/evaluation/schemas.py
src/marketpilot/evaluation/evaluator.py
tests/unit/test_llm_*.py
tests/unit/test_prompts.py
tests/integration/test_llm_demo.py
tests/smoke/test_openai_smoke.py
```

## Known Limitations

- Real web research is still absent; tools are deterministic mocks.
- The OpenAI adapter is not exercised by CI.
- No pricing table is configured by default, so real-provider estimated cost remains `None`.
- LLM agents use a fixed deterministic planner; the model cannot mutate the DAG.
- The decision agent selects a candidate by exact name.

## Technical Debt

- Real provider error mapping covers OpenAI only.
- Prompt templates are intentionally simple and will evolve.
- The live smoke test depends on a user-supplied API key.
- Persistence models do not yet store per-call LLM metrics in a database.

## Step 3 Readiness

The runtime is ready to add real web research tools behind the existing `ToolExecutor` contract. The LLM tool-call loop, structured output, metrics, and trajectory events are already in place and can consume those tools without further orchestration changes.

## Recommended Next Step

Implement Step 3: real web research tools, with one or two read-only providers behind the existing tool protocol, while keeping the deterministic mock path for tests and CI.
