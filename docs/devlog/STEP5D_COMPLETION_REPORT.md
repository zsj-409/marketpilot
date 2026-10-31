# MarketPilot Step 5D Completion Report

## Final Commit

See repository commit after this report.

## Engineering Status

```text
ENGINEERING COMPLETENESS: READY
RESEARCH PERFORMANCE STATUS: NOT YET DEMONSTRATED
```

## Live Experiment

```text
provider: openai-compatible (DashScope)
model: qwen-plus
new trajectories: 16 policy-diverse branches
LLM calls: 16
input tokens: ~91,507
output tokens: ~19,995
total tokens: ~111,502
client wall latency: recorded per branch
```

## Baseline

Historical Step 5B static IID N=4 rollouts were reused as the matched baseline.

## Non-floor Results

```text
fitness-hard:
  static IID N=4 oracle regret: 0.0782
  policy-diverse N=4 regret: 0.0782
  frontier change: none

kitchen-medium:
  static IID N=4 oracle regret: 0.055
  policy-diverse N=4 regret: 0.055
  frontier change: none
```

## Floor Controls

```text
outdoor-hard: 0.0 regret
beauty-medium: 0.0 regret
```

## Mechanism

```text
evidence overlap: 1.0
research diversity: absent
oracle promotion: ranking order changed but no top-2 frontier change
```

## Gate A

```text
FAIL / NO MECHANISTIC EVIDENCE
```

## Research Conclusion

```text
REAL LLM PERFORMANCE IMPROVEMENT NOT YET DEMONSTRATED
```

## Selector

```text
NOT ALLOWED
```

Reason: candidate frontier did not improve; no selection headroom exists.

## Confirmation DEV

```text
NOT READY
```

## Held-out TEST

```text
UNTOUCHED
```

## Validation

```text
ruff: passed
mypy src: 107 source files, no issues
pytest: 94 passed, 1 skipped
doctor: works
showcase: works
secret scan: no API key found
```

## Next Step

The synthetic search layer currently returns the same sources for different policy queries, so branches do not acquire different evidence. The next step is to make the frozen synthetic environment expose query-discriminative, policy-relevant sources before rerunning Gate A.
