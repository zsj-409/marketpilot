"""Final Locked Evaluation: DEV baselines (Task 1.4) + frozen policy registry.

Runs Random / SimpleHeuristic / CheapestFirst / Fixed / MissingEvidence /
Uncertainty / AdaptiveVOI / ContextualHybrid / FullInformationOracle on the
160 Generation DEV worlds and writes real baseline numbers.
Also selects the Global Best Static on DEV (Task 3.2) and writes the frozen
policy registry (Task 3.4).
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from generate_benchmark_v31 import ID_FAMILIES, SEED_DEV

from marketpilot.benchmark.validity import (
    _cheapest_first_heuristic,
    _full_info_oracle,
    _heuristic_selection,
    _random_selection,
)
from marketpilot.evaluation.outcomes import (
    OutcomeStatus,
    classify_outcome,
)
from marketpilot.input.spec import WorldSplit
from marketpilot.optimization.dream_rsi import ParameterizedPolicy
from marketpilot.world.core import (
    AgentWorldView,
    World,
    WorldOracle,
)
from marketpilot.world.generator import generate_world

OUT = Path("artifacts/locked_eval_v2")


def _run_static(view: AgentWorldView, fam: str):
    pol = ParameterizedPolicy(strategy=fam, name=fam)
    return pol.execute(view)


def _classify(result, oracle) -> dict:
    o = classify_outcome(result, oracle)
    return {
        "outcome": o.outcome_status.value,
        "regret": o.decision_regret,
        "task_loss": o.task_loss,
        "cost": result.total_cost,
        "valid_go": o.outcome_status is OutcomeStatus.VALID_GO,
        "wrong_go": o.outcome_status is OutcomeStatus.WRONG_GO,
        "app_abstain": o.outcome_status is OutcomeStatus.APPROPRIATE_ABSTENTION,
        "unn_abstain": o.outcome_status is OutcomeStatus.UNNECESSARY_ABSTENTION,
        "correct": (not result.refused)
        and result.decision != "INSUFFICIENT"
        and result.selected_id == oracle.best_product_id(),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    worlds: list[World] = []
    for fam, spec in ID_FAMILIES.items():
        for seed in SEED_DEV:
            wid = f"b31-{fam}-{seed}"
            worlds.append(
                generate_world(spec, seed=seed, world_id=wid, split=WorldSplit.DEV, family=fam)
            )
    print(f"DEV worlds: {len(worlds)}")

    methods = [
        "random", "heuristic", "cheapest_first", "fixed", "missing-evidence",
        "uncertainty", "adaptive-voi", "contextual-hybrid", "full_info",
    ]
    rows: list[dict] = []
    for w in worlds:
        oracle = WorldOracle(w)
        row: dict = {
            "world_id": w.world_id,
            "family": w.world_id.split("-")[1],
            "difficulty": w.difficulty.value,
            "budget": w.research_budget or 12.0,
        }
        # P0 fix (integrity audit): each method gets a FRESH view.
        results = {
            "random": _random_selection(w),
            "heuristic": _heuristic_selection(w),
            "cheapest_first": _cheapest_first_heuristic(w, w.research_budget or 12.0),
            "fixed": _run_static(AgentWorldView(w), "fixed"),
            "missing-evidence": _run_static(AgentWorldView(w), "missing-evidence"),
            "uncertainty": _run_static(AgentWorldView(w), "uncertainty"),
            "adaptive-voi": _run_static(AgentWorldView(w), "adaptive-voi"),
            "contextual-hybrid": _run_static(AgentWorldView(w), "contextual-hybrid"),
            "full_info": _full_info_oracle(w),
        }
        for m in methods:
            row[m] = _classify(results[m], oracle)
        rows.append(row)

    # Method summary (DEV).
    summary = {}
    for m in methods:
        valid = sum(1 for r in rows if r[m]["valid_go"])
        wrong = sum(1 for r in rows if r[m]["wrong_go"])
        app = sum(1 for r in rows if r[m]["app_abstain"])
        unn = sum(1 for r in rows if r[m]["unn_abstain"])
        correct = sum(1 for r in rows if r[m]["correct"])
        cost = sum(r[m]["cost"] for r in rows)
        loss = sum(r[m]["task_loss"] for r in rows)
        summary[m] = {
            "valid_go": valid,
            "wrong_go": wrong,
            "app_abstain": app,
            "unn_abstain": unn,
            "correct": correct,
            "total_cost": round(cost, 2),
            "task_loss": round(loss, 3),
            "valid_go_rate": round(valid / len(rows), 3),
            "cost_per_valid_go": round(cost / valid, 2) if valid else None,
        }
    print("\n=== DEV baselines (160 worlds) ===")
    for m in methods:
        s = summary[m]
        print(f"{m:18s}: valid_go={s['valid_go']:3d} wrong={s['wrong_go']:3d} "
              f"app_abstain={s['app_abstain']:3d} unn={s['unn_abstain']:3d} "
              f"correct={s['correct']:3d} cost={s['total_cost']:.1f} "
              f"cost/valid={s['cost_per_valid_go']}")

    # Global Best Static (Task 3.2): quality-first, then cost.
    static_fams = ["fixed", "missing-evidence", "uncertainty", "adaptive-voi"]
    gbs_scores = {}
    for fam in static_fams:
        valid = sum(1 for r in rows if r[fam]["valid_go"])
        cost = sum(r[fam]["cost"] for r in rows)
        gbs_scores[fam] = {"valid_go": valid, "cost": round(cost, 2)}
    ranked = sorted(
        gbs_scores.items(),
        key=lambda kv: (kv[1]["valid_go"], -kv[1]["cost"]),
        reverse=True,
    )
    gbs = ranked[0][0]
    print("\n=== Global Best Static (DEV) ===")
    for fam, sc in sorted(gbs_scores.items()):
        print(f"  {fam}: valid_go={sc['valid_go']} cost={sc['cost']}")
    print(f"  -> BEST: {gbs}")

    # Frozen policy registry (Task 3.4).
    registry = {
        "benchmark_version": "v3.1-locked",
        "evaluation_plan_version": "1.0",
        "frozen_policies": {
            fam: ParameterizedPolicy(strategy=fam, name=fam).hash
            for fam in static_fams
        },
        "contextual_hybrid": ParameterizedPolicy(strategy="contextual-hybrid", name="ch").hash,
        "global_best_static": {
            "family": gbs,
            "hash": ParameterizedPolicy(strategy=gbs, name=f"gbs-{gbs}").hash,
        },
        "dev_world_ids": [w.world_id for w in worlds],
    }
    (OUT / "frozen_policy_registry.json").write_text(
        json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Per-world CSV.
    with open(OUT / "dev_baselines.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        header = ["world_id", "family", "difficulty", "budget"] + [
            f"{m}.{k}" for m in methods
            for k in ("outcome", "regret", "task_loss", "cost")
        ]
        writer.writerow(header)
        for r in rows:
            line = [r["world_id"], r["family"], r["difficulty"], r["budget"]]
            for m in methods:
                line += [
                    r[m]["outcome"],
                    r[m]["regret"] if r[m]["regret"] is not None else "",
                    r[m]["task_loss"],
                    r[m]["cost"],
                ]
            writer.writerow(line)
    print("\nwrote", OUT / "frozen_policy_registry.json")
    print("wrote", OUT / "dev_baselines.csv")


if __name__ == "__main__":
    main()
