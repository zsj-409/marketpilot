# Changelog

## v1.1.0

- **Web Workbench** (`marketpilot workbench`, http://127.0.0.1:8600): self-contained interactive UI over all project artifacts, no build step and no CDN assets.
  - Overview page with architecture diagram, artifact counts, cross-experiment strategy table, and honest-labeling caveats.
  - Run detail views: clickable task DAG, recommendation score radar, findings/evidence/risk/source chain, SystemEvaluator checks, and a filterable trajectory timeline for all 40+ event types.
  - Closed-loop selection (`select-product`) run views with rounds, gaps, conflicts, and follow-up investigations.
  - Benchmark experiment pages with difficulty/family breakdowns, failure taxonomy donut, and per-task results; multi-experiment comparison with grouped metric charts.
  - Synthetic environment explorer exposing observable agent-facing fields only (hidden ground truth is never read by the workbench).
  - Workbench job submission (demo / benchmark / dataset / select-product) as isolated subprocesses with persisted logs and live status polling.
- New `webui` package: FastAPI app (`server.py`), typed artifact readers (`readers.py`), job manager (`jobs.py`), and a vanilla-JS SPA (`static/`).
- New CLI command `marketpilot workbench [--host H] [--port P]`.
- Fixed run-report duration: `report.html` now computes wall-clock time from event timestamps instead of misusing sequence numbers.
- Added fastapi and uvicorn as runtime dependencies; webui unit tests for readers, jobs, and API endpoints.

## v1.0.0

- Framework-independent domain and multi-agent runtime.
- Provider-neutral LLM boundary with OpenAI and deterministic mock providers.
- Real research environment with Tavily search and HTTP retrieval adapters.
- Source, retrieval, and snapshot provenance with strict replay.
- Versioned synthetic market environment with hidden ground truth.
- SQLite/PostgreSQL persistence models and Alembic migrations.
- MarketPilot synthetic benchmark v1 with business-level decision quality.
- Deterministic verifier, Best-of-N, and verifier-guided Best-of-N strategies.
- Adaptive research planning and structured episodic/skill memory.
- Static `report.html` and `benchmark.html`.
- Zero-credential `marketpilot showcase`.
