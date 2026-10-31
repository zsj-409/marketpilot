# MarketPilot Step 5E Completion Report

## Commit

Recorded after validation.

## Observed Facts

- fitness-hard static oracle rank 5; enters top-k at k=5.
- kitchen-medium static oracle rank 9; enters top-k at k=10.
- Evidence overlap across policies is approximately 0.41, so evidence diversity is real.
- Candidate frontier did not improve.

## Diagnostic Inference

- fitness-hard static: shortlist cutoff dominates.
- kitchen-medium: ranking pressure dominates; the oracle candidate has a better observable opportunity score than the rank-2 candidate but is ranked lower.

## Implementation Change

- Added read-only promotion forensics module.
- No algorithm changes.

## Future Hypothesis

Candidate promotion may be limited by the LLM's ranking pressure, not by evidence acquisition. A future experiment should measure whether ranking inputs can be changed to promote candidates that observable scores already favor, without using hidden truth.

## Validation

```text
ruff: passed
mypy src: no issues in 108 source files
pytest: 96 passed, 1 skipped
secret scan: no API key
network use: none
```

## Next Step

Diagnose ranking pressure / candidate promotion. Do not change top-k, add a selector, or touch held-out TEST.
