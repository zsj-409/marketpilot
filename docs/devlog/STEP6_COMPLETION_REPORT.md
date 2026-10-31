# MarketPilot Step 6 Completion Report

## Status

```text
STEP 6 CLOSED-LOOP PRODUCT SELECTION: COMPLETE
```

## Root Problem

The prior skeleton had typed contracts but no causal path from Critic to selective research to state mutation to decision rerun.

## Architecture Added

- `FollowUpTask` and selective `WorkerRegistry`.
- `DecisionModule` isolated from research tools.
- `ClosedLoopRunner` rewired for dynamic follow-up tasks, targeted worker dispatch, state mutation, and decision rerun.
- `LiveResearchEnvironment` connects the same loop to real search/retrieval providers.

## Scenario A Causal Trace

```text
Candidate A initially wins.
Critic: MISSING_EVIDENCE on risk.
Planner: review-risk follow-up task.
Worker: adds negative risk evidence.
Decision reruns.
Candidate B becomes winner.
```

This proves both required causal loops.

## Scenarios

- A: PASS
- B: PASS
- C: PASS
- D: PASS
- E: PASS

## Validation

```text
ruff check: passed
mypy src: no issues in 117 source files
pytest: 102 passed, 1 skipped
secret scan: no API key
offline/replay regression: preserved
```

## Live Path

`marketpilot select-product --mode live` enters the same `ClosedLoopRunner` with `LiveResearchEnvironment`. A live run was not executed because no search credentials were supplied.

`select-product --mode mock` writes `candidates.json`, `recommendation.json`, and a minimal product-oriented `report.html`.

## Known Limitations

- Live candidate discovery does not yet extract price/constraint features from pages.
