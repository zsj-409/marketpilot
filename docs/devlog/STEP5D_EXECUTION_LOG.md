# MarketPilot Step 5D Execution Log

## 2026-08-29T05:00:00Z Phase 0 — Pre-registration

### Hypothesis

Under equal trajectory budget, policy-diverse research branches (static, constraint-first, evidence-gap-first, risk-first) expand the candidate utility frontier more than repeated IID static ranking.

### Configuration

```text
model: qwen-plus
base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
temperature: 0.7
tasks: fitness-hard, kitchen-medium, outdoor-hard, beauty-medium
branches: static-ranking, constraint-first, evidence-gap-first, risk-first
branch budget: 1 LLM call each, 3 synthetic search results
primary metric: policy-diverse N=4 frontier regret vs historical static IID N=4
success gate: at least one non-floor frontier improvement
```

## 2026-08-29T05:20:00Z Phase 1 — Live Gate A

### Results

```text
fitness-hard: policy-diverse regret=0.0782, static IID N=4 oracle regret=0.0782, no frontier improvement
kitchen-medium: policy-diverse regret=0.055, static IID N=4 oracle regret=0.055, no frontier improvement
outdoor-hard: regret=0.0 (floor control)
beauty-medium: regret=0.0 (floor control)
evidence_overlap: 1.0 on all tasks
```

### Interpretation

- No non-floor frontier improvement.
- All policy branches retrieved the same synthetic evidence (`evidence_overlap=1.0`), so research behavior did not actually diverge in information acquisition.
- Oracle ranks changed across policies but did not move the global best candidate into the top-2 pool.

### Gate A Verdict

```text
FAIL / NO MECHANISTIC EVIDENCE
```

Selector remains not allowed. Confirmation DEV is not ready. Held-out TEST remains untouched.
