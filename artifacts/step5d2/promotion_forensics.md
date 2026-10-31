# Candidate Promotion Forensics

## Primary Research Question

Why does query-sensitive evidence acquisition not convert into top-2 candidate promotion?

## Non-floor Findings

### fitness-hard

- static-ranking oracle rank: 5, k_star=5.
- static oracle regret(k): k=1 0.1106, k=2 0.0782, k=5 0.0.
- static rank2_score=0.3721, oracle_score=0.3551, promotion_gap=+0.0170.
- constraint/evidence-gap/risk policies rank oracle 16/11/17.

Interpretation: static ranking has the oracle candidate immediately outside the top-2 cutoff. The shortlist cutoff is dominant for the static branch, while other policies push the oracle candidate much deeper.

### kitchen-medium

- static-ranking oracle rank: 9, k_star=10.
- static oracle regret(k): k=1 0.055, k=4 0.0324, k=10 0.0.
- static rank2_score=0.3789, oracle_score=0.3983, promotion_gap=-0.0194.
- constraint/evidence-gap/risk policies rank oracle 11/8/12.

Interpretation: the oracle candidate has a higher observable opportunity score than the static rank-2 candidate but is still ranked ninth. This indicates ranking/utility-estimation or promotion pressure, not a simple evidence-acquisition gap.

## Bottleneck Classification

- fitness-hard static branch: `SHORTLIST_CUTOFF_DOMINANT`.
- fitness-hard policy branches: `RANKING_PRESSURE_DOMINANT`.
- kitchen-medium: `RANKING_PRESSURE_DOMINANT` / `MIXED`.

## Allowed Conclusion

```text
INFORMATION-ACQUISITION MECHANISM IMPROVEMENT DEMONSTRATED
CANDIDATE-FRONTIER IMPROVEMENT NOT YET DEMONSTRATED
```

## Prohibited Conclusions

- Real-LLM performance improvement demonstrated.
- Candidate promotion already improved.
- Selector is now justified.

## Recommended Next Experiment

Investigate ranking pressure / candidate promotion. Do not change top-k, add a selector, or run held-out TEST.
