# MarketPilot v1 Experiment Report

## Research Questions

1. Why did baseline saturate the original benchmark?
2. Does verifier score predict hidden decision utility?
3. How does the hardened benchmark change strategy results?
4. Do adaptive planning and memory improve decision quality?
5. How does candidate scaling change quality and cost?

## Experimental Setup

- Synthetic market: 144 products, 8 categories, 1012 reviews, 24 sources.
- Benchmark: 48 tasks, 6 families, easy/medium/hard difficulty.
- Strategies: baseline, best-of-n, verifier-best-of-n, adaptive-planner, episodic-memory, skill-memory.
- Hidden latent opportunity and risk scores are only read by offline evaluators.

## Evaluation Metrics

- Regret: best available latent opportunity minus selected latent opportunity.
- Top-k recall: overlap between selected top candidates and hidden top-k.
- Constraint satisfaction and verifier score.
- Tool calls as a deterministic cost proxy.

## Main Results

| Strategy | Regret | Top-k recall | Tool calls |
| --- | --- | --- | --- |
| Baseline | 0.0430 | 0.458 | 1.0 |
| Best-of-N N=2 | 0.0718 | 0.319 | 2.0 |
| Best-of-N N=4 | 0.0799 | 0.278 | 4.0 |
| Verifier N=2 | 0.0618 | 0.208 | 2.0 |
| Verifier N=4 | 0.0618 | 0.208 | 4.0 |
| Adaptive planner | 0.0430 | 0.403 | ~1.33 |
| Episodic memory | 0.0430 | 0.458 | 2.0 |
| Skill memory | 0.0430 | 0.458 | 2.0 |

All results are synthetic-environment decision quality, not real market performance.

## Findings

1. Baseline saturation was caused by formula coupling, now corrected.
2. The verifier score is essentially unaligned with hidden decision utility.
3. On the hardened benchmark, no tested strategy beat baseline decision quality.
4. Adaptive planning and memory retrieval did not improve ranking quality, at extra tool-call cost.
5. Candidate scaling and verifier selection currently reduce utility, showing that more computation does not automatically improve product selection.

## Limitations

- Deterministic heuristic variants are candidate-scaling strategies, not independent LLM rollouts.
- The synthetic environment is a model, not empirical e-commerce data.
- Quality-cost tradeoffs are measured with a deterministic tool-call proxy.

## Conclusions

MarketPilot v1 now provides a reproducible experimental environment, a hardened benchmark, and honest negative results. The most important engineering finding is that process verification and decision utility are distinct objectives.

## Next Research Directions

- Independent LLM rollouts with real sampling.
- Utility-supervised verifier learning.
- Human evaluation of selected candidates.
