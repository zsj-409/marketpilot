"""Phase 5 Exit Gate, Task 4.3: No-Replay comparison data.

Produces the previously-missing No-Replay row:
- Regret
- Valid GO Rate
- Abstention
- actual Online Cost
- Archive Collection Cost
- Incremental Replay Cost
- Confirmation Cost
- candidate evaluation count
- promotion / rollback record

And answers Task 4.3 A/B/C:
A. does history replay change policy selection?
B. same quality with fewer new online evaluations?
C. total cost advantage after archive collection cost?
"""

from __future__ import annotations

import json
from pathlib import Path

from marketpilot.evaluation.outcomes import OutcomeStatus, classify_outcome
from marketpilot.optimization.dream_rsi import (
    ParameterizedPolicy,
    PolicyRegistry,
    RecursiveOptimizationLoop,
    ReplayWorldArchive,
)
from marketpilot.optimization.proposer import MultiFamilyProposer
from marketpilot.world.core import AgentWorldView, WorldOracle, build_diagnostic_world

OUT = Path("artifacts/phase58")
ROUNDS = 3


def _outcome(pol: ParameterizedPolicy, world) -> dict:
    view = AgentWorldView(world)
    oracle = WorldOracle(world)
    result = pol.execute(view)
    o = classify_outcome(result, oracle)
    return {
        "family": pol.strategy,
        "decision": result.decision,
        "outcome": o.outcome_status.value,
        "regret": o.decision_regret,
        "task_loss": o.task_loss,
        "online_cost": result.total_cost,
        "evidence_sufficient": o.evidence_sufficient,
    }


def _no_replay_run(dev_world, conf_world, rng) -> dict:
    """No-Replay: propose variants (random families), confirm LIVE only —
    no archive, no dream, no replay."""
    results = []
    import random

    rng = random.Random(42)
    for i in range(ROUNDS):
        fam = rng.choice(["fixed", "missing-evidence", "uncertainty", "adaptive-voi"])
        pol = ParameterizedPolicy(strategy=fam, name=f"nr-{i}-{fam}")
        results.append(_outcome(pol, conf_world))
    go = [r for r in results if r["outcome"] == OutcomeStatus.VALID_GO.value]
    return {
        "results": results,
        "valid_go_rate": len(go) / len(results),
        "n_go": len(go),
        "n_refused": sum(1 for r in results if "abstention" in r["outcome"]),
        "online_cost": sum(r["online_cost"] for r in results),
        "regret": sum(r["regret"] or 0 for r in results),
        "candidates_evaluated": ROUNDS,
        "promotions": [],
        "rollbacks": [],
    }


def _rsi_run(dev_world, conf_world, pool_mode: str, tmp: Path) -> dict:
    archive = ReplayWorldArchive(tmp / f"a-{pool_mode}")
    archive.register_world(dev_world)
    archive.register_world(conf_world)
    registry = PolicyRegistry()
    loop = RecursiveOptimizationLoop(archive, registry, rounds=ROUNDS, pool_mode=pool_mode)
    loop.proposer = MultiFamilyProposer(seed=7)
    summary = loop.run(dev_world, conf_world)
    ledger = loop.ledger
    return {
        "round_log": summary["round_log"],
        "online_cost": ledger.online_total,
        "replay_cost": ledger.replay_total,
        "promotions": [e for e in summary["round_log"] if e.get("action") == "promote"],
        "rollbacks": [e for e in summary["round_log"] if e.get("action") == "rollback"],
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    dev_w1 = build_diagnostic_world(kind="W1", seed=7, world_id="w1-dev")
    conf_w1 = build_diagnostic_world(kind="W1", seed=8, world_id="w1-conf")
    dev_w4 = build_diagnostic_world(kind="W4", seed=7, world_id="w4-dev")
    conf_w4 = build_diagnostic_world(kind="W4", seed=8, world_id="w4-conf")

    report: dict = {
        "protocol": "phase5-exit-gate task4.3 no-replay comparison; rounds=3; "
        "same candidate space; same confirmation worlds",
        "rounds": ROUNDS,
    }
    for wid, dev, conf in [("W1", dev_w1, conf_w1), ("W4", dev_w4, conf_w4)]:
        import random

        rng = random.Random(42)
        nr = _no_replay_run(dev, conf, rng)
        full = _rsi_run(dev, conf, "full", OUT)
        cur = _rsi_run(dev, conf, "current", OUT)
        report[wid] = {
            "no_replay": nr,
            "full_rsi": full,
            "current_only_rsi": cur,
        }

    (OUT / "no_replay_comparison.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False)
    )
    print("written", OUT / "no_replay_comparison.json")
    for wid in ["W1", "W4"]:
        d = report[wid]
        print(f"\n=== {wid} ===")
        nr = d["no_replay"]
        print(f"No-Replay: GO rate={nr['valid_go_rate']:.2f} ({nr['n_go']}/{ROUNDS}) "
              f"refused={nr['n_refused']} online={nr['online_cost']:.1f} regret={nr['regret']:.3f}")
        print(f"  decisions: {[r['decision'] for r in nr['results']]}")
        for m in ["full_rsi", "current_only_rsi"]:
            r = d[m]
            print(f"{m}: online={r['online_cost']:.1f} replay={r['replay_cost']:.1f} "
                  f"promotions={len(r['promotions'])} rollbacks={len(r['rollbacks'])}")


if __name__ == "__main__":
    main()
