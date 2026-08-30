# Contributing

MarketPilot keeps the domain layer framework-independent and the CI path credential-free. Contributions should preserve the typed contracts, deterministic offline tests, evidence provenance, replay semantics, and the authoritative `ToolExecutor` boundary.

Before submitting changes:

```bash
uv sync
uv run ruff format .
uv run ruff check .
uv run mypy src
uv run pytest
```

Add tests for new behavior. Do not commit credentials, `.env` files, generated databases, or large benchmark outputs.
