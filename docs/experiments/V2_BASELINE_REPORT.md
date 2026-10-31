# MarketPilot V2 Baseline Report (Phase 0)

Status: BASELINE RECORDED AND FROZEN
Commit: `bf5f8e6` (validation: record three-run replay repeatability)
Public release commit: `8a804f2`
Date: 2026-10-29
Environment: Windows 11, Python 3.12.14 (uv-managed venv in repo), no API keys configured

This report records the v1 baseline exactly as it exists before any V2 work begins. It is the Phase 0 deliverable required by the MarketPilot 2.0 plan: run existing tests and benchmark, save the baseline commit, environment versions, model configuration, historical metrics, and run logs; if the original results cannot be reproduced, analyze the cause without modifying historical data.

## 1. Reproduction Command Sequence

```bash
cd D:\agent_work\_output\marketpilot
# venv: .venv/Scripts/python.exe (Python 3.12.14); uv-managed, editable install
.venv/Scripts/python.exe -m pytest tests/
.venv/Scripts/python.exe -m ruff check src tests      # ruff 0.x from venv
.venv/Scripts/python.exe -m mypy src                  # mypy strict
.venv/Scripts/python.exe -m marketpilot.cli doctor
.venv/Scripts/python.exe -m marketpilot.cli benchmark run --suite marketpilot-synthetic-v1 --strategy baseline --provider mock --seed 42
.venv/Scripts/python.exe -m marketpilot.cli benchmark run --suite marketpilot-synthetic-v1 --strategy verifier-best-of-n --provider mock --seed 42
.venv/Scripts/python.exe -m marketpilot.cli benchmark run --suite marketpilot-synthetic-v1 --strategy adaptive-planner --provider mock --seed 42
.venv/Scripts/python.exe -m marketpilot.cli showcase
```

Note: `uv` is not on PATH in this environment; the repository's own `.venv` (created by uv 0.12.5, Python 3.12.14) is used directly. The venv's editable-install `.pth` file had to be repointed from the original `D:\codex\_output\marketpilot\src` to `D:\agent_work\_output\marketpilot\src` — the code moved between machines but the venv was carried along. This is an environment relocation, not a code change; all results below are from the relocated venv.

## 2. Exact Results

### Tests and static checks

```text
pytest: 102 passed, 1 skipped in 2.42s
  (the 1 skip is the optional live OpenAI smoke test, requires MARKETPILOT_LLM_API_KEY)
ruff check: All checks passed!
mypy src: Success: no issues found in 118 source files
```

### Doctor

```text
MarketPilot version: 0.1.0
Python: 3.12.14
Offline capability: available
LLM provider: mock
LLM model: mock-research-model
LLM API key: missing
Search API key: missing
Database URL: sqlite:///marketpilot.db
Execution modes: mock, llm
Research modes: mock, live, replay
```

### Deterministic benchmark (mock provider, seed 42)

| Experiment | Strategy | Tasks | Success rate | Mean regret | Mean top-k recall | Run dir |
| --- | --- | --- | --- | --- | --- | --- |
| `e399e30a-0ee8-45ad-a63e-a603b5d02fc2` | baseline | 48 | 1.000 | **0.0430** | **0.458** | `benchmark_runs/e399e30a...` |
| `ffa7fe5d-007c-4b8a-8157-82e7968c201d` | verifier-best-of-n | 48 | 1.000 | 0.0618 | 0.208 | `benchmark_runs/ffa7fe5d...` |
| `8ffbe4bf-4eb3-448a-8e76-36b24f7a4b9c` | adaptive-planner | 48 | 1.000 | 0.0430 | 0.403 | `benchmark_runs/8ffbe4bf...` |

Baseline reproduces exactly: `0.0430 / 0.458 / 1.000` — matches the documented v1 hardening result (`docs/experiments/V1_EXPERIMENT_REPORT.md`, `README.md`, `docs/PROJECT_STATE.md`). Verifier-guided and adaptive also match their documented values.

Baseline metrics detail (from `benchmark_runs/e399e30a.../metrics.json`):

```text
task_count: 48
success_rate: 1.0
mean_regret: 0.04301131491122376
mean_top_k_recall: 0.4583333333333333
constraint_satisfaction_rate: 1.0
mean_verifier_score: 0.99375
mean_risk_recall: 0.0
mean_ranking_correlation: 0.7140522875816994
mean_tool_calls: 1.0
by_difficulty:
  easy:   regret 0.1055, top-k 0.0833
  medium: regret 0.0166, top-k 0.6250
  hard:   regret 0.0069, top-k 0.6667
```

### Showcase (zero-credential offline demo)

```text
run: runs/039ef6c2-b6fc-499d-89a9-533ccb2942a9
status: COMPLETED
evaluation_passed: true
task_success_rate: 1.0
evidence_coverage: 1.0
tool_success_rate: 1.0
recommendation: "Demand and margin are acceptable, but medium-high competition and recurring reliability complaints warrant continued monitoring."
decision: WATCH
trajectory events: 79
```

## 3. Frozen Baseline Inventory (must not move)

| Item | Location | Value |
| --- | --- | --- |
| v1 dataset | `datasets/synthetic-market-v1/` | products.jsonl 144, reviews.jsonl 1012, sources.jsonl 24, sources_v2.jsonl 64, trends.jsonl 1728, ground_truth.jsonl 144, manifest, generation_config |
| v1 benchmark experiments | `benchmark_runs/` | 22 experiment dirs + showcase (includes all historical runs and the 3 fresh runs above) |
| v1 diagnostics | `artifacts/diagnostics/` | baseline_saturation.json/csv |
| Step 5 live artifacts | `artifacts/step5_live/` | rollout_records.jsonl, candidate_pool_diagnostics.json/csv, forensics.json/csv, step5d_branch_records.jsonl, step5d_summary.json/csv |
| Step 5D.2 artifacts | `artifacts/step5d2/` | env_freeze.json, promotion_forensics.{md,json,csv}, step5d_branch_records.jsonl, step5d_summary.{json,csv} |
| Real ecommerce validation | `artifacts/real_validation/` | acquisition_summary.json, candidate_summary.json, cross_site_decision.json, evidence_gap_result.json, product_features.jsonl, replay_repeatability.json, validation_report.html, snapshots/ |
| Historical dev logs | `docs/devlog/` | 27 logs (STEP1…STEP6, V1 hardening, real validation) |
| Historical experiments docs | `docs/experiments/` | V1_EXPERIMENT_REPORT.md, baseline-saturation-analysis.md, verifier-utility-alignment.md, STEP5_REAL_LLM_REPORT.md |
| Public release commit | `public@8a804f2` | publish subset of master + REAL_ECOMMERCE_VALIDATION.md, docs/data/real_validation_summary.json, validation/real_ecommerce_validation.example.yaml |

## 4. Environment and Model Configuration

```text
Python: 3.12.x (uv-managed virtual environment)
uv: 0.12.x (lockfile uv.lock)
Runtime deps: pydantic>=2.8, pydantic-settings>=2.4, sqlalchemy>=2.0, alembic>=1.13, openai>=1.40
Dev deps: pytest>=8.3, pytest-asyncio>=0.23, ruff>=0.6, mypy>=1.11
LLM provider: mock (default); OpenAI-compatible adapter configured for live (qwen-plus via DashScope base_url) but NO key present
Model config: llm_model=mock-research-model, temperature=0.0, max_output_tokens=1024, max_retries=2,
              max_model_turns=4, max_tool_calls=8, max_calls_per_task=12, max_rollout_count=4
Research modes: mock / live / replay (live requires keys; not executed)
Database: sqlite:///marketpilot.db (Alembic migration f3c4ed1987f9_initial_schema)
```

## 5. Historical Metrics Recorded (from docs/experiments and dev logs, not re-run)

- Hardened benchmark (v1): baseline 0.0430/0.458, best-of-n N=2 0.0718/0.319, N=4 0.0799/0.278, verifier N=2 0.0618/0.208, N=4 0.0618/0.208, adaptive 0.0430/0.403, episodic-memory 0.0430/0.458, skill-memory 0.0430/0.458.
- Baseline saturation: pre-hardening Pearson=Spearman=1.0 (formula coupling); post-hardening Pearson=0.5563, Spearman=0.4997.
- Verifier/utility alignment: Pearson=0.0, Spearman=0.0259, N=144.
- Real LLM DEV candidate-headroom gate (qwen-plus, 4 tasks × 4 rollouts): `oracle_gain_n4_vs_n1 = 0.0` on all tasks; candidate generation is the bottleneck.
- Step 5D Gate A (v1): FAIL, evidence_overlap=1.0. Step 5D.2 (v2): Gate A1 PASS (evidence_overlap≈0.41), Gate A2 FAIL (no top-2 frontier promotion; shortlist-cutoff / ranking-pressure dominance).
- Real ecommerce validation: 6/6 pages, 3 domains, replay ×3 identical, cross-site decision PASS, evidence-gap PASS.

## 6. Reproduction Notes / Environment Findings (no historical data modified)

1. The only obstacle to immediate reproduction was the venv editable-install path pointing at the old machine path `D:\codex\_output\marketpilot\src`. The `.pth` file was repointed to the current repo path. No source, test, dataset, or artifact was changed; the git working tree is clean.
2. All three benchmark strategies reproduce their documented aggregate values exactly (deterministic mock provider + seed 42).
3. The optional live smoke test (`tests/smoke/test_openai_smoke.py`) is skipped without `MARKETPILOT_LLM_API_KEY`; no live LLM result was fabricated or substituted.
4. No API keys are present in this environment, so all V2 real-LLM experiments are deferred and must be marked `REQUIRES LIVE LLM VALIDATION`.

## 7. Baseline Verdict

```text
V1 BASELINE: REPRODUCED AND FROZEN (102 passed, 1 skipped; ruff clean; mypy clean; benchmark 0.0430/0.458)
NEXT: Phase 1 (stable input & data layer) on top of the frozen baseline.
```
