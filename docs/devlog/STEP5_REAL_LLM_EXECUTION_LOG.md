# MarketPilot Step 5 Real LLM Execution Log

## 2026-08-29T00:00:00Z Phase 0 — Credential Availability Check

### Goal

Determine whether a real LLM provider can be exercised.

### Result

```text
MARKETPILOT_LLM_API_KEY: absent
MARKETPILOT_LLM_BASE_URL: absent
OPENAI_API_KEY: absent
MARKETPILOT_SEARCH_API_KEY: absent
```

### Interpretation

No live provider credentials are configured in this environment. Real LLM experiments cannot be executed truthfully.

## 2026-08-29T00:10:00Z Phase 1 — Configurable Provider and Budget

### Goal

Prepare the real-LLM path without hard-coding credentials.

### Actual Changes

- Added `llm_base_url`, `llm_max_calls_per_task`, `llm_max_rollout_count`, and `llm_total_call_limit` configuration.
- Added `base_url` to `LLMModelConfig` and the OpenAI adapter.
- Added `LLMBudgetGuard` for call and output-token limits.
- Added `marketpilot llm smoke`.

### Validation

```text
uv run ruff check .: all checks passed
uv run mypy src: no issues in 100 source files
uv run marketpilot llm smoke: LIVE LLM NOT EXECUTED: OpenAI API key is not configured
```

## 2026-08-29T00:20:00Z Phase 2-9 — Live Experiment Status

### Status

```text
Phase 2 structured output: NOT EXECUTED (no key)
Phase 3 real tool call: NOT EXECUTED (no key)
Phase 4 multi-turn agent: NOT EXECUTED (no key)
Phase 5 true LLM rollouts: NOT EXECUTED (no key)
Phase 6 oracle headroom: analysis-only code exists; no live rollouts
Phase 7 utility selector: NOT EXECUTED (no key)
Phase 8 held-out benchmark: NOT EXECUTED (no key)
Phase 9 API ablation: NOT EXECUTED (no key)
```

## Final Verdict

```text
REAL LLM PERFORMANCE IMPROVEMENT NOT YET DEMONSTRATED
```

## 2026-08-29T01:00:00Z Live Credential Provided

### Goal

- Re-run live experiments with the provided Alibaba Cloud Bailian OpenAI-compatible endpoint.

### Configuration Used

```text
provider: openai-compatible (DashScope)
base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
model: qwen-plus
```

No key is written to source, tests, artifacts, logs, or Git history.

### Phase 1 — Provider Smoke

```text
provider=openai
model=qwen-plus
response_id=chatcmpl-096b67c4-f7a0-9dc7-8f81-9b7112b7602f
input_tokens=15
output_tokens=1
latency_ms=0
```

PASS: an actual provider response was received.

### Phase 3 — Real Tool Call

A real research task produced `finish_reason=TOOL_CALLS` and multiple `web_search` / `fetch_page` calls through ToolExecutor. PASS.

### Phase 4 — Multi-Turn Agent

One full Pet Supplies task completed with `COMPLETED`, 20 evidence items, 7 findings, 1 recommendation, and a candidate set.

### Phase 5-9 Status

Full N=1/2/4 rollouts, oracle headroom, utility selector comparison, held-out benchmark, and API ablation are NOT YET COMPLETED. The live path is operational, but the full experiment matrix remains to be run.

## Final Verdict

```text
REAL LLM PERFORMANCE IMPROVEMENT NOT YET DEMONSTRATED
```

## 2026-08-29T02:00:00Z Step 5B Minimal DEV Pilot

### Goal

- Test true LLM candidate ranking with N=1/2/4 on one frozen easy task.

### Configuration

- qwen-plus, temperature 0.7, frozen synthetic environment, Pet Supplies / easy.

### Results

```text
N=1: first_regret=0.0, oracle_regret=0.0, unique_candidates=1, input_tokens=5239
N=2: first_regret=0.0, oracle_regret=0.0, unique_candidates=1, input_tokens=10478
N=4: first_regret=0.0, oracle_regret=0.0, unique_candidates=1, input_tokens=20956
```

### Interpretation

- The LLM consistently selected the same top candidate on this easy task; the candidate pool showed no diversity because only the first ranked candidate was pooled.
- This pilot is insufficient for a performance conclusion. It confirms the LLM ranking path works but does not measure scaling benefit or selector quality.

### Problems / Deviations

- The full DEV pilot and held-out TEST matrix were not completed in this pass.
- No final performance claim is made.

### Next Action

- Run the full 8-12 task DEV pilot and untouched TEST split with proper top-k pooling before drawing conclusions.

## 2026-08-29T03:00:00Z DEV Candidate-Headroom Gate

### Goal

- Finish a low-cost DEV gate with four tasks and four independent LLM rollouts per task.

### Configuration

```text
model: qwen-plus
base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
temperature: 0.7
top_k_per_rollout: 2
max_rollouts: 4
rollout budget used: 16
```

### Results

```text
outdoor-hard: n1_first_regret=0.0, n4_oracle_regret=0.0, oracle_gain=0.0, unique_top1=1, pool_size=2, disagreement=0.75
beauty-medium: n1_first_regret=0.0, n4_oracle_regret=0.0, oracle_gain=0.0, unique_top1=2, pool_size=4, disagreement=0.50
fitness-hard: n1_first_regret=0.1473, n1_oracle=0.0782, n4_oracle=0.0782, oracle_gain=0.0, unique_top1=2, pool_size=3, disagreement=0.50
kitchen-medium: n1_first_regret=0.055, n1_oracle=0.055, n4_oracle=0.055, oracle_gain=0.0, unique_top1=1, pool_size=2, disagreement=0.75
```

### Interpretation

- Across all four tasks, `oracle_gain_n4_vs_n1 = 0.0`: additional independent rollouts did not add a better candidate to the pool.
- Ranking disagreement is nonzero, but diversity does not translate into better oracle candidates.
- Candidate generation is the bottleneck, not candidate selection.

### Decision

- STOP selector optimization per the Go/No-Go gate.
- Diagnose candidate generation before any UtilityAlignedSelector work.

### Next Action

- Improve research-order, constraint-first, risk-first, and evidence-gap prompting; do not tune a selector against hidden truth.
