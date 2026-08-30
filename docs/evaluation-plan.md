# Evaluation Plan

Step 1 evaluates structural system properties, not real market accuracy.

Step 2 keeps those checks and adds LLM-level observability metrics: call count, input/output/total tokens, latency, estimated cost, failed calls, and retry count.

Step 3 begins evaluating research quality without claiming market ground truth: source counts, unique source counts, duplicate rates, retrieval success, source traceability, and budget compliance.

## Current deterministic checks

- run completed
- all required tasks completed
- recommendation exists
- recommendation references findings
- findings reference evidence
- no missing evidence IDs
- no invalid DAG state
- no unsupported recommendation

## Current metrics

- task success rate
- evidence coverage
- unsupported claim rate
- tool success rate
- tool calls per run
- execution latency
- cost per run
- retry rate
- recommendation confidence
- risk violation rate
- LLM call count
- LLM input/output/total tokens
- LLM latency
- LLM estimated cost
- LLM failed calls
- LLM retry count

## Future metrics

Once real tools and benchmarks exist:

- recommendation precision and recall
- evidence quality
- source diversity
- cost efficiency
- latency by task type
- recovery from injected failures
- verifier precision
- trajectory-level reward

## Future evaluation strategy

1. Build a synthetic product research environment.
2. Define deterministic success criteria per task.
3. Inject tool failures and partial evidence.
4. Compare orchestration strategies.
5. Use trajectories for offline evaluation and dataset generation.
