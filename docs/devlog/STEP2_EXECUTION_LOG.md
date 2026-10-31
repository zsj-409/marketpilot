# MarketPilot Step 2 Execution Log

This log is append-only during Step 2. It records baseline verification, implementation phases, commands, validation, failures, corrections, and final artifact inspection.

## 2026-08-25T07:00:00Z Phase 0 — Baseline Verification

### Goal

Freeze and verify the completed Step 1 architecture before introducing the provider-neutral LLM runtime.

### Planned Changes

- Inspect the repository, existing documentation, source packages, and tests.
- Run the complete Step 1 verification sequence.
- Record Git state, command results, demo status, trajectory count, and artifacts.
- Make no unrelated Step 1 changes during baseline verification.

### Design Considerations

- Step 2 must preserve the deterministic planner, Task DAG, ResearchState, evidence validation, ToolExecutor boundary, and trajectory format.
- The default execution mode must remain deterministic and offline.
- Provider SDKs must be isolated behind adapter boundaries.

### Actual Changes

- No code changes were made during this phase.

### Repository State

```text
branch: master
current commit: none; repository initialized but no commit has been created
git status: all Step 1 files are currently untracked
```

### Commands Executed

```bash
uv sync
uv run ruff format .
uv run ruff check .
uv run mypy src
uv run pytest
uv run marketpilot demo --goal "Find promising pet products in the US market"
```

### Validation

```text
uv sync:
  Resolved 22 packages in 0.90ms
  Checked 22 packages in 0.94ms

ruff format:
  60 files left unchanged

ruff check:
  All checks passed!

mypy src:
  Success: no issues found in 36 source files

pytest:
  23 passed in 0.39s

demo:
  status=COMPLETED
  run_id=3ca6d1c3-12a3-46ee-a5af-937174c0e1dc
  evaluation_passed=true
  task_success_rate=1.0
  evidence_coverage=1.0
  tool_success_rate=1.0
```

### Demo Artifacts

```text
runs/3ca6d1c3-12a3-46ee-a5af-937174c0e1dc/
├── trajectory.jsonl
├── final_state.json
└── summary.json
```

Artifact validation:

```text
trajectory events: 77
sequence numbers: valid 0..76
event IDs: unique
run IDs: consistent
```

### Decisions

- Proceed with Step 2 from a green baseline.
- Keep mock-agent execution as the default CLI mode.
- Add a new LLM package rather than embedding provider concepts in `domain/` or `agents/`.

### Problems / Deviations

- None.

### Next Action

Implement the provider-neutral LLM models, client contract, typed errors, registry, pricing boundary, and retry policy.

## 2026-08-25T07:20:00Z Phase 1 — LLM Domain Boundary

### Goal

- Add provider-neutral LLM models, client contract, typed errors, registry, pricing, retry policy, and structured-output parsing.

### Planned Changes

- Add `src/marketpilot/llm/` with models, base, errors, retry, pricing, registry, structured parsing, and provider packages.

### Design Considerations

- Agent business logic must depend on normalized models only.
- Provider SDK types must never appear in `domain/`.
- Default runtime must remain deterministic and offline.

### Actual Changes

- Added `LLMMessage`, `LLMRequest`, `LLMResponse`, `LLMUsage`, `LLMToolDefinition`, `LLMToolCall`, `LLMStructuredOutputSpec`, `LLMModelConfig`, and `LLMMetrics`.
- Added `LLMClient`, `LLMClientRegistry`, `RetryableLLMClient`, `PricingCalculator`, and typed error classes.
- Added JSON structured-output parsing and validation.

### Commands Executed

- `uv sync`
- `uv run ruff format .`
- `uv run ruff check .`
- `uv run mypy src`
- `uv run pytest`

### Validation

- Ruff and strict Mypy passed after renaming the structured-output `schema` field to `json_schema` to avoid shadowing a Pydantic `BaseModel` member.

### Decisions

- Use normalized models with optional metadata; unknown provider metadata is not required domain state.
- Treat `estimated_cost = None` as unknown instead of inventing a price.

### Problems / Deviations

- Pydantic disallowed a model field named `schema`; renamed to `json_schema`.

### Next Action

- Implement the deterministic mock LLM provider.

## 2026-08-25T07:30:00Z Phase 2 — Deterministic Mock LLM Provider

### Goal

- Provide scripted, reproducible responses for offline tests and the LLM runtime demo.

### Planned Changes

- Add `llm/providers/mock.py` with global-sequence and prompt-scoped scripting.

### Design Considerations

- Scripts must support normal output, tool calls, structured output, malformed output, and provider errors without network access.

### Actual Changes

- Implemented `MockLLMClient` and `build_demo_llm_responses()`.
- Added multi-turn prompt-scoped scripts for every role.

### Commands Executed

- `uv run pytest`

### Validation

- 54 tests passed, 1 smoke test skipped.
- LLM runtime demo completed with `COMPLETED` status.

### Decisions

- Script by prompt name so multi-turn tool loops are deterministic per role.

### Problems / Deviations

- None.

### Next Action

- Add the OpenAI adapter.

## 2026-08-25T07:40:00Z Phase 3 — Real Provider Adapter

### Goal

- Isolate OpenAI SDK calls behind the normalized `LLMClient` contract.

### Planned Changes

- Add `openai` dependency and `llm/providers/openai.py`.

### Design Considerations

- Convert requests, responses, usage, tool calls, and errors at the adapter boundary.
- Sanitize any API key in provider error text.

### Actual Changes

- Added `OpenAIChatClient` with request conversion, tool-call normalization, usage normalization, response-format mapping, and typed error translation.
- Added adapter unit tests using fake SDK-shaped completions.

### Commands Executed

- `uv sync`
- `uv run ruff format .`
- `uv run ruff check .`
- `uv run mypy src`
- `uv run pytest`

### Validation

- All adapter conversion tests pass.
- Provider error sanitization test confirms the key is redacted.

### Decisions

- Use the OpenAI SDK directly at the adapter boundary rather than an HTTP wrapper.
- Retry at the LLM runtime level, not inside the SDK client.

### Problems / Deviations

- OpenAI SDK overloads required explicit keyword call branches for optional `response_format`.

### Next Action

- Add the prompt system.

## 2026-08-25T07:50:00Z Phase 4 — Prompt System

### Goal

- Make prompt engineering an explicit, versioned subsystem.

### Planned Changes

- Add `src/marketpilot/prompts/` with typed specs, deterministic rendering, hashing, and six role templates.

### Design Considerations

- Trajectory metadata must record prompt name, version, and hash without storing full prompts.

### Actual Changes

- Added `PromptSpec`, `RenderedPrompt`, `PromptRegistry`, and default templates.
- Added deterministic rendering tests.

### Commands Executed

- `uv run pytest`

### Validation

- Rendering is deterministic for identical inputs; all six prompts register correctly.

### Decisions

- Use standard-library `string.Template` for deterministic rendering.

### Problems / Deviations

- None.

### Next Action

- Implement the reusable LLM agent runtime.

## 2026-08-25T08:00:00Z Phase 5 — LLM Agent Base Runtime

### Goal

- Implement the shared prompt/LLM/tool/parse loop once.

### Planned Changes

- Add `agents/llm_outputs.py` and `agents/llm_runtime.py`.

### Design Considerations

- Role-specific agents should define prompt, output schema, and tool allowances, not reimplement execution infrastructure.
- Malformed structured output must not mutate `ResearchState`.

### Actual Changes

- Added role output models and `LLMAgent`.
- Added LLM metrics aggregation and trajectory events.

### Commands Executed

- `uv run ruff check .`
- `uv run mypy src`
- `uv run pytest`

### Validation

- Agent runtime tests pass: tool loop, unknown tool, malformed output, provider failure.

### Decisions

- Route tool calls only through `AgentContext.tool_executor`.
- Keep tool loops bounded with `max_model_turns` and `max_tool_calls`.

### Problems / Deviations

- Initial subclasses used untyped `**kwargs`; refactored to abstract properties with explicit typed constructor parameters.

### Next Action

- Implement LLM research worker agents.

## 2026-08-25T08:10:00Z Phase 6 — Research Worker Agents

### Goal

- Add LLM-backed market, product, review, and competitor agents.

### Planned Changes

- Add `agents/llm.py` role implementations and a registry builder.

### Design Considerations

- Keep the deterministic planner and deterministic evidence verifier unchanged.

### Actual Changes

- Added all four research workers plus risk and decision agents, and `build_llm_agent_registry`.

### Commands Executed

- `uv run pytest`

### Validation

- End-to-end LLM runtime demo produced evidence, findings, one candidate, one risk, and one `WATCH` recommendation.

### Decisions

- Research workers collect evidence from tool observations and then produce one evidence-backed finding.

### Problems / Deviations

- None.

### Next Action

- Implement risk and decision agents.

## 2026-08-25T08:15:00Z Phase 7 — Risk and Decision

### Goal

- Add LLM-backed risk and decision agents without weakening structural validation.

### Planned Changes

- Add `LLMRiskAnalysisAgent` and `LLMDecisionAgent`.

### Design Considerations

- Recommendations must continue referencing valid findings, evidence, risks, and scores.

### Actual Changes

- Risk agent creates a `RiskFlag` and finding from tool evidence.
- Decision agent selects a candidate and creates a recommendation referencing all shared state evidence, findings, and risks.

### Commands Executed

- `uv run pytest`

### Validation

- End-to-end evaluation passed; recommendation references remained valid.

### Decisions

- Decision output chooses a candidate by name; unknown candidate names are rejected.

### Problems / Deviations

- None.

### Next Action

- Complete metrics, trajectory, CLI, and configuration.

## 2026-08-25T08:20:00Z Phase 8 — Metrics and Trajectory

### Goal

- Add LLM token, latency, cost, failure, and retry accounting to existing structures.

### Planned Changes

- Extend `ExecutionMetrics`, `EvaluationMetrics`, and trajectory event types.

### Design Considerations

- Do not create a parallel metrics subsystem.

### Actual Changes

- Added LLM metrics to domain state and evaluator output.
- Added `PROMPT_RENDERED`, `LLM_REQUESTED`, `LLM_COMPLETED`, `LLM_FAILED`, `LLM_RETRIED`, `STRUCTURED_OUTPUT_VALIDATED`, `STRUCTURED_OUTPUT_REJECTED`, and `TOOL_REQUESTED_BY_MODEL` event types.

### Commands Executed

- `uv run ruff check .`
- `uv run mypy src`
- `uv run pytest`

### Validation

- LLM runtime demo recorded 125 trajectory events with valid sequence numbers and unique IDs.

### Decisions

- Record prompt hashes and provider/model metadata instead of raw prompts.

### Problems / Deviations

- None.

### Next Action

- Add CLI execution modes.

## 2026-08-25T08:25:00Z Phase 9 — CLI and Configuration

### Goal

- Add `mock` and `llm` execution modes without breaking the original demo command.

### Planned Changes

- Extend settings, `.env.example`, and the `demo` command with `--mode`, `--provider`, and `--model`.

### Design Considerations

- Default mode stays `mock`; real-provider configuration uses environment variables only.

### Actual Changes

- Added mode/provider/model settings and CLI flags.
- Added clean error handling when the OpenAI key is missing.

### Commands Executed

- `uv run marketpilot demo --mode mock ...`
- `uv run marketpilot demo --mode llm --provider mock ...`

### Validation

- Both commands completed successfully.

### Decisions

- Keep standard-library `argparse` and integrate with `pydantic-settings`.

### Problems / Deviations

- None.

### Next Action

- Add failure/retry and full-suite validation.

## 2026-08-25T08:30:00Z Phase 10 — Failure and Retry Validation

### Goal

- Exercise timeout, rate limit, malformed output, bad tool, provider failure, and retry exhaustion.

### Planned Changes

- Add retry, structured-output, mock-provider, adapter, agent-runtime, and security tests.

### Design Considerations

- Unit tests must remain fast; no real sleeps.

### Actual Changes

- Added tests covering retryable/permanent errors, exhaustion, malformed output, invalid tools, unknown tools, provider failure, and secret sanitization.

### Commands Executed

- `uv run pytest`

### Validation

- 54 passed, 1 skipped in 0.90s.

### Decisions

- Permanent failures re-raise without wrapping; retry exhaustion uses `LLMRetryExhaustedError`.

### Problems / Deviations

- Initial retry wrapper wrapped permanent errors; corrected to re-raise original typed errors.

### Next Action

- Run full test suite and offline LLM runtime demo.

## 2026-08-25T08:35:00Z Phase 11 — Full Test Suite

### Goal

- Run formatting, linting, typing, and tests before final verification.

### Planned Changes

- None; validation only.

### Design Considerations

- Failures must be fixed, not suppressed.

### Actual Changes

- Fixed Ruff and Mypy findings.

### Commands Executed

- `uv sync`
- `uv run ruff format .`
- `uv run ruff check .`
- `uv run mypy src`
- `uv run pytest`

### Validation

- Ruff passed.
- Mypy passed for 53 source files.
- pytest: 54 passed, 1 skipped.

### Decisions

- None.

### Problems / Deviations

- None.

### Next Action

- Run the offline LLM runtime demo and inspect artifacts.

## 2026-08-25T08:40:00Z Phase 12 — Offline LLM Runtime Demo

### Goal

- Exercise the real Step 2 LLM code path with the fake provider and mock tools.

### Planned Changes

- Run the CLI in `llm` mode with provider `mock` and inspect all artifacts.

### Design Considerations

- Parse artifacts programmatically instead of trusting the exit code.

### Actual Changes

- Ran the demo; no code changes.

### Commands Executed

- `uv run marketpilot demo --mode llm --provider mock --goal "Find promising pet products in the US market"`

### Validation

- run status: `COMPLETED`
- evaluation passed
- trajectory events: 125
- LLM calls: 13
- input tokens: 200
- output tokens: 280
- total tokens: 480
- failed LLM calls: 0
- retries: 0
- estimated cost: 0.0

### Decisions

- Use this artifact set as authoritative evidence for Step 2 completion.

### Problems / Deviations

- None.

### Next Action

- Update documentation and create the Step 2 completion report.

## 2026-08-25T08:50:00Z Phase 13 — Optional Real LLM Smoke Run

### Goal

- Exercise a live provider only when an API key is available.

### Planned Changes

- Add an optional skipped pytest smoke test.

### Design Considerations

- CI must never depend on a paid API.

### Actual Changes

- Added `tests/smoke/test_openai_smoke.py`, skipped when `MARKETPILOT_LLM_API_KEY` is absent.

### Commands Executed

- `uv run pytest`

### Validation

- The live smoke test was skipped; no API key is configured in this environment.
- Real provider smoke test was **not performed**.

### Decisions

- Keep live-provider verification manual and optional.

### Problems / Deviations

- None.

### Next Action

- Update documentation and produce the completion report.

## 2026-08-25T08:55:00Z Phase 14 — Documentation

### Goal

- Document the Step 2 changes without overselling capability.

### Planned Changes

- Update README, architecture, agent contracts, tool contracts, evaluation plan, and add ADR-0004.

### Design Considerations

- Clearly state that real web research and market intelligence are not yet implemented.

### Actual Changes

- Updated README, architecture, agent contracts, tool contracts, and evaluation plan.
- Added `docs/adr/0004-provider-neutral-llm-runtime.md`.
- Added `docs/devlog/STEP2_COMPLETION_REPORT.md`.

### Commands Executed

- None.

### Validation

- Manual documentation review.

### Decisions

- Describe provider boundary and LLM runtime without claiming real market intelligence.

### Problems / Deviations

- None.

### Next Action

- Run the complete final verification sequence and stop.

## 2026-08-25T09:00:00Z Final Verification — Step 2

### Goal

- Run every required command and inspect artifacts programmatically.

### Planned Changes

- None; verification only.

### Design Considerations

- Do not infer success from exit code alone.

### Actual Changes

- No code changes.

### Commands Executed

- `uv sync`
- `uv run ruff format .`
- `uv run ruff check .`
- `uv run mypy src`
- `uv run pytest`
- `uv run marketpilot demo --mode mock --goal "Find promising pet products in the US market"`
- `uv run marketpilot demo --mode llm --provider mock --goal "Find promising pet products in the US market"`

### Validation

- `uv sync`: resolved and checked 33 packages.
- `ruff format`: 89 files unchanged.
- `ruff check`: all checks passed.
- `mypy src`: no issues in 53 source files.
- `pytest`: 54 passed, 1 skipped in 0.92s.
- Mock demo run: `9f0db1d0-fc27-43e5-b150-0cad1d0b5705`, status `COMPLETED`.
- LLM runtime demo run: `7ad7ea30-fc96-4190-b05f-19ce6dcf9d56`, status `COMPLETED`.
- LLM runtime trajectory: 125 events, valid sequence, unique IDs, consistent run ID.
- Artifacts parsed successfully; no credentials present.

### Decisions

- Mark Step 2 complete.

### Problems / Deviations

- Real OpenAI smoke run was not performed because no API key is configured; this is expected and does not block Step 2.

### Next Action

- Stop; do not begin Step 3 automatically.
