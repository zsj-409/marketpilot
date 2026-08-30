# Real Ecommerce Validation

MarketPilot was validated on a bounded set of real, predeclared public ecommerce product pages across three distinct domains.

## Summary

See [docs/data/real_validation_summary.json](docs/data/real_validation_summary.json) for the compact machine-readable proof.

## Result

```text
live fetch attempts: 6
successful pages: 6
distinct domains: 3
refetch count: 0
deterministic extraction successes: 6
LLM semantic-analysis successes: 6
replay repeatability runs: 3
replay repeatability passed: true
cross-site decision passed: true
evidence-gap follow-up passed: true
```

Every successful page was fetched exactly once and immediately saved as an immutable local snapshot. All subsequent parsing, semantic analysis, decision, and reporting operated from replay.

## Pipeline

```text
real page → snapshot → deterministic extraction → bounded LLM semantic features
          → candidate + evidence → DecisionModule → Critic → targeted follow-up
```

## Limitations

- Some pages did not expose deterministic price; price remained UNKNOWN rather than hallucinated.
- LLM semantic features are DERIVED, not OBSERVED.
- This is a bounded validation, not a production crawler.
