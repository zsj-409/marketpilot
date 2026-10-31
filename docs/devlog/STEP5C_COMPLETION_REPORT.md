# MarketPilot Step 5C Completion Report

## Engineering Completeness

- A new user can install with `uv sync`, check the environment with `marketpilot doctor`, and run a zero-credential offline showcase.
- The offline showcase completes an Agent run and emits trajectory, state, source, evaluation, and `report.html`.
- The real LLM path remains optional and credentials remain environment-only.
- README contains only repository-relative paths.

## Research Diagnostics

Zero-API forensic results on the existing 16 rollouts:

```text
rollout_frontier_gap: 0.0 on all four DEV tasks
selection_gap: non-zero only on fitness-hard (0.0691)
observable_universe_gap: fitness-hard 0.0782, kitchen-medium 0.055
```

The globally best candidate was consistently ranked outside the top-2 candidate pool on non-floor tasks. This means candidate generation is the primary bottleneck, not selector quality.

## New Generation Method

Added four explainable generation policies:

- static-ranking (control)
- constraint-first
- evidence-gap-first
- risk-first

These vary what the Agent investigates before ranking, rather than randomly permuting the same candidate list. They are typed, hidden-truth-free, and tested.

## Live DEV Result

No new live API spend was made in this step. The Step 5B negative result remains the current evidence.

## Validation

```text
uv run ruff check .: passed
uv run mypy src: no issues in 106 source files
uv run pytest: 94 passed, 1 skipped
```

## Project Status

```text
ENGINEERING COMPLETENESS: READY
RESEARCH PERFORMANCE STATUS: NOT YET DEMONSTRATED
```

MarketPilot is engineering-complete as a deterministic, reproducible research platform. No Agent research method has yet beaten the deterministic baseline on the synthetic benchmark.

## Next Step

Evaluate the new research-conditioned generation policies on DEV before touching held-out TEST. Do not train a selector, begin memory work, or start RL.
