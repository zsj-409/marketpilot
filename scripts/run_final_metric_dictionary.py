"""Final Evidence Release (Milestone A): recompute the full metric dictionary
from per-task records (Task A1/A2/A3).

- Supported GO = Supported Optimal GO + Supported Suboptimal GO
- Cost per Supported GO = total_executed_research_cost / supported_go_count
- Oracle-Optimal cost kept as auxiliary diagnostic
- Outcome counts must sum exactly to 120 (TEST) / 80 (OOD) per method
- All from artifacts/locked_eval_v21/per_world_metrics_v21.csv (never recomputed)
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

OUT = Path("artifacts/locked_eval_v21")
STATIC = ["fixed", "missing-evidence", "uncertainty", "adaptive-voi",
          "contextual-hybrid"]


def main() -> None:
    with open(OUT / "per_world_metrics_v21.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    splits = {"test": [r for r in rows if r["split"] == "test"],
              "ood": [r for r in rows if r["split"] == "ood"]}
    dictionary = {"version": "1.0",
                  "definitions": {
                      "supported_go": "evidence-sufficient GO (optimal + suboptimal)",
                      "oracle_optimal_supported_go": "evidence-sufficient GO == oracle best",
                      "supported_suboptimal": "evidence-sufficient GO != oracle best",
                      "unsupported_go": "GO without sufficient evidence",
                      "cost_per_supported_go": "total_cost / supported_go_count (N/A if 0)",
                  }}

    for split, sub in splits.items():
        dictionary[split] = {}
        for m in STATIC:
            total = len(sub)
            valid = sum(1 for r in sub if r[f"{m}.outcome"] == "valid_go")
            subopt = sum(1 for r in sub if r[f"{m}.reason"] == "supported_suboptimal_go")
            unsup = sum(1 for r in sub if r[f"{m}.reason"] == "unsupported_go")
            app = sum(1 for r in sub if r[f"{m}.outcome"] == "appropriate_abstention")
            unn = sum(1 for r in sub if r[f"{m}.outcome"] == "unnecessary_abstention")
            cost = sum(float(r[f"{m}.cost"]) for r in sub)
            supported = valid + subopt
            loss = sum(float(r[f"{m}.task_loss_v21"]) for r in sub)
            # Closure check: every outcome must be one of the categories.
            covered = valid + subopt + unsup + app + unn
            assert covered == total, f"{m} {split}: {covered} != {total}"
            dictionary[split][m] = {
                "n_tasks": total,
                "supported_go": supported,
                "oracle_optimal_supported_go": valid,
                "supported_suboptimal": subopt,
                "unsupported_go": unsup,
                "appropriate_abstention": app,
                "unnecessary_abstention": unn,
                "closure_ok": covered == total,
                "supported_go_rate": round(supported / total, 4),
                "oracle_optimal_rate": round(valid / total, 4),
                "unsupported_go_rate": round(unsup / total, 4),
                "abstention_rate": round((app + unn) / total, 4),
                "task_loss_v21_total": round(loss, 3),
                "mean_task_loss_v21": round(loss / total, 4),
                "total_cost": round(cost, 2),
                "cost_per_supported_go": round(cost / supported, 2) if supported else None,
                "cost_per_oracle_optimal": round(cost / valid, 2) if valid else None,
            }

    (OUT / "final_metric_dictionary.json").write_text(
        json.dumps(dictionary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("=== TEST (120) — Final Metric Dictionary ===")
    for m in STATIC:
        d = dictionary["test"][m]
        print(f"{m:18s}: supported={d['supported_go']:3d} "
              f"(optimal {d['oracle_optimal_supported_go']} + subopt {d['supported_suboptimal']}) "
              f"unsup={d['unsupported_go']:3d} abstain={d['abstention_rate']:.2f} "
              f"cost/sup={d['cost_per_supported_go']} cost/opt={d['cost_per_oracle_optimal']} "
              f"mean_loss={d['mean_task_loss_v21']:.3f}")
    print("=== OOD (80) — Final Metric Dictionary ===")
    for m in STATIC:
        d = dictionary["ood"][m]
        print(f"{m:18s}: supported={d['supported_go']:3d} "
              f"(optimal {d['oracle_optimal_supported_go']} + subopt {d['supported_suboptimal']}) "
              f"unsup={d['unsupported_go']:3d} abstain={d['abstention_rate']:.2f} "
              f"cost/sup={d['cost_per_supported_go']} cost/opt={d['cost_per_oracle_optimal']} "
              f"mean_loss={d['mean_task_loss_v21']:.3f}")
    print("\nclosure checks:", all(
        d["closure_ok"] for s in ("test", "ood") for d in dictionary[s].values()
    ))


if __name__ == "__main__":
    main()
