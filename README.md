# MarketPilot

**A reproducible multi-agent product-research platform: real LLM runtime, deterministic safety gate, hidden-ground-truth synthetic benchmark, and auditable evidence chains.**

MarketPilot demonstrates a complete agent research loop — from user request to evidence-backed product recommendation — with full provenance, replay, budget-aware research controllers, and a locked, independently replicated evaluation suite. It is built to be **deterministic, offline-testable, and auditable**: every claim in the docs maps to a real experiment artifact, never a fabricated result.

[![Python](https://img.shields.io/badge/python-3.12-blue.svg)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Ruff](https://img.shields.io/badge/lint-ruff-5b2a86.svg)]()
[![Mypy](https://img.shields.io/badge/types-mypy-2a6db2.svg)]()
[![Tests](https://img.shields.io/badge/tests-pytest-322%20passed-orange.svg)]()
[![CI](https://img.shields.io/badge/CI-credential--free-blue.svg)]()

---

## Why This Project

Cross-border e-commerce teams need product research that is **auditable, repeatable, and improvable**. Prompt-only agent demos fail because they hide state, lose provenance, cannot be replayed, and offer no meaningful decision-quality signal. MarketPilot shows how to build an agent loop that:

- **Records every research action** — evidence, sources, timestamps, costs — into a replayable trajectory.
- **Separates hidden truth from agent observation** — controllers never read the oracle; regret is computed evaluator-side.
- **Gates every final recommendation** through a deterministic, strategy-independent Safety Gate that refuses unsafe (evidence-insufficient) GOs.
- **Evaluates honestly** — a locked 440-world synthetic benchmark plus a 200-world independent replication, with pre-registered metrics and three clearly separated historical result generations (INVALIDATED ORIGINAL / POST-AUDIT REANALYSIS v2 / INDEPENDENT REPLICATION v2.1).

## What's Inside

| Layer | Module | What it does |
|---|---|---|
| Input | `src/marketpilot/input/` | Normalization (money, quantity, time), constraint parsing, prompt-injection scanning, perturbation invariance |
| Agents | `src/marketpilot/agents/` | LLM planner/research/decision agents + deterministic mock fallback |
| Orchestration | `src/marketpilot/orchestration/` | DAG runner, research planner |
| Research | `src/marketpilot/research/` | Search/retrieval providers (mock, Tavily, HTTP), evidence store, dedup, budget tracker, replay store |
| Synthetic market | `src/marketpilot/world/` | Hidden-truth world generator (W0–W5 mechanism families), agent view with revealed-evidence isolation |
| Policies | `src/marketpilot/optimization/` | Deterministic research controllers (fixed, missing-evidence, uncertainty, adaptive-voi, contextual-hybrid) + Dream-RSI (experimental) |
| **Safety** | `src/marketpilot/safety/` | **Final Decision Safety Gate** (`gate.py`), full-path gateway (`gateway.py`), evidence trust boundary (`trust.py`) |
| Evaluation | `src/marketpilot/evaluation/` + `benchmark/` | Outcome taxonomy (7 reason codes), Metric Contract v2.1, isolation runner, reachability oracle |
| Workbench | `scripts/serve_workbench.py` + `artifacts/milestone_c/workbench.html` | Interactive demo: run strategies live, inspect evidence chains, Safety Gate verdicts, benchmark tables, runtime status |

## Quickstart (no API keys required)

```bash
uv sync                      # or: python -m pip install -e .
uv run pytest tests/ -q      # 322 passed, 1 skipped
uv run ruff check src tests scripts
uv run mypy src

# Interactive workbench (offline demo):
uv run python scripts/build_workbench.py
uv run python scripts/serve_workbench.py
# open http://127.0.0.1:8000/workbench.html
```

### Real-LLM mode (optional)

The real-LLM runtime speaks OpenAI-compatible chat completions (any provider with a base_url + key). Set the key via environment variable only — it is never read from files inside the repo, never logged, never committed:

```bash
export ARK_API_KEY=...                 # or LLM_API_KEY (OpenAI-compatible provider)
uv run python scripts/run_real_llm_smoke.py    # 4-task smoke
uv run python scripts/run_real_llm_b2.py       # 24-world paired experiment
```

The B2 experiment was executed for real on `deepseek-v4-flash` (volcengine-ark): 24 worlds, 50 calls, 170 tool calls, 87k tokens, 0 schema failures, 0 gate interceptions. Results in `artifacts/milestone_b/real_llm_vs_deterministic.json`.

## Evaluation Honesty

- **Metric Contract v2.1**: an evidence-insufficient GO (`unsupported_go`) is penalized ≥ a correct abstention — guessing without evidence is never rewarded.
- **Independent replication**: 120 ID + 80 OOD worlds with fresh seeds, manifest frozen before reading results. Systematized families (fixed/missing-evidence/uncertainty/contextual-hybrid) are behaviorally equivalent on generous budgets; adaptive-voi is significantly worse (pooled diff +0.338, CI [0.274, 0.403]); fixed is the recommended default.
- **Three result generations are kept separate** — invalidated original runs are never mixed with corrected or independent runs.
- **Dream-RSI is marked EXPERIMENTAL** — no verified independent replay gain.

## Demo / Interview Materials

- `docs/demo/MARKETPILOT_DEMO_GUIDE.md` — clean-environment launch, success + gate-rejection scenarios, 3–5 min talk track.
- `docs/demo/ARCHITECTURE_WALKTHROUGH.md` — layered architecture, data flow, security boundaries.
- `docs/demo/INTERVIEW_QA.md` — ten prepared answers with evidence references.
- `docs/demo/FINAL_RELEASE_SECURITY_AUDIT.md` + `docs/demo/SAFETY_GATE_EVIDENCE_CONTRACT.md` — trust-boundary and server-hardening audit.

## Key Results (Independent Replication, Metric v2.1)

| Method | TEST Supported GO (120) | OOD Supported GO (80) | Unsupported GO (TEST) | Cost/Supported (TEST) |
|---|---|---|---|---|
| fixed / missing-evidence / uncertainty / contextual-hybrid | **84** | 20 | 0 | 14.73 |
| adaptive-voi | 34 | 0 | 55 | 34.71 |

Real LLM (deepseek-v4-flash): 15/24 GO vs fixed 16/24; 0 unsupported GOs; decision agreement 50%; P50 latency 8s.

## License

MIT — see [LICENSE](LICENSE).
