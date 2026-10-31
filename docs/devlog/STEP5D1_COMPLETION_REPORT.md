# MarketPilot Step 5D.1 Completion Report

## Goal

Fix the frozen synthetic research environment so query → evidence acquisition becomes real, while keeping it deterministic, replayable, auditable, policy-agnostic, and benchmark-safe.

## What Changed

- Added synthetic environment version `v2`.
- Added a multi-facet frozen source corpus (`sources_v2.jsonl`).
- Added facet-aware deterministic retrieval with no policy input and no hidden-truth access.

## Validation

```text
ruff check: passed
mypy src: 107 source files, no issues
pytest: 96 passed, 1 skipped
v2 retrieval tests: different queries retrieve different evidence facets
```

## Not Changed

- Hidden truth, oracle utility, candidate universe, candidate IDs, top-k semantics, benchmark tasks, evaluator, regret calculation, floor/non-floor classification, policy definitions, held-out TEST.

## Current Research Status

```text
REAL LLM PERFORMANCE IMPROVEMENT NOT YET DEMONSTRATED
```

Step 5D Gate A remains a formal negative result for synthetic-env-v1. The v2 environment is ready for a clean re-run, but no new live experiment was executed in this step.

## Next Step

Point the Step 5D policy-diverse harness at `load_synthetic_providers_v2` and re-run Gate A with the same 16-trajectory budget. Do not train a selector or touch held-out TEST.
