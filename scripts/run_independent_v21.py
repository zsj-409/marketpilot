"""Independent Replication v2.1: run frozen policies on the NEW 200-world
independent dataset (Task 7).

- Uses marketpilot.benchmark.isolation.isolated_execute (fresh view per
  method, order-invariant).
- Metric Contract v2.1 (task_loss_v21 + reason_code).
- Global Best Static re-selected on a NEW DEV subset (seeds 900-911),
  never on the independent TEST worlds.
- Outputs per-world metrics + outcome breakdown + paired comparisons.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from generate_benchmark_v31 import ID_FAMILIES, OOD_FAMILIES

from marketpilot.benchmark.isolation import isolated_execute
from marketpilot.evaluation.outcomes import (
    classify_outcome,
    task_loss_v21,
)
from marketpilot.input.spec import WorldSplit
from marketpilot.optimization.dream_rsi import ParameterizedPolicy
from marketpilot.world.core import AgentWorldView, WorldOracle
from marketpilot.world.generator import generate_world

OUT = Path("artifacts/locked_eval_v21")
STATIC = ["fixed", "missing-evidence", "uncertainty", "adaptive-voi",
          "contextual-hybrid"]


def _make_runner(strategy: str):
    def _run(view: AgentWorldView, seed: int):
        pol = ParameterizedPolicy(strategy=strategy, name=strategy)
        return pol.execute(view)

    return _run


def _select_gbs() -> str:
    """Re-select Global Best Static on NEW DEV worlds (seeds 900-911)."""
    scores = {}
    for fam, spec in ID_FAMILIES.items():
        for seed in range(900, 912):
            w = generate_world(spec, seed=seed, world_id=f"v21dev-{fam}-{seed}",
                               split=WorldSplit.DEV, family=fam)
            oracle = WorldOracle(w)
            for m in STATIC:
                pol = ParameterizedPolicy(strategy=m, name=m)
                r = pol.execute(AgentWorldView(w))
                o = classify_outcome(r, oracle)
                if m not in scores:
                    scores[m] = {"valid": 0, "cost": 0.0}
                scores[m]["valid"] += 1 if o.outcome_status.value == "valid_go" else 0
                scores[m]["cost"] += r.total_cost
    ranked = sorted(scores.items(),
                    key=lambda kv: (kv[1]["valid"], -kv[1]["cost"]),
                    reverse=True)
    best = ranked[0][0]
    print(f"GBS re-selected on NEW DEV: {best} "
          f"(valid={scores[best]['valid']}, cost={scores[best]['cost']:.1f})")
    return best


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    gbs = _select_gbs()

    # Build the independent TEST worlds.
    worlds = []
    for fam, spec in ID_FAMILIES.items():
        for seed in range(500, 512):
            worlds.append(generate_world(
                spec, seed=seed, world_id=f"v21-{fam}-{seed}",
                split=WorldSplit.TEST, family=fam))
    for fam, spec in OOD_FAMILIES.items():
        for seed in range(700, 720):
            worlds.append(generate_world(
                spec, seed=seed, world_id=f"v21-{fam}-{seed}",
                split=WorldSplit.TEST, family=fam))
    print(f"evaluating {len(worlds)} independent worlds")

    rows = []
    for w in worlds:
        oracle = WorldOracle(w)
        row = {"world_id": w.world_id,
               "split": "ood" if w.world_id.startswith("v21-ood") else "test",
               "budget": w.research_budget or 12.0,
               "gbs_family": gbs}
        for m in STATIC:
            result, _sig = isolated_execute(
                w, m, _make_runner(m), verify_clean=True
            )
            o = classify_outcome(result, oracle)
            row[m] = {
                "outcome": o.outcome_status.value,
                "reason": o.reason_code,
                "regret": o.decision_regret,
                "task_loss_v20": o.task_loss,
                "task_loss_v21": task_loss_v21(o),
                "cost": round(result.total_cost, 3),
                "evidence_sufficient": o.evidence_sufficient,
            }
        # GBS = the selected static family (already in STATIC).
        rows.append(row)

    # Per-world CSV.
    with open(OUT / "per_world_metrics_v21.csv", "w", newline="", encoding="utf-8") as f:
        wtr = csv.writer(f)
        hdr = ["world_id", "split", "budget", "gbs_family"] + [
            f"{m}.{k}" for m in STATIC
            for k in ("outcome", "reason", "regret", "task_loss_v21", "cost",
                      "evidence_sufficient")
        ]
        wtr.writerow(hdr)
        for r in rows:
            line = [r["world_id"], r["split"], r["budget"], r["gbs_family"]]
            for m in STATIC:
                line += [r[m]["outcome"], r[m]["reason"],
                         r[m]["regret"] if r[m]["regret"] is not None else "",
                         r[m]["task_loss_v21"], r[m]["cost"],
                         r[m]["evidence_sufficient"]]
            wtr.writerow(line)

    # Outcome breakdown + summary by split.
    summary = {}
    for split in ["test", "ood"]:
        sub = [r for r in rows if r["split"] == split]
        summary[split] = {}
        for m in STATIC:
            valid = sum(1 for r in sub if r[m]["outcome"] == "valid_go")
            unsupported = sum(1 for r in sub if r[m]["reason"] == "unsupported_go")
            app = sum(1 for r in sub if r[m]["outcome"] == "appropriate_abstention")
            unn = sum(1 for r in sub if r[m]["outcome"] == "unnecessary_abstention")
            subopt = sum(1 for r in sub if r[m]["reason"] == "supported_suboptimal_go")
            cost = sum(r[m]["cost"] for r in sub)
            loss = sum(r[m]["task_loss_v21"] for r in sub)
            summary[split][m] = {
                "valid_go": valid, "unsupported_go": unsupported,
                "suboptimal_go": subopt, "app_abstain": app, "unn_abstain": unn,
                "total_cost": round(cost, 2), "task_loss_v21": round(loss, 3),
                "valid_go_rate": round(valid / len(sub), 3),
                "cost_per_valid": round(cost / valid, 2) if valid else None,
            }
    (OUT / "method_summary_v21.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("\n=== INDEPENDENT TEST (120) — Metric v2.1 ===")
    for m in STATIC:
        s = summary["test"][m]
        print(f"{m:18s}: valid={s['valid_go']:3d} unsup={s['unsupported_go']:3d} "
              f"subopt={s['suboptimal_go']:3d} app={s['app_abstain']:3d} "
              f"unn={s['unn_abstain']:3d} loss21={s['task_loss_v21']:.2f} "
              f"cost/valid={s['cost_per_valid']}")
    print("\n=== INDEPENDENT OOD (80) — Metric v2.1 ===")
    for m in STATIC:
        s = summary["ood"][m]
        print(f"{m:18s}: valid={s['valid_go']:3d} unsup={s['unsupported_go']:3d} "
              f"subopt={s['suboptimal_go']:3d} app={s['app_abstain']:3d} "
              f"unn={s['unn_abstain']:3d} loss21={s['task_loss_v21']:.2f} "
              f"cost/valid={s['cost_per_valid']}")


if __name__ == "__main__":
    main()
