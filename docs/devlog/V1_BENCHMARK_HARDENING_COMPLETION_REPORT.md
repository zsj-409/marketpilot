# MarketPilot v1 Benchmark Hardening Completion Report

## Commit and Dataset

```text
base commit before hardening: 312607f257df3b60a946b8f5072619bd8bf1f8bf
dataset version: synthetic-market-v1 / v1
generator version: 1.0.0
seed: 42
products: 144
reviews: 1012
sources: 24
benchmark tasks: 48
difficulty tiers: easy / medium / hard
```

## Validation

```text
uv sync: resolved and checked
ruff format: clean
ruff check: all checks passed
mypy src: no issues in 99 source files
pytest: 90 passed, 1 skipped
```

## Main Benchmark Table

Hardened deterministic synthetic benchmark:

| Strategy | Mean regret | Top-k recall | Mean tool calls |
| --- | --- | --- | --- |
| Baseline | 0.0430 | 0.458 | 1.0 |
| Best-of-N N=2 | 0.0718 | 0.319 | 2.0 |
| Best-of-N N=4 | 0.0799 | 0.278 | 4.0 |
| Verifier-guided N=2 | 0.0618 | 0.208 | 2.0 |
| Verifier-guided N=4 | 0.0618 | 0.208 | 4.0 |
| Adaptive planner | 0.0430 | 0.403 | ~1.33 |
| Episodic memory | 0.0430 | 0.458 | 2.0 |
| Skill memory | 0.0430 | 0.458 | 2.0 |

## Ablations

Planning ablation:

- Fixed baseline: regret 0.0430, top-k 0.458.
- Adaptive planner: regret 0.0430, top-k 0.403, additional tool cost.

Memory ablation:

- No memory: regret 0.0430, top-k 0.458.
- Episodic memory: regret 0.0430, top-k 0.458.
- Skill memory: regret 0.0430, top-k 0.458.

Test-time scaling:

- N=1 baseline regret 0.0430.
- N=2 candidate scaling regret 0.0718.
- N=4 candidate scaling regret 0.0799.

## Verifier Correlation

```text
verifier_utility_pearson = 0.0
verifier_utility_spearman = 0.0259
sample_count = 144
```

The verifier is essentially unaligned with hidden decision utility in this synthetic environment. This is a preserved negative result.

## Baseline Saturation

Original baseline correlated perfectly with hidden utility (`Pearson = 1.0`, `Spearman = 1.0`) because it reused the same weighted formula. After decoupling latent utility with a hidden future-demand realization, correlation fell to `Pearson = 0.5563`, `Spearman = 0.4997`.

## Reproducibility

Running the baseline twice after regenerating the seed-42 dataset produced identical aggregate metrics:

```text
run 1: regret=0.0430, top_k=0.458
run 2: regret=0.0430, top_k=0.458
```

## Live Validation Status

```text
LIVE VALIDATION NOT EXECUTED
```

No OpenAI, Tavily, or other live credentials were configured.

## Known Limitations

- Candidate-scaling experiments use deterministic heuristic variants, not independent LLM rollouts.
- Synthetic results do not describe real market performance.
- Tool calls are a deterministic cost proxy, not real latency or monetary cost.

## Technical Debt

- No utility-supervised learned verifier.
- No independent LLM sampling path.
- No human evaluation.
- PostgreSQL runtime integration remains optional and unexercised locally.

## Release Decision

The independent release audit is recorded in `docs/devlog/V1_RELEASE_AUDIT.md`.
