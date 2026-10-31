# MarketPilot Step 5E Execution Log

## 2026-08-29T08:00:00Z Phase 0 — Freeze

```text
Step 5D.2 baseline: a1f4d18
synthetic-env: v2
sources_v2_sha256: dd9ea22311409b00343ddbbf21718688c25cc7680cac0152552aca5d26a8a632
```

Offline verification before changes:

```text
ruff: passed
mypy src: no issues
pytest: 96 passed, 1 skipped
```

## 2026-08-29T08:10:00Z Phase 1 — Promotion Forensics Layer

Added `evaluation/promotion_forensics.py`. It consumes Step 5D.2 branch records and ground truth, and produces typed promotion forensics with zero API calls.

## 2026-08-29T08:20:00Z Phase 2 — Findings

See `artifacts/step5d2/promotion_forensics.md`.

Primary bottleneck:

- fitness-hard static branch: shortlist cutoff.
- kitchen-medium: ranking pressure; oracle candidate has better observable opportunity than rank-2 but is still ranked ninth.

## Next Action

Stop. Do not implement reweighting, reranking, pooling changes, selector, Confirmation DEV, or held-out TEST.
