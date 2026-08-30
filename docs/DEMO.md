# Demo

The fastest way to see MarketPilot work with no API keys:

```bash
uv run marketpilot showcase
```

This generates the synthetic dataset if needed, runs one research task, persists a run, evaluates it, and prints the `report.html` path.

Generate the full synthetic dataset:

```bash
uv run marketpilot dataset generate --dataset synthetic-market-v1 --seed 42
```

Run the deterministic benchmark:

```bash
uv run marketpilot benchmark run --suite marketpilot-synthetic-v1 --strategy baseline --provider mock
```

Compare verifier-guided Best-of-N:

```bash
uv run marketpilot benchmark run --suite marketpilot-synthetic-v1 --strategy verifier-best-of-n --n 4 --provider mock
```

Replay a recorded research run:

```bash
uv run marketpilot demo --mode llm --provider mock --research-mode replay --replay-run <RUN_ID>
```
