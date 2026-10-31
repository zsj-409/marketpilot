# MarketPilot Step 5D.2 Completion Report

## Environment

```text
synthetic-env-v2
sources_v2.jsonl count: 64
sources_sha256: dd9ea22311409b00343ddbbf21718688c25cc7680cac0152552aca5d26a8a632
retrieval_sha256: 7f3be5178178fb7d313d527d2717680928a420877e3b253e141fede18bd44921
latent leakage: none
```

## Live Experiment

```text
arm: policy-diverse only (16 trajectories)
provider: openai-compatible (DashScope)
model: qwen-plus
temperature: 0.7
LLM calls: 16
total tokens: ~96,150
client wall latency: recorded per branch
```

## Gate A1

```text
PASS
```

Different policies now produce different evidence: `evidence_overlap` is approximately 0.41–0.43 instead of 1.0.

## Gate A2

```text
FAIL
```

No non-floor task showed a top-2 frontier improvement.

## Research Conclusion

```text
GENERATION-DEV MECHANISM IMPROVEMENT DEMONSTRATED
FRONTIER IMPROVEMENT NOT YET DEMONSTRATED
```

The v2 environment fixed the query → evidence acquisition coupling. Candidate promotion remains unsolved.

## Preserved Historical Result

Step 5D synthetic-env-v1 negative result is unchanged.

## Selector / Confirmation DEV / TEST

```text
selector: NOT ALLOWED
confirmation dev: NOT READY
held-out TEST: UNTOUCHED
```

## Next Step

Investigate why better-ranked oracle candidates still do not enter the top-2 pool: likely a candidate-promotion / ranking-pressure problem, not an evidence-acquisition problem.
