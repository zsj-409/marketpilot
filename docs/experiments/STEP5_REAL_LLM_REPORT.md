# Step 5 Real LLM Experiment Report

## Status

```text
REAL LLM PERFORMANCE IMPROVEMENT NOT YET DEMONSTRATED
```

## Live Results So Far

- Provider smoke against qwen-plus succeeded.
- Real multi-turn tool calling succeeded.
- One full synthetic Pet Supplies task completed with evidence and a recommendation.

The full independent-rollout N=1/2/4, oracle headroom, utility selector, held-out benchmark, and API ablation still need to be executed before a performance claim can be made.

## DEV Candidate-Headroom Gate

Four medium/hard DEV tasks, four independent qwen-plus rollouts each:

- `oracle_gain_n4_vs_n1 = 0.0` on all four tasks.
- Additional rollouts produced ranking disagreement but no better oracle candidate.
- Candidate generation is the measured bottleneck, not selection.

Per the Go/No-Go gate, selector optimization stops here. The conclusion remains:

```text
REAL LLM PERFORMANCE IMPROVEMENT NOT YET DEMONSTRATED
```

## What Was Implemented

- OpenAI-compatible `base_url` configuration.
- Per-task call and output-token budget guard.
- Rollout-count configuration.
- `marketpilot llm smoke` live validation command.
- Credential-leakage-safe smoke command that reports `LIVE LLM NOT EXECUTED` when no key exists.

## What Was Not Executed

- Provider smoke.
- Structured output validation.
- Real multi-turn tool calling.
- True independent LLM rollouts.
- Held-out LLM benchmark.
- API ablation.

## Reproduce When a Key Is Available

```bash
export MARKETPILOT_LLM_API_KEY=...
export MARKETPILOT_LLM_BASE_URL=...   # optional for OpenAI-compatible endpoints
export MARKETPILOT_LLM_MODEL=gpt-4o-mini
uv run marketpilot llm smoke
```

Then run the benchmark with `--provider openai`.

## Honesty Note

No synthetic, mock, or replay result has been substituted for a live LLM result.
