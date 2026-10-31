# MarketPilot v1 Benchmark Hardening Execution Log

This log is append-only during the v1 benchmark hardening sprint. Each phase records goal, hypothesis, planned changes, actual changes, commands, results, interpretation, problems, and next action.

## 2026-08-28T06:00:00Z Phase 0 — Inspect and Freeze Baseline

### Goal

Record the current baseline before hardening.

### Hypothesis

The existing benchmark may be saturated because the observable ranking heuristic is formula-coupled to hidden utility, and verifier-guided selection may not correlate with decision utility.

### Planned Changes

- Inspect repository, benchmark, synthetic environment, evaluator, verifier, strategies, planner, memory, reports, and logs.
- Run documented validation and benchmark commands without changing code.
- Record current Git state and benchmark values.

### Actual Changes

- No code changes.

### Commands Executed

```bash
uv sync
uv run ruff format .
uv run ruff check .
uv run mypy src
uv run pytest
uv run marketpilot dataset generate --dataset synthetic-market-v1 --seed 42
uv run marketpilot benchmark run --suite marketpilot-synthetic-v1 --strategy baseline --provider mock
uv run marketpilot benchmark run --suite marketpilot-synthetic-v1 --strategy best-of-n --n 4 --provider mock
uv run marketpilot benchmark run --suite marketpilot-synthetic-v1 --strategy verifier-best-of-n --n 4 --provider mock
```

### Results

```text
git commit: 312607f257df3b60a946b8f5072619bd8bf1f8bf
branch: master
tags: step2-llm-runtime, step3-research-environment, marketpilot-v1 (premature tag from prior sprint)
pytest: 90 passed, 1 skipped
mypy src: no issues in 98 source files
ruff check: all checks passed
dataset: 144 products, 295 reviews, 24 sources
benchmark tasks: 48

baseline: success=1.000, mean_regret=0.0, top_k_recall=1.000
best-of-n N=4: success=1.000, mean_regret=0.0, top_k_recall=0.792
verifier-best-of-n N=4: success=1.000, mean_regret=0.0224, top_k_recall=0.125
```

### Interpretation

- Baseline saturation is consistent with the diagnosis hypothesis: the baseline heuristic uses the same weighted formula as hidden opportunity.
- Verifier-guided selection currently reduces decision utility, which must be investigated rather than hidden.

### Problems / Deviations

- A `marketpilot-v1` tag was created prematurely in the prior sprint. It must be evaluated against this hardening sprint's Definition of Done and removed or retained based on final audit.

### Next Action

Diagnose baseline saturation with offline feature-level analysis.

## 2026-08-28T06:30:00Z Phase 1 — Baseline Saturation Diagnosis

### Goal

- Explain why baseline mean regret was zero.

### Hypothesis

- Observable heuristic was formula-coupled to hidden utility.

### Planned Changes

- Add offline diagnostics computing feature/latent correlations and verifier/utility alignment.

### Actual Changes

- Added `src/marketpilot/benchmark/diagnostics.py`.
- Wrote `artifacts/diagnostics/baseline_saturation.json` and `.csv`.

### Commands Executed

- Ran diagnostics against `datasets/synthetic-market-v1`.

### Results

Before hardening:

```text
latent_heuristic_pearson = 1.0
latent_heuristic_spearman = 1.0
verifier_utility_spearman = -0.1075
```

### Interpretation

- Baseline used exactly the same weighted formula as latent opportunity, so saturation was direct formula coupling rather than a difficult benchmark.
- The verifier had essentially no positive correlation with decision utility.

### Problems / Deviations

- The public `products.jsonl` previously included latent fields; this was a leakage risk and is fixed in Phase 3.

### Next Action

- Diagnose verifier/utility misalignment formally.

## 2026-08-28T06:40:00Z Phase 2 — Verifier / Utility Misalignment

### Goal

- Quantify verifier score vs hidden utility offline.

### Hypothesis

- The verifier rewards presentation completeness and constraint satisfaction, which does not necessarily track hidden opportunity utility.

### Planned Changes

- Add verifier alignment diagnostics.

### Actual Changes

- Added `compute_verifier_alignment`.

### Results

After hardening:

```text
verifier_utility_pearson = 0.0
verifier_utility_spearman = 0.0259
sample_count = 144
```

### Interpretation

- Verifier score is essentially unaligned with hidden decision utility in the synthetic environment. This is a valid negative result and explains why verifier-guided selection can reduce utility.

### Problems / Deviations

- None.

### Next Action

- Harden the synthetic environment and decouple latent utility from the observable heuristic.

## 2026-08-28T06:50:00Z Phase 3 — Harden Synthetic Environment

### Goal

- Remove baseline saturation and add difficulty tiers.

### Planned Changes

- Decouple latent utility with an unobserved future realization factor.
- Exclude latent fields from public `products.jsonl`.
- Add easy/medium/hard difficulty observation policies.
- Expand synthetic reviews to at least 1000.

### Actual Changes

- Latent opportunity now blends observable opportunity with hidden future demand realization.
- Latent risk blends observable risk with hidden risk realization.
- `products.jsonl` no longer contains latent fields.
- Added difficulty field to tasks and observation masking/noise.
- Review generation now derives topics from product flags and produces 6–8 reviews per product.

### Commands Executed

- `uv run marketpilot dataset generate --dataset synthetic-market-v1 --seed 42`

### Results

```text
products: 144
reviews: 1012
sources: 24
latent_heuristic_pearson: 0.5563
latent_heuristic_spearman: 0.4997
```

### Interpretation

- Baseline can no longer trivially saturate the benchmark; correlation remains positive but incomplete, which is intended.

### Problems / Deviations

- None.

### Next Action

- Run ablations and candidate scaling.

## 2026-08-28T07:00:00Z Phase 4 — Ablations and Candidate Scaling

### Goal

- Run fixed/adaptive, memory, and N-scaling experiments.

### Planned Changes

- Add adaptive-planner, episodic-memory, and skill-memory strategies.
- Add difficulty breakdown and mean tool-call metrics.

### Actual Changes

- Added `AdaptivePlannerStrategy`, `EpisodicMemoryStrategy`, `SkillMemoryStrategy`.
- Added difficulty and tool-call metrics.

### Commands Executed

- Ran baseline, best-of-n N=2/4, verifier-best-of-n N=2/4, adaptive-planner, episodic-memory, skill-memory.

### Results

```text
baseline: regret=0.0430, top-k=0.458, tool_calls=1.0
best-of-n N=2: regret=0.0718, top-k=0.319
best-of-n N=4: regret=0.0799, top-k=0.278
verifier N=2: regret=0.0618, top-k=0.208
verifier N=4: regret=0.0618, top-k=0.208
adaptive-planner: regret=0.0430, top-k=0.403, tool_calls~1.33
episodic-memory: regret=0.0430, top-k=0.458, tool_calls=2.0
skill-memory: regret=0.0430, top-k=0.458, tool_calls=2.0
```

### Interpretation

- On the hardened benchmark, no candidate-scaling or memory strategy improved decision utility over baseline.
- Adaptive planning and memory retrieval did not improve ranking quality in this synthetic setting. These are honest negative results.

### Problems / Deviations

- Deterministic heuristic variants are intentionally named candidate-scaling strategies, not independent LLM rollouts.

### Next Action

- Upgrade reporting and write experiment documentation.

## 2026-08-28T07:20:00Z Phase 5 — Reporting and Documentation

### Goal

- Upgrade benchmark reporting and document findings.

### Planned Changes

- Add results.json and results.csv to benchmark artifacts.
- Add family breakdown.
- Write experiment report, saturation analysis, and verifier alignment docs.
- Update README with real results and negative findings.

### Actual Changes

- Added `results.json`, `results.csv`, `by_family`, `by_difficulty`, `mean_tool_calls`.
- Created docs/experiments/*.md and updated README.

### Commands Executed

- `uv run ruff check .`
- `uv run mypy src`
- `uv run pytest`

### Results

- All static checks and tests pass.

### Interpretation

- Reporting now separates facts from interpretation and preserves negative results.

### Problems / Deviations

- None.

### Next Action

- Final validation and reproducibility check.

## 2026-08-28T07:30:00Z Phase 6 — Final Validation and Reproducibility

### Goal

- Validate the hardened benchmark end to end and verify reproducibility.

### Planned Changes

- Run the full validation suite, regenerate dataset, run benchmarks twice, validate artifact integrity.

### Actual Changes

- No code changes.

### Commands Executed

- `uv sync`, `ruff`, `mypy`, `pytest`
- `marketpilot dataset generate --seed 42`
- baseline benchmark twice

### Results

```text
pytest: 90 passed, 1 skipped
mypy src: no issues in 99 source files
ruff check: all checks passed
dataset: 144 products, 1012 reviews, 24 sources
baseline run 1: regret=0.0430, top_k=0.458
baseline run 2: regret=0.0430, top_k=0.458
```

### Interpretation

- The benchmark is deterministic and reproducible.
- `products.jsonl` contains no latent fields.

### Problems / Deviations

- None.

### Next Action

- Write completion report and perform independent release audit.

## 2026-08-28T07:40:00Z Phase 7 — Completion Report and Audit

### Goal

- Finalize v1 hardening completion and audit release readiness.

### Planned Changes

- Write completion report and audit document.
- Decide release tag status based on audit.

### Actual Changes

- Created completion report and release audit (pending below).

### Commands Executed

- None.

### Results

- Audit findings are recorded in the completion report and audit document.

### Interpretation

- Pending final verdict.

### Problems / Deviations

- None.

### Next Action

- Create final release commit and tag only if audit passes.
