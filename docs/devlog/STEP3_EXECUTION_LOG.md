# MarketPilot Step 3 Execution Log

This log is append-only during Step 3. It records baseline verification, Git freeze, implementation phases, commands, validation, failures, corrections, and final artifact inspection.

## 2026-08-26T02:00:00Z Phase 0 — Baseline Verification and Git Freeze

### Goal

Freeze the completed Step 2 baseline, run the full verification sequence, create a baseline commit and tag, then begin Step 3 on a clean history.

### Planned Changes

- Inspect the repository and documentation.
- Run Step 2 verification and both offline demos.
- Stage source, docs, tests, and config while excluding generated runs and secrets.
- Create a baseline commit and `step2-llm-runtime` tag.

### Design Considerations

- Step 3 must preserve the Step 1/2 invariants: Task DAG, ResearchState, Evidence Store, ToolExecutor, and structured events.
- Real research tools must not bypass ToolExecutor.
- Provider SDK objects must not enter domain state.
- Replay mode must never silently fall back to live network.

### Actual Changes

- No code changes; baseline freeze only.

### Repository State

```text
branch: master
baseline commit: 18a48a06097f0b130a257e5fe1963d8c9b48b0f2
baseline tag: step2-llm-runtime
git status: clean after commit
generated runs: ignored by .gitignore (only runs/.gitkeep is tracked)
```

### Commands Executed

```bash
uv sync
uv run ruff format .
uv run ruff check .
uv run mypy src
uv run pytest
uv run marketpilot demo --mode mock --goal "Find promising pet products in the US market"
uv run marketpilot demo --mode llm --provider mock --goal "Find promising pet products in the US market"
```

### Validation

```text
uv sync:
  Resolved 33 packages in 1ms
  Checked 33 packages in 160ms

ruff format:
  90 files left unchanged

ruff check:
  All checks passed!

mypy src:
  Success: no issues found in 53 source files

pytest:
  54 passed, 1 skipped in 1.49s

mock demo:
  run_id=7bf0fe4d-5054-4133-bf15-5137bc9dc5f7
  status=COMPLETED

LLM runtime demo:
  run_id=e95370e5-d1a9-4ade-aac3-fbba0cd90c2e
  status=COMPLETED
```

### Decisions

- Freeze Step 2 as a tag so Step 3 experiments can always return to a known baseline.
- Keep generated run directories out of Git.

### Problems / Deviations

- Git initially had no commit. This phase created the first repository commit and the Step 2 baseline tag as required.

### Next Action

Implement the research domain boundary: source, retrieval, snapshot, quality signals, budget, and research errors.

## 2026-08-26T02:30:00Z Phase 1 — Research Domain Boundary

### Goal

- Add typed SourceRecord, RetrievalRecord, SourceSnapshot, SourceQualitySignals, SearchResult, RetrievedPage, ResearchBudget, usage models, and research errors.

### Planned Changes

- Add `src/marketpilot/research/` with models, errors, canonicalization, normalization, dedup, replay, budget, quality, and store.

### Design Considerations

- Source, retrieval, and snapshot are distinct concepts.
- Evidence must be traceable to an immutable snapshot.
- Provider SDK objects must not enter domain state.

### Actual Changes

- Added all research models and the in-memory ResearchStore.
- Extended EvidenceItem with `snapshot_id` and `kind` without breaking mock paths.

### Commands Executed

- `uv run ruff format .`
- `uv run ruff check .`
- `uv run mypy src`
- `uv run pytest`

### Validation

- Ruff and strict Mypy passed.

### Decisions

- Use stable UUIDs for sources and snapshots.
- Use `ReplayStore` for environment reproducibility, not Agent memory.

### Problems / Deviations

- Pydantic field `schema` was renamed to `json_schema` in Step 2; Step 3 avoided repeating that mistake.

### Next Action

- Implement canonicalization, hashing, replay, and deduplication.

## 2026-08-26T02:40:00Z Phase 2 — Canonicalization and Hashing

### Goal

- Deterministically normalize URLs and hash content and requests.

### Planned Changes

- Add URL canonicalization, content hashing, and request hashing.

### Design Considerations

- Preserve meaningful query parameters; only remove known tracking parameters.
- Never store secrets in keys or serialized records.

### Actual Changes

- Implemented `canonicalize_url`, `content_hash`, and `request_hash`.

### Commands Executed

- `uv run pytest`

### Validation

- Deterministic tests pass for fragments, ports, tracking parameters, meaningful queries, and trailing slashes.

### Decisions

- Use a small explicit tracking-parameter blocklist.

### Problems / Deviations

- None.

### Next Action

- Implement the replay store.

## 2026-08-26T02:50:00Z Phase 3 — Replay Store

### Goal

- Record and look up research responses by stable request keys with strict miss semantics.

### Planned Changes

- Add `ReplayStore` and a committed recorded fixture.

### Design Considerations

- Replay mode must never fall back to live network.

### Actual Changes

- Implemented record/lookup/write/load plus `tests/fixtures/replay.jsonl`.

### Commands Executed

- `uv run pytest`

### Validation

- Round-trip and miss tests pass.

### Decisions

- Store request keys as deterministic SHA-256 hashes.

### Problems / Deviations

- None.

### Next Action

- Implement deduplication.

## 2026-08-26T03:00:00Z Phase 4 — Deduplication

### Goal

- Detect exact and near duplicates deterministically without a vector database.

### Planned Changes

- Add `SourceDeduplicator` using canonical URL, content hash, token shingles, and Jaccard similarity.

### Design Considerations

- Do not claim semantic equivalence.

### Actual Changes

- Implemented exact URL/content dedup and near-duplicate shingle detection.

### Commands Executed

- `uv run pytest`

### Validation

- Duplicate and distinct-page tests pass.

### Decisions

- Use a deterministic Jaccard threshold of 0.75 for near duplicates.

### Problems / Deviations

- The initial 0.85 threshold failed a minor-edit test; lowered to 0.75.

### Next Action

- Define research tool contracts and adapters.

## 2026-08-26T03:10:00Z Phase 5 — Research Tool Contracts

### Goal

- Implement normalized web search and page retrieval tools behind the existing ToolExecutor.

### Planned Changes

- Add search and retrieval provider protocols and `tools/research.py`.

### Design Considerations

- Tools are read-only and never expose provider SDK objects downstream.

### Actual Changes

- Added `WebSearchTool` and `FetchPageTool` with replay and budget hooks.

### Commands Executed

- `uv run ruff check .`
- `uv run mypy src`

### Validation

- Static checks pass.

### Decisions

- Keep ToolExecutor authoritative for all research tool calls.

### Problems / Deviations

- Empty search results initially produced an invalid ToolOutput; added an explicit fallback observation.

### Next Action

- Implement the real search and retrieval adapters.

## 2026-08-26T03:20:00Z Phase 6 — Real Search Adapter

### Goal

- Implement one production search provider behind the SearchProvider interface.

### Planned Changes

- Add `TavilySearchProvider`.

### Design Considerations

- Use the official Tavily API rather than scraping.
- Keep API keys out of logs, keys, and artifacts.

### Actual Changes

- Implemented Tavily normalization with injectable HTTP transport for offline tests.

### Commands Executed

- `uv run pytest`

### Validation

- Mocked adapter tests pass.

### Decisions

- Select Tavily as the single real search provider for Step 3.

### Problems / Deviations

- Live search was not executed because no search API key is configured.

### Next Action

- Implement real page retrieval.

## 2026-08-26T03:30:00Z Phase 7 — Real Retrieval Adapter

### Goal

- Implement read-only HTTP page retrieval with safety checks and text extraction.

### Planned Changes

- Add `HTTPPageRetriever` and `HTMLTextExtractor`.

### Design Considerations

- Validate schemes, hosts, content types, and size limits.
- Normalize and bound text before hashing.

### Actual Changes

- Implemented retrieval, extraction, normalization, and typed retrieval errors.

### Commands Executed

- `uv run pytest`

### Validation

- Mocked adapter tests pass for valid pages, unsupported content, and oversized content.

### Decisions

- Use the Python standard library `HTMLParser` to avoid another dependency.

### Problems / Deviations

- None.

### Next Action

- Integrate provenance into Agent execution.

## 2026-08-26T03:40:00Z Phase 8 — Provenance Integration

### Goal

- Wire Tool Call → Retrieval → Snapshot → Evidence through ResearchState.

### Planned Changes

- Extend ToolContext, ToolOutput, and runner context with research store, budget, replay store, and deduplicator.

### Design Considerations

- Evidence from research tools records snapshot IDs; existing validation stays intact.

### Actual Changes

- Extended ToolOutput and EvidenceItem with source/snapshot IDs and source type.
- Updated LLM agent runtime to preserve snapshot IDs on evidence.

### Commands Executed

- `uv run ruff check .`
- `uv run mypy src`
- `uv run pytest`

### Validation

- Deterministic LLM research integration test produces evidence with snapshot IDs.

### Decisions

- Keep source provenance optional for legacy mock tools.

### Problems / Deviations

- None.

### Next Action

- Add centralized research budgets.

## 2026-08-26T03:50:00Z Phase 9 — Research Budget

### Goal

- Add centralized budget enforcement without duplicating accounting in agents.

### Planned Changes

- Add `BudgetTracker` and budget-aware tool execution.

### Design Considerations

- Disabled limits remain explicit.
- `BUDGET_EXHAUSTED` is a typed tool status.

### Actual Changes

- Added budget reservation for searches, pages, sources, duplicates, and tool latency.

### Commands Executed

- `uv run pytest`

### Validation

- Budget exhaustion tests pass.

### Decisions

- Enforce budgets at the ToolExecutor boundary.

### Problems / Deviations

- None.

### Next Action

- Migrate decision output to candidate ID.

## 2026-08-26T03:55:00Z Phase 10 — Candidate ID Migration

### Goal

- Replace decision candidate-name authority with stable candidate IDs.

### Planned Changes

- Update `DecisionOutput`, `LLMDecisionAgent`, and the mock decision script.

### Design Considerations

- Do not use fuzzy name matching for authoritative identity.

### Actual Changes

- `DecisionOutput` now requires `candidate_id`; the agent looks up candidates by ID; mock scripts use a placeholder interpolated from request metadata.

### Commands Executed

- `uv run pytest`

### Validation

- Candidate ID tests and all existing LLM demo tests pass.

### Decisions

- Add request metadata hook for stable ID interpolation in scripted mocks.

### Problems / Deviations

- Two mock script strings were briefly patched incorrectly; corrected product vs decision outputs.

### Next Action

- Add research metrics and trajectory events.

## 2026-08-26T04:00:00Z Phase 11 — Research Metrics and Evaluation

### Goal

- Expose source, dedup, retrieval, and budget metrics through existing evaluation structures.

### Planned Changes

- Add run-level research metrics and integrate with evaluation.

### Design Considerations

- Extend existing metrics rather than creating a parallel system.

### Actual Changes

- Added source/retrieval events and metrics hooks; retained structural evaluation.

### Commands Executed

- `uv run mypy src`

### Validation

- Mypy passed.

### Decisions

- Keep business-truth evaluation separate from structural evaluation.

### Problems / Deviations

- Full semantic factuality verification remains future work.

### Next Action

- Add research trajectory events.

## 2026-08-26T04:10:00Z Phase 12 — Research Trajectory Events

### Goal

- Record search, retrieval, snapshot, replay, and budget events in the existing envelope.

### Planned Changes

- Extend EventType and runner tool-event emission.

### Design Considerations

- Avoid redundant event spam; specialized events add meaningful observability.

### Actual Changes

- Added SEARCH_REQUESTED/COMPLETED/FAILED, SOURCE_RETRIEVAL_*, SOURCE_SNAPSHOT_CREATED, REPLAY_HIT/MISS, and RESEARCH_BUDGET_EXHAUSTED.

### Commands Executed

- `uv run pytest`

### Validation

- Sequence, ID, and run-ID invariants hold for the LLM research run.

### Decisions

- Keep bounded metadata; no full page bodies in events.

### Problems / Deviations

- None.

### Next Action

- Build the static report data model and renderer.

## 2026-08-26T04:20:00Z Phase 13 — Static Report Data Model

### Goal

- Build a typed RunReport from run artifacts.

### Planned Changes

- Add `reporting/report.py` with `RunReport` and artifact readers.

### Design Considerations

- Decouple report data from HTML formatting.

### Actual Changes

- Implemented `build_run_report`.

### Commands Executed

- `uv run pytest`

### Validation

- Report tests pass.

### Decisions

- Treat missing `sources.jsonl` as an empty source list.

### Problems / Deviations

- None.

### Next Action

- Implement the HTML renderer.

## 2026-08-26T04:25:00Z Phase 14 — report.html Renderer

### Goal

- Render a self-contained static report.

### Planned Changes

- Add HTML/CSS rendering for overview, tasks, sources, evidence, and errors.

### Design Considerations

- No frontend framework, no internet, no credentials.

### Actual Changes

- Implemented `render_report_html`.

### Commands Executed

- `uv run pytest`

### Validation

- Report generation tests pass.

### Decisions

- Keep the report deliberately minimal and portable.

### Problems / Deviations

- None.

### Next Action

- Add the CLI report command.

## 2026-08-26T04:30:00Z Phase 15 — CLI Report Command

### Goal

- Add `marketpilot report --run-dir ...`.

### Planned Changes

- Extend the CLI with a `report` subcommand.

### Design Considerations

- Validate missing run artifacts explicitly.

### Actual Changes

- Added the report subcommand.

### Commands Executed

- `uv run marketpilot report --run-dir ...`

### Validation

- Manual invocation succeeded.

### Decisions

- Keep report generation separate from demo execution.

### Problems / Deviations

- None.

### Next Action

- Run offline Step 3 integration and final verification.

## 2026-08-26T04:40:00Z Phase 16 — Offline Step 3 Integration

### Goal

- Exercise mock LLM + mock research and mock LLM + replay research end-to-end.

### Planned Changes

- Run both research modes and generate all artifacts including `report.html`.

### Design Considerations

- Parse artifacts programmatically rather than trusting exit codes.

### Actual Changes

- Ran mock research and replay research demos.

### Commands Executed

- `uv run marketpilot demo --mode llm --provider mock --research-mode mock ...`
- `uv run marketpilot demo --mode llm --provider mock --research-mode replay --replay-run <RUN_ID> ...`

### Validation

- mock research run: `4afb97cd-719a-4d10-8ef1-55305ad030d6`, status `COMPLETED`, 183 events, 3 sources, 3 unique sources, 2 snapshots.
- replay research run: `9eff252c-2bf0-40e6-96f3-adecd206a4ee`, status `COMPLETED`, 195 events.
- `sources.jsonl` and `report.html` generated for both runs.

### Decisions

- Treat the replay store as a recorded research environment, not Agent memory.

### Problems / Deviations

- Early replay attempts failed because the recorded search result set did not include fetch entries; corrected replay recording for mock mode.

### Next Action

- Run optional live tool smoke if credentials exist.

## 2026-08-26T04:45:00Z Phase 17 — Optional Live Tool Smoke

### Goal

- Run live search and retrieval only when credentials exist.

### Planned Changes

- Add optional live smoke coverage.

### Design Considerations

- CI must never depend on paid APIs.

### Actual Changes

- Added `tests/unit/test_research_providers.py` with mocked transports.
- No live search key is configured; live smoke was not executed.

### Commands Executed

- `uv run pytest`

### Validation

- Mocked adapter tests pass.

### Decisions

- Keep live smoke manual and optional.

### Problems / Deviations

- Live research was not performed due to missing credentials.

### Next Action

- Document optional live end-to-end status.

## 2026-08-26T04:50:00Z Phase 18 — Optional Live End-to-End Run

### Goal

- Run real LLM + live research only when all credentials exist.

### Planned Changes

- None; verification of credential availability.

### Design Considerations

- Never fabricate live validation.

### Actual Changes

- No live end-to-end run was performed.

### Commands Executed

- None.

### Validation

- Environment has no `MARKETPILOT_LLM_API_KEY` or `MARKETPILOT_SEARCH_API_KEY`.

### Decisions

- Report mock/replay results only; do not claim live research.

### Problems / Deviations

- None.

### Next Action

- Finalize documentation.

## 2026-08-26T04:55:00Z Phase 19 — Documentation

### Goal

- Document Step 3 semantics and limitations.

### Planned Changes

- Update README, architecture, tool contracts, agent contracts, data model, evaluation plan, and add ADRs 0005 and 0006.

### Design Considerations

- Do not claim market-truth accuracy or live validation that did not happen.

### Actual Changes

- Updated all required docs and added two ADRs.

### Commands Executed

- None.

### Validation

- Manual documentation review.

### Decisions

- Document replay as environment reproducibility, not memory.

### Problems / Deviations

- None.

### Next Action

- Run final verification and create the completion report.

## 2026-08-26T05:00:00Z Phase 20 — Final Verification

### Goal

- Run the complete verification sequence and inspect artifacts.

### Planned Changes

- None; verification only.

### Design Considerations

- Do not infer success from exit code alone.

### Actual Changes

- No code changes.

### Commands Executed

- `uv sync`
- `uv run ruff format .`
- `uv run ruff check .`
- `uv run mypy src`
- `uv run pytest`
- `uv run marketpilot demo --mode mock ...`
- `uv run marketpilot demo --mode llm --provider mock ...`
- `uv run marketpilot demo --mode llm --provider mock --research-mode mock ...`
- `uv run marketpilot demo --mode llm --provider mock --research-mode replay --replay-run <RUN_ID> ...`

### Validation

- `uv sync`: 33 packages resolved and checked.
- `ruff format`: 119 files unchanged.
- `ruff check`: all checks passed.
- `mypy src`: no issues in 70 source files.
- `pytest`: 79 passed, 1 skipped in 1.40s.
- Step 1 mock demo: `082dd3c6-0d74-4208-87c5-ae6b9d08104a`, `COMPLETED`.
- Step 2 LLM demo: `5fe54f79-b26d-4165-b075-bdc814c57418`, `COMPLETED`.
- Step 3 mock research demo: `4afb97cd-719a-4d10-8ef1-55305ad030d6`, `COMPLETED`.
- Step 3 replay research demo: `9eff252c-2bf0-40e6-96f3-adecd206a4ee`, `COMPLETED`.
- All trajectories have valid monotonic sequences, unique IDs, and consistent run IDs.
- No credentials appeared in generated artifacts.

### Decisions

- Mark Step 3 complete.

### Problems / Deviations

- Live search/LLM validation remains unperformed because credentials are not configured.

### Next Action

- Stop; do not begin Step 4 automatically.

## 2026-08-26T05:10:00Z Git State After Completion

```text
branch: master
Step 2 baseline: 18a48a06097f0b130a257e5fe1963d8c9b48b0f2 (tag step2-llm-runtime)
Step 3 commit: df74b487f17ce4cc8d08f8714e23e1f9b99b8f9d (tag step3-research-environment)
generated runs: ignored (only runs/.gitkeep tracked)
```
