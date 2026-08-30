# MarketPilot

MarketPilot is a reproducible multi-agent product-research platform with a real LLM runtime, a real read-only research environment, a hidden-ground-truth synthetic market benchmark, provenance, replay, verifier-guided test-time scaling, adaptive planning, memory, persistence, and offline run visualization.

[![Python](https://img.shields.io/badge/python-3.12-blue.svg)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![CI](https://img.shields.io/badge/CI-credential--free-blue.svg)]()
[![Ruff](https://img.shields.io/badge/lint-ruff-5b2a86.svg)]()
[![Mypy](https://img.shields.io/badge/types-mypy-2a6db2.svg)]()
[![Tests](https://img.shields.io/badge/tests-pytest-orange.svg)]()

## Why This Project

Cross-border e-commerce teams need product research that is auditable, repeatable, and improvable. Prompt-only agent demos fail because they hide state, lose provenance, cannot be replayed, and offer no meaningful decision-quality signal. MarketPilot demonstrates the full Agent research loop with evidence, trajectory, and benchmark evaluation.

## Demo

No API keys required:

```bash
uv run marketpilot showcase
```

## Architecture

```text
                 Research Goal
                       ↓
                 Research Planner
                 /             \
           Fixed DAG      Adaptive DAG
                 \             /
                       ↓
                 Multi-Agent Runtime
                       ↓
                   ToolExecutor
              /         |          \
       Synthetic      Replay       Live
        Market        Research    Research
              \         |          /
                       ↓
                Evidence Graph
                       ↓
                Candidate Set
                       ↓
          ┌────────────┴────────────┐
          ↓                         ↓
      Baseline                 Best-of-N
                                    ↓
                                Verifier
                                    ↓
                             Recommendation
                                    ↓
                                Evaluator
                                    ↓
                              Benchmark DB
                                    ↓
                             benchmark.html
```

## Agent Roles

ResearchManager, MarketResearch, ProductResearch, ReviewMining, CompetitorResearch, RiskAnalysis, Decision, and EvidenceVerifier. Agents coordinate through a typed shared blackboard, not free-form chat.

## Research Environment

`mock`, `replay`, and `live` research modes share the same `ToolExecutor`. Live mode includes a Tavily search adapter and a read-only HTTP page retriever. Replay mode is strict and never falls back to the network.

## Synthetic Market Environment

The deterministic generator creates an internally consistent market from category profiles and regime rules. Hidden latent opportunity and risk scores form benchmark ground truth and are never exposed to agents.

## Evidence & Provenance

Every finding references evidence. Every evidence item can trace to a source snapshot, retrieval record, and tool call. Recommendations must reference findings, evidence, and risks.

## Verifier

A deterministic verifier checks evidence, snapshot existence, constraint satisfaction, source diversity, risk coverage, and numeric consistency, returning inspectable issues and a score.

## Test-Time Scaling

Baseline N=1, Best-of-N, and verifier-guided Best-of-N strategies run against the same frozen synthetic environment.

## Adaptive Planning

An optional bounded planner can spawn follow-up research tasks when evidence, diversity, competitor coverage, risk, or constraint coverage is missing.

## Memory & Skills

Structured episodic memory stores successful and failed episodes and retrieves them by category, task type, and constraint overlap. Deterministic skill extraction turns recurring evidence patterns into bounded, inspectable skills.

## Benchmark

MarketPilot Synthetic Benchmark v1 contains 48 tasks across eight categories and six families. Evaluation is split into structural, research-quality, and synthetic decision-quality levels.

## Evaluation

Decision-quality metrics include regret, top-k recall, constraint satisfaction, risk recall, ranking correlation, and verifier score. Results are labeled synthetic-environment decision quality, not real market accuracy.

## Experiment Reproducibility

Every benchmark run writes a manifest with git commit, dataset version, generator version, seed, strategy, model, provider, prompt versions, budget, and timestamps.

## Example Results

Run the benchmark to regenerate results:

```bash
uv run marketpilot benchmark run --suite marketpilot-synthetic-v1 --strategy baseline --provider mock
uv run marketpilot benchmark run --suite marketpilot-synthetic-v1 --strategy verifier-best-of-n --n 4 --provider mock
uv run marketpilot benchmark compare <experiment-a> <experiment-b>
```

Representative synthetic benchmark results after hardening:

| Strategy | Mean regret | Top-k recall |
| --- | --- | --- |
| Baseline | 0.0430 | 0.458 |
| Best-of-N N=4 | 0.0799 | 0.278 |
| Verifier-guided N=4 | 0.0618 | 0.208 |
| Adaptive planner | 0.0430 | 0.403 |

Key finding: process verification score was essentially unaligned with hidden decision utility (`Spearman = 0.026`). More computation did not automatically improve final product selection. These are synthetic-environment results, not real market performance.

## Failure Analysis

The benchmark reports a typed failure taxonomy with counts and representative examples in `benchmark.html`.

## Project Structure

```text
src/marketpilot/
├── agents/            # LLM and deterministic agents
├── benchmark/         # synthetic benchmark and strategies
├── domain/            # typed domain contracts
├── evaluation/        # structural and business evaluation
├── llm/               # provider-neutral LLM runtime
├── memory/            # episodic and skill memory
├── observability/     # trajectory events and logging
├── orchestration/     # DAG, planner, adaptive planner, runner
├── persistence/       # SQLAlchemy models and repositories
├── prompts/           # versioned prompts
├── reporting/         # report.html and benchmark.html
├── research/          # research tools, replay, provenance
├── synthetic/         # synthetic market environment
├── tools/             # tool protocol and registry
└── verifier/          # deterministic verification
```

## Quick Start

```bash
uv sync
uv run marketpilot doctor
uv run marketpilot dataset generate --dataset synthetic-market-v1 --seed 42
uv run marketpilot showcase
```

See [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md) for the canonical project status and [docs/experiments/V1_EXPERIMENT_REPORT.md](docs/experiments/V1_EXPERIMENT_REPORT.md) for benchmark findings.

## Run a Benchmark

```bash
uv run marketpilot benchmark run --suite marketpilot-synthetic-v1 --strategy baseline --provider mock
```

## Run with a Real LLM

Set `MARKETPILOT_LLM_API_KEY` and run:

```bash
uv run marketpilot demo --mode llm --provider openai --model gpt-4o-mini
```

## Run with Live Research

Set `MARKETPILOT_SEARCH_API_KEY` and run:

```bash
uv run marketpilot demo --mode llm --provider mock --research-mode live
```

## Limitations

Synthetic benchmark results describe behavior inside MarketPilot's deterministic synthetic environment. They are not claims about real product-market performance. The candidate-scaling experiments use deterministic heuristic variants, not independent LLM rollouts. Live research requires user-supplied API keys and was not executed during development.

## Status

- IMPLEMENTED: Agent runtime, research environment, provenance, replay, benchmark, verifier, persistence, reporting.
- EVALUATED: Baseline, candidate scaling, verifier selection, adaptive planning, memory.
- OPTIONAL LIVE VALIDATION: Not executed; no API keys were configured.
- FUTURE WORK: Independent LLM sampling, utility-supervised verifier, human evaluation, Agentic RL.

## Roadmap

- PostgreSQL-backed benchmark runs and source snapshots.
- Larger benchmark datasets and human evaluation.
- Reflection loops and more advanced test-time scaling.
- Trajectory-learning reward modeling and Agentic RL.
- Interactive research workbench.

## Engineering Decisions

- Framework-independent domain and agent contracts.
- Provider SDKs isolated behind adapters.
- Evidence before recommendation.
- Event-sourced trajectories.
- Replay for environment reproducibility, separate from memory.
- Credential-free CI.
