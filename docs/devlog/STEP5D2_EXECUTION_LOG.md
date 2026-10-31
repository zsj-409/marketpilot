# MarketPilot Step 5D.2 Execution Log

## 2026-08-29T07:00:00Z Phase 0 — Freeze v2

### Frozen Environment

```text
environment_version: v2
source_count: 64
sources_sha256: dd9ea22311409b00343ddbbf21718688c25cc7680cac0152552aca5d26a8a632
retrieval_sha256: 7f3be5178178fb7d313d527d2717680928a420877e3b253e141fede18bd44921
latent_leak_in_sources: false
```

Deterministic Gate E0: four representative queries returned four distinct facets.

## 2026-08-29T07:20:00Z Phase 1 — Policy-Diverse Gate on v2

### Budget

16 policy-diverse trajectories: 4 tasks × 4 policies.

### Results

```text
Gate A1 evidence_overlap:
  fitness-hard 0.4133
  kitchen-medium 0.4110
  outdoor-hard 0.4268
  beauty-medium 0.4137

Gate A2:
  fitness-hard regret 0.0782, pool 4, oracle ranks {static:5, constraint:16, evidence-gap:11, risk:17}
  kitchen-medium regret 0.055, pool 5, oracle ranks {static:9, constraint:11, evidence-gap:8, risk:12}
  floor controls regret 0.0
```

### Verdict

- Gate A1: PASS. Different policies now acquire different evidence.
- Gate A2: FAIL. No oracle candidate was promoted into the top-2 frontier on non-floor tasks.
