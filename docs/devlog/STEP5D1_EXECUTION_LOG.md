# MarketPilot Step 5D.1 Execution Log

## 2026-08-29T06:00:00Z Phase 0 — Baseline

### Goal

Freeze the Step 5D negative result and verify the repository before changing the synthetic research environment.

### Validation

```text
ruff check: passed
mypy src: no issues in 107 source files
pytest: 96 passed, 1 skipped
```

## 2026-08-29T06:10:00Z Phase 1 — Synthetic Environment v2

### Goal

Make frozen synthetic search query-sensitive without exposing policy names, hidden utility, or oracle information.

### Actual Changes

- Added `sources_v2.jsonl` with eight evidence facets per category:
  broad, constraints, performance, price, reliability, downside, uncertainty, distractor.
- Added `SyntheticSearchProviderV2` with deterministic lexical + facet-keyword retrieval.
- Added `load_synthetic_providers_v2`.
- Added tests proving different decision-relevant queries retrieve different facets.
- Retrieval depends only on query text and the frozen corpus.

### Design Considerations

- The search engine has no policy parameter and no access to latent truth.
- Historical v1 artifacts remain unchanged and labeled `synthetic-env-v1`.

### Next Action

Run the fixed policy-diverse Gate A against the v2 environment once the Step 5D harness is pointed at `load_synthetic_providers_v2`.
