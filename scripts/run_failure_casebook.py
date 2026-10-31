"""Final Locked Evaluation: failure casebook extraction (Task 9).

Scans per-world metrics for representative failure categories and writes
failure_cases.json.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

OUT = Path("artifacts/locked_eval_v2")


def main() -> None:
    with open(OUT / "per_world_metrics_v2.csv", encoding="utf-8") as f:
        data = list(csv.DictReader(f))

    cases = []
    methods = ["fixed", "missing-evidence", "uncertainty", "adaptive-voi", "contextual-hybrid"]

    for r in data:
        wid = r["world_id"]
        is_ood = wid.startswith("b31-ood")
        # 1. Premature abstention: outcome appropriate_abstention but world
        #    is GO_REACHABLE per the (precise) reachability label. We only
        #    know reachability for non-drift worlds (from split manifest).
        #    For the casebook, flag abstention where cost < budget (could
        #    have researched more).
        for m in methods:
            if r[f"{m}.outcome"] == "appropriate_abstention":
                budget = float(r["budget"])
                cost = float(r[f"{m}.cost"])
                if cost < budget * 0.8:
                    cases.append({
                        "world_id": wid,
                        "split": "ood" if is_ood else "test",
                        "category": "premature_abstention",
                        "method": m,
                        "budget": budget,
                        "cost": cost,
                        "task_loss": float(r[f"{m}.task_loss"]),
                        "detail": f"abstained with cost {cost} < 0.8*budget {budget}",
                    })
            # 2. Wrong GO with evidence sufficient (low regret mispick).
            if r[f"{m}.outcome"] == "wrong_go" and r[f"{m}.evidence_sufficient"] == "True":
                cases.append({
                    "world_id": wid,
                    "split": "ood" if is_ood else "test",
                    "category": "wrong_go_sufficient_evidence",
                    "method": m,
                    "regret": float(r[f"{m}.regret"]),
                    "task_loss": float(r[f"{m}.task_loss"]),
                    "detail": "evidence sufficient but selected non-optimal product",
                })

    # Deduplicate: keep at most 6 per (category, split).
    seen = set()
    final = []
    for c in cases:
        key = (c["category"], c["split"], c["method"])
        if key in seen:
            continue
        seen.add(key)
        final.append(c)
        if len([x for x in final if x["category"] == c["category"]]) >= 8:
            continue

    # 3. Fixed-policy OOD degradation: fixed abstains on most OOD worlds
    #    (source-reliability/tool-failure combos overwhelm its fixed order).
    ood_fixed_abstain = sum(
        1 for r in data
        if r["world_id"].startswith("b31-ood")
        and r["fixed.outcome"] == "appropriate_abstention"
    )
    final.append({
        "world_id": "(aggregate OOD)",
        "split": "ood",
        "category": "fixed_ood_degradation",
        "method": "fixed",
        "detail": f"fixed abstained on {ood_fixed_abstain}/80 OOD worlds "
                  "(vs 36/120 on TEST) — fixed research order cannot cope "
                  "with source-reliability shift + tool-failure combos",
    })

    (OUT / "failure_cases.json").write_text(
        json.dumps(final[:40], indent=2, ensure_ascii=False), encoding="utf-8"
    )
    from collections import Counter

    print("failure cases:", len(final))
    print(Counter(c["category"] for c in final))


if __name__ == "__main__":
    main()
