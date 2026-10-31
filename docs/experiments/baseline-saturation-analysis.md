# Baseline Saturation Analysis

## Question

Why did the original baseline achieve `mean regret = 0` and `top-k recall = 1.0`?

## Method

We computed the Pearson and Spearman correlation between the agent-visible heuristic score and the hidden latent opportunity score across all 144 synthetic products.

## Finding

Before hardening:

```text
latent_heuristic_pearson = 1.0
latent_heuristic_spearman = 1.0
```

The baseline strategy used exactly the same weighted formula as latent opportunity:

```text
0.35 * demand + 0.25 * margin + 0.20 * differentiation
- 0.15 * competition - 0.10 * risk
```

This is formula coupling, not a difficult benchmark. The baseline was not discovering hidden value; it was recomputing the hidden scoring rule from observable fields.

## Hardening

Latent utility was changed to include an unobserved future-demand realization:

```text
latent_opportunity =
0.6 * observable_opportunity + 0.4 * future_demand_realization
```

After hardening:

```text
latent_heuristic_pearson = 0.5563
latent_heuristic_spearman = 0.4997
```

The benchmark is no longer trivially saturated, but observable features still carry meaningful signal.

## Conclusion

The original zero-regret result was an artifact of formula coupling. The hardened benchmark produces more informative, non-saturated results.
