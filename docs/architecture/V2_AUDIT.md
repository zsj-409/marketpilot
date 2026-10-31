# MarketPilot V2 Architecture Audit

Status: AUDIT COMPLETE (Phase 0 of the MarketPilot 2.0 plan)
Audit commit: `bf5f8e6` (validation: record three-run replay repeatability)
Audit date: 2026-10-29
Auditor: MarketPilot 2.0 engineering pass (code-level review, not claim-level review)

This document is the first V2 deliverable. It records the existing architecture, module responsibilities, code locations, verified capabilities, technical debt, reusable components, and modules recommended for deletion or consolidation. It was produced by reading every file in `src/marketpilot/`, `tests/`, `docs/`, `pyproject.toml`, and the run/benchmark artifacts, then running the full offline verification sequence.

---

## 1. Executive Summary

MarketPilot v1 is a **deterministic, reproducible, offline-first multi-agent product-research platform**. It is engineering-complete as a v1 portfolio release, with a strict evidence/provenance chain, a provider-neutral LLM boundary, a frozen synthetic market environment with hidden ground truth, a 48-task benchmark, and honest negative results (no strategy beats baseline; verifier score is unaligned with decision utility).

The v1 release exists in two branches of this repository:
- `master` at `bf5f8e6` — the full engineering history (dev logs, experiments, artifacts, tags).
- `public` at `8a804f2` — the published "MarketPilot v1 public release" (all 27 dev logs removed, only `V1_EXPERIMENT_REPORT.md` remains in `docs/experiments/`; `docs/REAL_ECOMMERCE_VALIDATION.md` and `docs/data/real_validation_summary.json` added; `validation/real_ecommerce_validation.example.yaml` added).

`8a804f2` is a subset of `bf5f8e6` plus three publish-only files. The published repository tree is a strict derivative of the master tree. **Both branches are frozen for V2: no historical result, dev log, artifact, or benchmark is to be modified.**

The core V2 strategy on top of this codebase is **incremental layering**: keep the proven `domain/ → agents/ → llm/ → tools/` dependency direction, keep the frozen synthetic environment and 48-task benchmark as the v1 baseline, and add new layers (`input/` normalization, `world/` synthetic v3, `policy/` research controllers, `optimization/` Dream-RSI, `evaluation/` harness extension) without rewriting what already works.

---

## 2. Repository Snapshot (as audited)

| Item | Value |
| --- | --- |
| Git branch | `master` |
| HEAD commit | `bf5f8e6` |
| Python | 3.12.14 (project `.venv`) |
| Runtime deps | pydantic, pydantic-settings, sqlalchemy, alembic, openai, httpx |
| Dev deps | pytest, pytest-asyncio, ruff, mypy |
| Source files | 118 (mypy count) |
| Tests | 102 passed, 1 skipped (optional live OpenAI smoke) |
| CLI | 9 commands: demo, report, dataset, benchmark, showcase, trajectories, llm, doctor, select-product |
| Dataset | `synthetic-market-v1`: 144 products, 1012 reviews, 24 sources (v1), 64 sources (v2 facets), ground truth hidden |
| Benchmark | 48 tasks, 6 families, easy/medium/hard |
| SQLite | `marketpilot.db` with Alembic migration `f3c4ed1987f9_initial_schema` |
| Tags | `marketpilot-v1`, `step2-llm-runtime`, `step3-research-environment` (in `public`/check-2 refs) |

### Verification results (Phase 0 re-run)

```text
pytest: 102 passed, 1 skipped in 2.42s
ruff check: All checks passed!
mypy src: Success: no issues found in 118 source files

benchmark baseline (mock, seed 42):
  experiment=e399e30a-0ee8-45ad-a63e-a603b5d02fc2
  tasks=48, success_rate=1.000, mean_regret=0.0430, mean_top_k_recall=0.458

benchmark verifier-best-of-n (mock, seed 42):
  experiment=ffa7fe5d-007c-4b8a-8157-82e7968c201d
  tasks=48, success_rate=1.000, mean_regret=0.0618, mean_top_k_recall=0.208

benchmark adaptive-planner (mock, seed 42):
  experiment=8ffbe4bf-4eb3-448a-8e76-36b24f7a4b9c
  tasks=48, success_rate=1.000, mean_regret=0.0430, mean_top_k_recall=0.403

showcase: runs/039ef6c2-b6fc-499d-89a9-533ccb2942a9, COMPLETED, 79 trajectory events
doctor: version 0.1.0, offline capability available, no API key configured
```

The v1 baseline reproduces exactly: `0.0430 / 0.458 / 1.000`. No historical result was altered.

---

## 3. Architecture Overview

The dependency direction is strictly layered:

```text
Domain (pure, framework-independent)
   ↑
Agents (typed roles, structured results)
   ↑
LLM abstraction (provider-neutral client)
   ↑
Provider adapters (OpenAI-compatible; SDK isolated)
```

Research tools sit beside agents behind the same boundary:

```text
Domain → Agents → ToolExecutor → Research provider adapters
                                  → Source → Retrieval → Snapshot → Evidence → Finding → Recommendation
```

Coordination is **not** free-form agent chat. It is:

```text
Task DAG + Shared ResearchState + Evidence Store + Structured Events (trajectory JSONL)
```

### Module responsibilities and code locations

| Module | Responsibility | Code location | Status |
| --- | --- | --- | --- |
| `domain/` | Typed contracts: enums, goals/constraints/budget, task nodes, evidence, findings, candidates/scoring/risk/recommendation, shared `ResearchState` blackboard | `src/marketpilot/domain/*.py` | IMPLEMENTED, tested, reuse as-is |
| `agents/` | Role contracts (`Agent`, `AgentResult`, `AgentContext`), registry; 8 deterministic mock agents; LLM-backed role agents | `src/marketpilot/agents/*.py` | IMPLEMENTED, tested |
| `llm/` | Provider-neutral client contract, typed request/response/usage models, retry policy, budget guard, pricing, structured-output parsing, OpenAI-compatible adapter, scripted mock client | `src/marketpilot/llm/*.py` | IMPLEMENTED, tested |
| `prompts/` | Versioned prompt registry with deterministic SHA-256 hashing | `src/marketpilot/prompts/*.py` | IMPLEMENTED, tested |
| `tools/` | Typed tool protocol, registry, mock tools, research tools (web search + page fetch) with replay/budget hooks | `src/marketpilot/tools/*.py` | IMPLEMENTED, tested |
| `research/` | Typed source/retrieval/snapshot models, canonicalization, dedup, replay store, budget tracker, provenance store, search/retrieval adapters (Tavily, HTTP), synthetic providers | `src/marketpilot/research/*.py` | IMPLEMENTED, tested |
| `synthetic/` | Deterministic market generator (8 categories, 10 regimes), v1+v2 source corpora, environment hiding latent ground truth, dataset validation | `src/marketpilot/synthetic/*.py` | IMPLEMENTED, tested, FROZEN as v1 |
| `benchmark/` | Suite (48 tasks), loader, strategies (baseline, best-of-n, verifier-guided, adaptive, memory), runner, evaluation, export, generation policies, LLM candidate ranker, step5 pool/diagnostics/forensics | `src/marketpilot/benchmark/*.py` | IMPLEMENTED, tested; v1 suite FROZEN |
| `verifier/` | Deterministic evidence/constraint/diversity verification | `src/marketpilot/verifier/*.py` | IMPLEMENTED, tested |
| `memory/` | Episodic + skill memory (structured retrieval, deterministic skill extraction), memory contracts + in-memory store | `src/marketpilot/memory/*.py` | IMPLEMENTED, tested |
| `orchestration/` | Task DAG, deterministic planner, bounded adaptive planner, DAG runner with trajectory/LLM metrics | `src/marketpilot/orchestration/*.py` | IMPLEMENTED, tested |
| `observability/` | Typed event models, trajectory recorder, structured JSON logging | `src/marketpilot/observability/*.py` | IMPLEMENTED, tested |
| `evaluation/` | Structural evaluator + typed schemas; candidate promotion forensics (zero-API) | `src/marketpilot/evaluation/*.py` | IMPLEMENTED, tested |
| `persistence/` | SQLAlchemy models, repositories, UnitOfWork, SQLite engine | `src/marketpilot/persistence/*.py` | IMPLEMENTED, tested |
| `reporting/` | Typed run report builder + self-contained `report.html` and `benchmark.html` | `src/marketpilot/reporting/*.py` | IMPLEMENTED, tested |
| `product_selection/` | Closed-loop product selection: DecisionCritic, TerminationController, DecisionModule, workers, mock + live environment, loop runner, report | `src/marketpilot/product_selection/*.py` | IMPLEMENTED, tested (Step 6) |
| `cli.py` | 9 subcommands; goal parsing; LLM/research context wiring | `src/marketpilot/cli.py` | IMPLEMENTED, tested |
| `config.py` | Typed settings via `MARKETPILOT_*` env / `.env` | `src/marketpilot/config.py` | IMPLEMENTED |

---

## 4. Verified Capabilities (IMPLEMENTED / EVALUATED)

### IMPLEMENTED and verified offline (all deterministic, no API keys)

- Typed domain contracts with strict reference validation (findings→evidence, recommendations→findings/evidence/risks; missing references rejected).
- 8-role deterministic mock agents and 6 LLM-backed role agents sharing the same `Agent` contract.
- Provider-neutral LLM boundary: `LLMClient`, retry policy (typed retryable/permanent errors, retry exhaustion), budget guard, structured-output parsing, OpenAI-compatible adapter, scripted mock client.
- Tool boundary: typed `ToolArguments`/`ToolOutput`/`ToolResult`, `ToolRegistry`, mock tools, research tools with replay/budget hooks; `ToolExecutor` is the only tool path.
- Research provenance chain: `SourceRecord` → `RetrievalRecord` → `SourceSnapshot` → `EvidenceItem(snapshot_id)` → `Finding` → `Recommendation`.
- Strict replay: `ReplayStore` with deterministic SHA-256 request keys; replay mode never falls back to network; `REPLAY_MISS` is typed.
- URL canonicalization (tracking-param blocklist, default-port strip, trailing-slash strip) and content/request hashing.
- Exact + near-duplicate detection (token shingles + Jaccard threshold 0.75).
- Research budget enforcement at the tool boundary (`BUDGET_EXHAUSTED` typed).
- Synthetic market generator (8 categories, 10 regimes, 144 products, 1012 reviews, 24 v1 sources, 64 v2 facet sources) with hidden latent opportunity/risk ground truth excluded from agent observations.
- 48-task benchmark with business-level evaluation: regret, top-k recall, constraint satisfaction, risk recall, ranking correlation, verifier score, tool-call cost proxy; deterministic reproducibility (two seed-42 runs identical).
- Difficulty tiers easy/medium/hard with controlled observation masking + noise.
- Deterministic verifier with typed issue codes.
- Test-time scaling strategies: baseline, best-of-n (heuristic variants, explicitly not independent LLM rollouts), verifier-guided, adaptive-planner, episodic-memory, skill-memory.
- Adaptive research planner producing bounded follow-up tasks.
- Structured episodic memory + deterministic skill extraction (bounded, inspectable, hidden-truth-free).
- Event-sourced trajectory (typed events, monotonic sequence, unique UUIDv5 IDs, JSONL) + summary + final-state artifacts.
- SQLite persistence + Alembic migration + repositories + UnitOfWork.
- Static self-contained `report.html` and `benchmark.html`.
- Closed-loop product selection (Step 6): DecisionCritic / TerminationController / DecisionModule / WorkerRegistry / ClosedLoopRunner with scenarios A–E passing; live environment wired but not executed without credentials.
- CLI: `demo`, `report`, `dataset generate`, `benchmark run/compare`, `showcase`, `trajectories export`, `llm smoke`, `doctor`, `select-product`.

### EVALUATED (real experiments recorded, honest negative results)

- Baseline saturation diagnosis: original baseline regret 0.0 was formula coupling (Pearson=1.0); after hardening Pearson=0.5563, Spearman=0.4997. Recorded in `docs/experiments/baseline-saturation-analysis.md` and artifacts.
- Verifier/utility alignment: verifier score essentially unaligned (Pearson=0.0, Spearman=0.0259, N=144). Recorded in `docs/experiments/verifier-utility-alignment.md`.
- Hardened benchmark: no tested strategy beats baseline (regret 0.0430).
- Real LLM (qwen-plus via DashScope compatible-mode): provider smoke PASS, real tool call PASS, one full multi-turn task PASS; N=1/2/4 candidate headroom gate: `oracle_gain_n4_vs_n1 = 0.0` on all four DEV tasks — candidate generation is the bottleneck. Recorded in `docs/experiments/STEP5_REAL_LLM_REPORT.md` and `docs/devlog/STEP5_REAL_LLM_EXECUTION_LOG.md`.
- Step 5D policy-diverse gate (v1): evidence overlap 1.0 → Gate A FAIL. Step 5D.2 (v2): evidence overlap ~0.41 → Gate A1 PASS, Gate A2 FAIL (no top-2 frontier promotion). Bottleneck classified: shortlist cutoff / ranking pressure (`docs/devlog/STEP5D2_COMPLETION_REPORT.md`, `artifacts/step5d2/promotion_forensics.md`).
- Bounded real ecommerce validation (Aug 30): 6/6 pages fetched once, 3 domains, replay repeatability ×3 PASS, cross-site decision PASS, evidence-gap follow-up PASS. Recorded in `docs/REAL_ECOMMERCE_VALIDATION.md` (public branch) and `docs/data/real_validation_summary.json`.

### EXPERIMENTAL (not yet validated end-to-end)

- `benchmark/step5_pool.py` resumable DEV candidate-headroom gate — written and tested offline; full real-LLM matrix not executed.
- `benchmark/llm_rollout.py` real LLM rollout over frozen synthetic env — wired; requires credentials.
- `benchmark/llm_decision.py` LLM candidate ranker (with `rank_research` policy-conditioned path) — wired; requires credentials.
- `benchmark/generation_policies.py` explainable generation policies — implemented and unit-tested; live evaluation not executed.
- Live search (Tavily) and live retrieval (HTTP) adapters — implemented and mocked-tested; not executed live (no keys).
- PostgreSQL persistence path — SQLAlchemy URL + optional `postgres` dep group; not exercised live.

### NOT IMPLEMENTED (explicitly out of v1 scope, all listed as roadmap)

- Interactive research workbench (README roadmap item; no server/frontend exists).
- Utility-supervised verifier / learned reward model.
- Independent LLM sampling as a genuine Best-of-N mechanism (current best-of-n is deterministic heuristic variants).
- Human evaluation of selected candidates.
- Trajectory-learning / Agentic RL.
- Source-class inference (always `UNKNOWN`), semantic claim verification, semantic near-duplicate detection.
- Full PostgreSQL runtime integration.

---

## 5. Technical Debt (v1 → carry into V2)

1. **No unified input normalization layer.** `ResearchGoal` normalizes market/category labels only; there is no price/currency/unit/inventory/time normalization, no `ResearchTaskSpec` unifying user constraints + budget + environment, and no input-perturbation tests. This is the V2 Phase 1 gap.
2. **No world-level data split.** The synthetic environment is a single frozen world; there is no dev/confirmation/test world partitioning, no OOD world, no material-change (regime shift) tests. This is the V2 Phase 2/7 gap.
3. **Candidate generation bottleneck is the measured blocker for LLM scaling.** Step 5B/5D/5D.2 all show `oracle_gain_n4_vs_n1 = 0.0` or no frontier promotion. V2 must fix research-action/evidence-use/decision logic before any selector or RSI training (explicit rule in the V2 spec).
4. **No adaptive research controller with VOI.** `AdaptiveResearchPlanner` and `ClosedLoopRunner` are rule-based and budget-unaware in the VOI sense; there is no Regret–Budget or Quality–Cost curve, no explicit `STOP`/`REFUSE`/`HUMAN_REVIEW` action, no evidence-conflict/missing-evidence-driven sequential acquisition beyond the closed-loop scenarios.
5. **No policy registry / replay-world archive / exploration tree / promotion-rollback.** Dream-RSI components are entirely absent. The only replay is the environment-level `ReplayStore` (request→payload), not a trajectory-level historical-replay simulator with coverage accounting.
6. **Memory has no versioning/lifecycle.** `SkillMemory` has no source, version, scope, validation record, capacity budget, dedup, invalidation, or rollback. `EpisodicMemory` is an unbounded dict.
7. **Evaluation harness is structural + synthetic-decision only.** It lacks: NDCG, Feasibility, Evidence Precision, Citation Validity, Unsupported Claim Rate (it has unsupported_claim_rate in evaluator metrics, but not in the benchmark harness), Input Invariance, Material Change Accuracy, Recovery/Reliability, Pass^k, latency per task, cost per successful task, Replay Coverage, RSI Improvement per Online Evaluation, paired bootstrap, repeated runs, OOD/security/fault experiments, and human evaluation.
8. **Persistence is not the runtime source of truth.** Runs are written as JSONL artifacts; SQLite stores benchmark/experiment summaries only. No run-level trajectory persistence.
9. **`ExecutionMetrics.token_cost` and `llm_estimated_cost` are optional/None by default** — no pricing table configured, so real cost is unknown rather than estimated. V2 must record model version and cost when real LLM experiments run.
10. **Skill retrieval is keyword-based; no semantic retrieval.**
11. **`promotion_forensics` and `forensics` are zero-API analysis utilities** — good, keep them; they are the seed of the V2 Evidence Influence Explorer.
12. **The `report.html`/`benchmark.html` are minimal static tables** — the V2 Workbench (Agent Experiment Lab, RSI Evolution Observatory, Evidence Influence Explorer) does not exist.

---

## 6. Reusable Components (keep, do not reinvent)

| Component | Why reuse |
| --- | --- |
| `domain/` typed contracts + `ResearchState` blackboard | Core invariants; reference validation is already strict; reuse as-is for V2 domain layer. |
| `llm/` boundary (client, retry, budget, structured output, adapter, mock) | Provider-neutral and tested; V2 policy/optimization code can call the same client. |
| `tools/` + `ToolExecutor` | Single tool boundary; V2 research actions (search/verify/compare) plug in here. |
| `research/` provenance chain + `ReplayStore` | Strict environment replay; V2 trajectory replay builds on this but is a different concept (see §8). |
| `synthetic/` generator + environment (v1 + v2 sources) | Frozen v1 baseline world; V2 `Synthetic Market v3` extends, never rewrites. |
| `benchmark/` suite + runner + evaluation | Frozen 48-task v1 benchmark; V2 keeps it as the historical baseline and adds a V3 suite. |
| `benchmark/llm_decision.py` + `step5_pool.py` + `generation_policies.py` | Candidate-generation/headroom machinery; V2 Phase 3 builds the multi-branch explorer on top. |
| `evaluation/promotion_forensics.py` + `benchmark/forensics.py` | Zero-API diagnostics; seed for Evidence Influence Explorer and candidate-frontier analysis. |
| `verifier/` | Deterministic process verifier; keep, but V2 must not treat verifier score as decision utility (documented negative result). |
| `memory/` contracts + `EpisodicMemory`/`SkillMemory` | Base for V2 Phase 6 (memory/skill evolution) — extend with versioning/lifecycle, keep retrieval semantics. |
| `product_selection/` closed loop | The only existing budget-aware sequential research loop; V2 Phase 4 controller can reuse its termination/critic vocabulary. |
| `observability/` trajectory recorder + events | Event-sourced artifact layer; V2 exploration tree and RSI observatory can emit the same envelope. |
| `persistence/` + Alembic | Extend tables for policies/worlds/experiments instead of a new DB layer. |
| `reporting/` | Extend renderers for V2 dashboards (static HTML is the proven offline pattern). |
| `cli.py` argparse pattern + `doctor` | Add V2 subcommands following the same pattern. |
| `.github/workflows/ci.yml` | Credential-free CI; V2 keeps offline deterministic tests in CI. |

---

## 7. Modules Recommended for Deletion or Consolidation

- **`synthetic/catalog.py`, `synthetic/trends.py`, `synthetic/reviews.py`, `synthetic/sources.py`, `synthetic/seeds.py`** — thin one-line re-export/docstring stubs with no logic. Consolidate into the generator or delete; they add no value and confuse the package map. (Keep `models.py`, `rules.py`, `generator.py`, `environment.py`, `providers.py`, `validation.py`.)
- **`domain/goals.py::ResearchBudget` vs `research/models.py::ResearchBudget`** — two distinct budget types with overlapping fields (`max_tool_calls` vs `max_search_queries`/`max_page_fetches`/`max_sources`). Consolidate into one typed budget under the V2 `ResearchTaskSpec`; keep both names documented.
- **`benchmark/export.py::RewardComponents`** — currently a stub with zeroed components (all non-`task_success`/`evidence_quality`/`constraint_score` terms are 0). It is exported as "trajectory-learning reward" but is not a real reward. Either implement meaningful components in V2 Phase 7 or remove the claim from README. Do not delete the file if V2 reuses it for the evaluation harness.
- **`benchmark/step5d.py` and `benchmark/step5_pool.py` overlap** — both build top-k pools and compute oracle regret. Consolidate the shared `build_pool` and oracle-regret logic into one module during V2 Phase 3, keeping the historical artifacts untouched.
- **`agents/llm.py` vs `agents/mock.py` duplication** — the LLM agents reimplement tool-loop logic that `LLMAgent` already provides; role classes are thin. This is acceptable for v1; V2 Phase 3 multi-agent ablation will need a single shared worker abstraction, so consolidate role config into data (role → prompt, tools, output model) rather than per-role classes if it grows.

---

## 8. Key V2 Implications (what the audit establishes for the plan)

1. **Frozen v1**: `master@bf5f8e6` and `public@8a804f2` are the frozen baseline. `marketpilot-v1` tag and the 48-task benchmark must not move. V2 adds `synthetic-market-v3` / `benchmark-v3` alongside, never mutating v1.
2. **Hidden truth isolation is already enforced** in v1 (latent fields excluded from `products.jsonl`, evaluator-only access). V2 Phase 2 must extend the same discipline to world-level splits (dev/confirmation/test worlds) and Oracle-only access.
3. **Historical Replay** must not be confused with the existing `ReplayStore` (request→payload). V2's `Historical Replay Simulator` is a *trajectory-level* simulator that replays only observed state transitions, rejects unknown actions, and reports coverage. It needs its own module (`optimization/replay/`), and the audit explicitly forbids using the environment `ReplayStore` for it.
4. **The candidate-frontier bottleneck is the gating fact.** V2 Phase 3 (candidate generation) must come before Phase 5 (RSI); the spec's rule "if no candidate headroom, check research actions/evidence use/decision logic first; do not train a selector or RSI" is directly supported by the Step 5B/5D.2 evidence.
5. **No real-LLM claims without credentials.** All V2 real-LLM experiments must be marked `REQUIRES LIVE LLM VALIDATION`; the offline deterministic path (mock provider, frozen synthetic worlds) is the CI-verifiable core.
6. **No workbench exists.** The V2 Phase 8 "existing Workbench" does not exist in the repository; the deliverable is a new static or lightweight dashboard layer (the audit recommends static HTML following the `reporting/` pattern, with the three panes: Agent Experiment Lab, RSI Evolution Observatory, Evidence Influence Explorer).

---

## 9. Recommended V2 Module Map (layered on top of v1, no rewrites)

```text
src/marketpilot/
├── input/            # NEW (Phase 1): ResearchTaskSpec, constraint normalization/validation,
│                     #   entity recognition, price/currency/unit/inventory/time normalization,
│                     #   input perturbation tests, untrusted-content isolation
├── world/            # NEW (Phase 2): Synthetic Market v3 — hidden attributes, noisy/biased
│                     #   observable evidence, action-revealed evidence, missing/conflict/staleness,
│                     #   difficulty tiers, oracle/agent isolation, world-level dev/conf/test split
├── policy/           # NEW (Phase 3/4): research policies (fixed, missing-evidence, uncertainty,
│                     #   adaptive VOI), candidate frontier explorer, budget-aware sequential
│                     #   controller with search/verify/compare/generate/stop actions
├── optimization/     # NEW (Phase 5): Dream-RSI — ExplorationTree, ReplayWorldArchive,
│                     #   Prefix-only Policy Interface, Historical Replay Simulator,
│                     #   Policy Proposal, Dream Evaluation, Policy Registry, Promotion/Rollback,
│                     #   Recursive Optimization Loop
├── memory/           # EXTEND (Phase 6): versioned skills with source/version/scope/validation/
│                     #   capacity/dedup/invalidation/rollback
├── evaluation/       # EXTEND (Phase 7): full harness (NDCG, feasibility, evidence precision,
│                     #   citation validity, unsupported-claim, input invariance, material change,
│                     #   recovery, pass^k, latency, cost-per-success, replay coverage, RSI gain),
│                     #   paired bootstrap, repeated runs, OOD/security/fault/human eval
├── workbench/        # NEW (Phase 8): Agent Experiment Lab, RSI Evolution Observatory,
│                     #   Evidence Influence Explorer (static HTML, offline)
└── (existing v1 modules unchanged; frozen)
```

---

## 10. Audit Checklist vs V2 Spec Section 1

| V2 spec requirement | Audit finding |
| --- | --- |
| README.md | Read; accurate; states limitations explicitly; roadmap has no workbench yet. |
| docs/PROJECT_STATE.md | Read; canonical status doc; current research question, stable architecture, completed/experimental capabilities, historical failure modes, benchmark status, live-LLM status, next gate. |
| docs/experiments/ historical reports | Read all 4: V1_EXPERIMENT_REPORT, baseline-saturation-analysis, verifier-utility-alignment, STEP5_REAL_LLM_REPORT. |
| src/marketpilot/ core implementation | Read every module (118 files). |
| tests/ existing tests | Read all test files; 102 passed + 1 skipped. |
| pyproject.toml | Read; hatchling build, Python ≥3.12,<3.13, ruff+mypy strict, dev group. |
| Existing CLI | 9 subcommands; argparse; `marketpilot doctor` works. |
| Database models | SQLAlchemy models + Alembic migration; SQLite runtime; repositories + UnitOfWork. |
| Web Workbench | **NOT PRESENT.** README roadmap item only. V2 Phase 8 must build it. |
| Distinguish IMPLEMENTED/EVALUATED/EXPERIMENTAL/NOT IMPLEMENTED | Done in §4 of this document. |

---

## 11. Phase 0 Freeze Evidence (frozen artifacts for V2 baseline)

| Artifact | Location | Frozen value |
| --- | --- | --- |
| Baseline commit | `master@bf5f8e6` | must not move |
| Public release commit | `public@8a804f2` | must not move |
| v1 dataset | `datasets/synthetic-market-v1/` (products 144, reviews 1012, sources 24, sources_v2 64, ground_truth 144) | frozen |
| v1 benchmark suite | `benchmark_runs/` (22 experiment dirs + showcase) | frozen |
| Baseline benchmark result | `benchmark_runs/e399e30a...` (regret 0.0430, top-k 0.458) | frozen |
| Verifier-guided result | `benchmark_runs/ffa7fe5d...` (regret 0.0618, top-k 0.208) | frozen |
| Adaptive result | `benchmark_runs/8ffbe4bf...` (regret 0.0430, top-k 0.403) | frozen |
| Step 5B/5D/5D.2 live artifacts | `artifacts/step5_live/`, `artifacts/step5d2/`, `artifacts/step5_live/rollout_records.jsonl` | frozen |
| Real ecommerce validation | `artifacts/real_validation/` + public-branch docs | frozen |
| Saturation/verifier diagnostics | `artifacts/diagnostics/` | frozen |
| Environment | Python 3.12.14, uv-managed venv, no API keys | recorded |

All Phase 0 verification commands and outputs are in §2 of this document; the detailed V2 baseline report is `docs/experiments/V2_BASELINE_REPORT.md` (companion deliverable).

---

## 12. Conclusion

MarketPilot v1 is a solid, honest, reproducible foundation with no architectural rewrite required. The V2 plan maps cleanly onto it as additive layers. The single most important scientific constraint the audit confirms is that **candidate generation, not selection, is the measured bottleneck**, so V2 must sequence Phase 3 (candidate frontier / research actions) before Phase 5 (Dream-RSI), and must not treat verifier score, evidence count, or replay scores as business quality.
