# MarketPilot Project State

This is the canonical living status document. It is updated after each significant engineering or research milestone.

## What MarketPilot Is

MarketPilot is a reproducible multi-agent product-research platform. It combines a provider-neutral LLM runtime, a read-only research environment, source/evidence provenance, replay, a synthetic market benchmark with hidden ground truth, deterministic verification, and static run/benchmark reports.

## Current Research Question

Can real LLM rollouts, with meaningful research-behavior variation rather than ranking permutation, expand the candidate utility frontier in a frozen synthetic environment?

Synthetic research environment version: `v2`. The v1 corpus was query-insensitive; v2 adds eight evidence facets and query-sensitive deterministic retrieval so different research policies can acquire different evidence.

## Stable Architecture

- Framework-independent typed domain.
- Deterministic Task DAG and shared ResearchState blackboard.
- ToolExecutor as the only tool boundary.
- Provider-neutral LLMClient with OpenAI-compatible adapter.
- Research provider boundary: search, retrieval, source, snapshot.
- Strict replay semantics.
- Event-sourced trajectory JSONL.

## Completed Capabilities

- Offline deterministic demo and showcase.
- Real LLM + frozen synthetic environment execution.
- Synthetic market environment with easy/medium/hard difficulty.
- Hidden latent utility and risk ground truth, evaluator-only.
- 48-task benchmark with business-level decision quality.
- SQLite persistence, Alembic migrations, benchmark/experiment repositories.
- Static `report.html` and `benchmark.html`.
- Trajectory export with typed reward components.

## Experimental Capabilities

- Real LLM candidate ranking (Step 5B).
- Resumable rollout persistence.
- Hypothesis-diverse candidate generation policies (Step 5C, under development).

## Historical Failure Modes

1. Hidden latent utility is evaluator-only.
2. Synthetic data must remain causally coherent.
3. Original baseline/benchmark coupling produced misleading zero regret.
4. Evidence-presentation quality is not decision utility.
5. Deterministic heuristic variants are not independent LLM rollouts.
6. Easy zero-regret tasks are plumbing tests, not scaling evidence.
7. Ranking disagreement is not candidate diversity or frontier improvement.
8. Candidate pools use stable IDs and explicit top-k semantics.
9. N=1/N=2/N=4 use prefix semantics from the same frozen rollout sequence.
10. Extra LLM sampling does not justify selector optimization without candidate headroom.
11. Successful API calls must be persisted and resumable.
12. Provider latency may be absent; measure client wall-clock latency locally.
13. Credentials never enter source, Git, logs, trajectory, reports, or artifacts.
14. Mock/synthetic/replay/live results must be labeled.
15. `marketpilot-v1` is a frozen historical release and must not move.

## Current Benchmark Status

- Hardened synthetic benchmark: 48 tasks, easy/medium/hard.
- Baseline mean regret after hardening: 0.0430, top-k recall 0.458.
- No tested strategy has yet beaten baseline decision quality.

## Current Live-LLM Status

- Provider smoke: PASS.
- Real tool loop: PASS.
- Real multi-turn task: PASS.
- Four-task DEV candidate-headroom gate: `oracle_gain_n4_vs_n1 = 0.0` on every task.

## Next Research Gate

Generation DEV protocol:

```text
Generation DEV → Gate A → freeze method → Confirmation DEV → Gate B → freeze config → held-out TEST
```

Step 5D Gate A verdict: `FAIL / NO MECHANISTIC EVIDENCE`.

Policy-diverse branches did not expand the candidate frontier on non-floor tasks, and `evidence_overlap = 1.0`. The immediate blocker is query-discriminative synthetic evidence: different research policies currently retrieve the same sources.

Step 5D.2 (synthetic-env-v2): Gate A1 PASS (`evidence_overlap` now ~0.41), Gate A2 FAIL (no top-2 frontier promotion). Candidate promotion is now the bottleneck.

Do not train UtilityAlignedSelector until candidate headroom exists. Do not touch held-out TEST. Do not begin RL.

Step 6 closed-loop product selection is complete: DecisionCritic, TerminationController, selective worker dispatch, DecisionModule, and `marketpilot select-product`. Deterministic scenarios A–E pass. Live path is wired but not executed without credentials.
