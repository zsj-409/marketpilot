# MarketPilot Step 3 Completion Report

## Completed

Step 3 adds a real read-only research environment on top of the unchanged Step 1/2 architecture. It introduces typed source, retrieval, and snapshot models; URL canonicalization; exact and near-duplicate detection; a strict replay store; research budgets; source quality signals; one real search adapter; one real page-retrieval adapter; candidate-ID-based decision output; source-level metrics; research trajectory events; `sources.jsonl`; and a static `report.html`.

## Architecture

```text
Research Goal
      ↓
Deterministic Planner
      ↓
Task DAG
      ↓
LLM-backed Agents
      ↓
LLM Agent Runtime
      ↓
ToolExecutor
      ↓
Web Search / Page Retrieval
      ↓
Source → Retrieval → Snapshot
      ↓
Evidence → Finding → Recommendation
      ↓
Deterministic Verification
      ↓
Evaluation
      ↓
trajectory.jsonl / sources.jsonl / report.html
```

Dependency direction remains:

```text
Domain → Agents → LLM abstraction → Provider adapters
Domain → Agents → ToolExecutor → Research provider adapters
```

## Major Changes

### Research Runtime

New package `src/marketpilot/research/`:

- typed source, retrieval, snapshot, search result, retrieved page, budget, usage, and quality models
- deterministic URL canonicalization and hashing
- exact and near-duplicate detection
- strict replay store
- budget tracker
- source-quality signals
- in-memory provenance store
- provider-neutral search and retrieval protocols
- Tavily search adapter
- HTTP page retriever with safety checks
- deterministic mock research providers

### Search Provider

Selected Tavily (`TavilySearchProvider`). It is isolated behind `SearchProvider`, uses the official API, and normalizes titles, URLs, snippets, ranks, and metadata. Live search was not executed because no search key is configured.

### Retrieval Provider

Selected HTTP page retrieval (`HTTPPageRetriever`). It validates scheme and host, follows redirects, checks content type and size, normalizes text, extracts a title, and records a content hash. Live retrieval was not executed.

### Source Model

`SourceRecord` is a logical identity. `RetrievalRecord` is one retrieval attempt. `SourceSnapshot` is immutable normalized content at a point in time.

### Provenance

`EvidenceItem` gained optional `snapshot_id` and `kind`. Research tools populate snapshot IDs on `ToolOutput`, and the LLM agent runtime preserves them on evidence.

### Replay

`mock`, `live`, and `replay` research modes are supported. Replay mode loads a recorded `replay.jsonl` and never falls back to the network; misses raise `REPLAY_MISS`.

### Deduplication

Canonical URL and content hash detect exact duplicates. Deterministic token shingles plus Jaccard similarity detect near duplicates at threshold 0.75.

### Source Quality

`SourceQualitySignals` exposes deterministic signals including source type, class, publication date availability, author availability, freshness, retrieval completeness, duplicate status, content length, HTTPS, and metadata availability.

### Research Budget

`BudgetTracker` enforces search, page-fetch, and source limits at the ToolExecutor boundary and reports `BUDGET_EXHAUSTED`.

### Candidate ID Migration

`DecisionOutput` now requires `candidate_id`. The decision agent looks up candidates by stable ID and rejects unknown IDs.

### Trajectory Changes

New event types:

```text
SEARCH_REQUESTED
SEARCH_COMPLETED
SEARCH_FAILED
SOURCE_RETRIEVAL_STARTED
SOURCE_RETRIEVAL_COMPLETED
SOURCE_RETRIEVAL_FAILED
SOURCE_SNAPSHOT_CREATED
REPLAY_HIT
REPLAY_MISS
RESEARCH_BUDGET_EXHAUSTED
```

The event envelope, monotonic sequence numbers, unique IDs, and JSONL output are preserved.

### Evaluation Changes

Structural evaluation remains authoritative. Research metrics (source counts, unique sources, duplicates, retrieval success, budget usage) are exposed through the existing state metrics and report.

### Visualization

`reporting/report.py` builds a typed `RunReport` from artifacts and renders a self-contained `report.html` with overview, task DAG, sources, evidence, and errors.

## Tests

Exact final results:

```text
uv sync:
  Resolved 33 packages in 0.90ms
  Checked 33 packages in 1ms

ruff format:
  119 files left unchanged

ruff check:
  All checks passed!

mypy src:
  Success: no issues found in 70 source files

pytest:
  79 passed, 1 skipped in 1.40s
```

The skipped test is the optional live OpenAI smoke test.

## Demos

Step 1 mock demo:

```text
run_id=082dd3c6-0d74-4208-87c5-ae6b9d08104a
status=COMPLETED
```

Step 2 LLM runtime demo:

```text
run_id=5fe54f79-b26d-4165-b075-bdc814c57418
status=COMPLETED
```

Step 3 mock research demo:

```text
run_id=4afb97cd-719a-4d10-8ef1-55305ad030d6
status=COMPLETED
decision=WATCH
sources=3
unique sources=3
snapshots=2
trajectory events=183
LLM calls=19
LLM total tokens=540
tool calls=12
tool success rate=1.0
```

Step 3 replay research demo:

```text
run_id=9eff252c-2bf0-40e6-96f3-adecd206a4ee
status=COMPLETED
decision=WATCH
trajectory events=195
```

## Live Validation

No live research was performed. The environment has neither `MARKETPILOT_LLM_API_KEY` nor `MARKETPILOT_SEARCH_API_KEY`. This is recorded explicitly and is not represented as a live run.

## Generated Artifacts

```text
runs/<run_id>/
├── trajectory.jsonl
├── final_state.json
├── summary.json
├── sources.jsonl
├── replay.jsonl (recorded research runs)
└── report.html
```

All generated trajectories were programmatically validated: JSON parses, sequence numbers are monotonic, event IDs are unique, run IDs are consistent, and no credentials are present.

## Repository Changes

Important added files:

```text
src/marketpilot/research/
src/marketpilot/reporting/
src/marketpilot/tools/research.py
docs/adr/0005-snapshot-research-provenance-replay.md
docs/adr/0006-static-run-visualization.md
docs/devlog/STEP3_EXECUTION_LOG.md
docs/devlog/STEP3_COMPLETION_REPORT.md
tests/fixtures/replay.jsonl
tests/unit/test_research_*.py
tests/unit/test_canonicalization.py
tests/unit/test_dedup.py
tests/unit/test_replay.py
tests/unit/test_budget.py
tests/unit/test_candidate_id.py
tests/unit/test_report.py
tests/integration/test_step3_demo.py
```

Important modified files:

```text
README.md
.env.example
.github/workflows/ci.yml
src/marketpilot/config.py
src/marketpilot/cli.py
src/marketpilot/domain/enums.py
src/marketpilot/domain/evidence.py
src/marketpilot/tools/base.py
src/marketpilot/agents/base.py
src/marketpilot/agents/llm_runtime.py
src/marketpilot/agents/llm.py
src/marketpilot/agents/llm_outputs.py
src/marketpilot/llm/providers/mock.py
src/marketpilot/llm/structured.py
src/marketpilot/orchestration/runner.py
docs/architecture.md
docs/agent-contracts.md
docs/tool-contracts.md
docs/data-model.md
docs/evaluation-plan.md
```

## Known Limitations

- Live search and retrieval were not executed.
- The Tavily adapter is not exercised by CI.
- Source classification defaults to `UNKNOWN`; no opaque trust score is computed.
- Near-duplicate detection is lexical, not semantic.
- The report is intentionally minimal and does not include an interactive graph.
- Structural evaluation does not prove market-truth accuracy.

## Technical Debt

- Runtime source/retrieval/snapshot records are not yet persisted to PostgreSQL.
- Source-class inference rules are intentionally not implemented.
- Full semantic claim verification remains future work.
- Live-provider cost accounting has no configured pricing table.

## Step 4 Readiness

The repository can now support frozen research environments, source snapshots, replay, source-level metrics, and report generation. Step 4 can add PostgreSQL persistence, benchmark datasets, and deeper research evaluation without rewriting retrieval logic.

## Recommended Next Step

Implement Step 4: Benchmark + Persistence + Research Evaluation, starting with PostgreSQL-backed runs and a small market-research benchmark dataset.
