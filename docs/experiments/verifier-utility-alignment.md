# Verifier Utility Alignment

## Question

Does the deterministic verifier score correlate with hidden decision utility?

## Method

For every product we computed the verifier total score from agent-safe observations and compared it with hidden latent opportunity offline. The verifier never reads latent utility during inference.

## Result

```text
verifier_utility_pearson = 0.0
verifier_utility_spearman = 0.0259
sample_count = 144
```

## Interpretation

The verifier is essentially unaligned with hidden decision utility in this synthetic environment. It rewards evidence presence, snapshot existence, source diversity, constraint satisfaction, and risk coverage, but these presentation/completeness properties do not automatically identify the highest-utility product.

This explains why verifier-guided selection can reduce final decision quality. This is a valid negative result and is preserved rather than tuned away.

## Implication

Verifier score should be interpreted as process/evidence quality, not decision utility. Future learned verifiers would need explicit utility supervision, which remains out of scope for v1.
