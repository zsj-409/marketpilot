"""Final Results Integrity Audit: outcome x reachability crosstab (Task 1).

Reads the ORIGINAL per_world_metrics_final.csv and the frozen split
manifest reachability labels, and produces:
- outcome_by_reachability.csv  (reachability_label x outcome_status, per method)
- scarce-world per-method decision detail (budget / spent / evidence / outcome)

Outputs to artifacts/locked_eval_audit/ (never overwrites the original).
"""

from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from generate_benchmark_v31 import ID_FAMILIES, OOD_FAMILIES

from marketpilot.input.spec import WorldSplit
from marketpilot.world.generator import generate_world

SRC = Path("artifacts/locked_eval")
OUT = Path("artifacts/locked_eval_audit")
METHODS = [
    "random", "heuristic", "cheapest_first", "fixed", "missing-evidence",
    "uncertainty", "adaptive-voi", "contextual-hybrid", "full_info",
]


def _reachability_for_world(world_id: str) -> str:
    """Recompute the CURRENT reachability label (post Task-1.1 fix)."""
    m2 = re.match(r"b31-(.+)-(\d+)$", world_id)
    assert m2 is not None
    fam, seed = m2.group(1), int(m2.group(2))
    spec = ID_FAMILIES.get(fam) or OOD_FAMILIES.get(fam)
    assert spec is not None
    split = WorldSplit.TEST if seed >= 300 else WorldSplit.DEV
    w = generate_world(spec, seed=seed, world_id=world_id, split=split, family=fam)
    from marketpilot.benchmark.validity import ExactBudgetedReachabilityOracle

    r = ExactBudgetedReachabilityOracle(
        w, budget=w.research_budget or 12.0, max_states=50_000
    ).solve()
    return r.status.value


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with open(SRC / "per_world_metrics_final.csv", encoding="utf-8") as f:
        data = list(csv.DictReader(f))

    # Cache reachability labels.
    reach_cache = {}
    for row in data:
        wid = row["world_id"]
        if wid not in reach_cache:
            reach_cache[wid] = _reachability_for_world(wid)

    # --- Task 1: outcome x reachability crosstab per method/split --------
    crosstab_rows = []
    for split_name, is_ood in [("test", False), ("ood", True)]:
        for m in METHODS:
            table = Counter()
            for row in data:
                if row["world_id"].startswith("b31-ood") != is_ood:
                    continue
                table[(reach_cache[row["world_id"]], row[f"{m}.outcome"])] += 1
            for (reach, outcome), count in sorted(table.items()):
                crosstab_rows.append({
                    "split": split_name, "method": m,
                    "reachability": reach, "outcome": outcome, "count": count,
                })
    with open(OUT / "outcome_by_reachability.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["split", "method", "reachability", "outcome", "count"])
        for r in crosstab_rows:
            w.writerow([r["split"], r["method"], r["reachability"],
                        r["outcome"], r["count"]])
    print("wrote outcome_by_reachability.csv")

    # --- Task 1: scarce (ABSTENTION_REQUIRED) TEST detail ---------------
    scarce_rows = []
    for row in data:
        if not row["world_id"].startswith("b31-scarce-"):
            continue
        if row["world_id"].startswith("b31-ood"):
            continue
        for m in METHODS:
            scarce_rows.append({
                "world_id": row["world_id"],
                "budget": row["budget"],
                "method": m,
                "outcome": row[f"{m}.outcome"],
                "spent": row[f"{m}.cost"],
                "evidence_sufficient": row[f"{m}.evidence_sufficient"],
                "task_loss": row[f"{m}.task_loss"],
                "reachability": "abstention_required",
            })
    with open(OUT / "scarce_test_detail.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["world_id", "budget", "method", "outcome", "spent",
                    "evidence_sufficient", "task_loss", "reachability"])
        for r in scarce_rows:
            w.writerow([r["world_id"], r["budget"], r["method"], r["outcome"],
                        r["spent"], r["evidence_sufficient"], r["task_loss"],
                        r["reachability"]])
    print("wrote scarce_test_detail.csv")

    # Summary: methods' decisions on the 12 scarce TEST worlds.
    print("\n=== 12 scarce TEST worlds (ABSTENTION_REQUIRED) ===")
    for m in METHODS:
        sub = [r for r in scarce_rows if r["method"] == m]
        c = Counter(r["outcome"] for r in sub)
        print(f"{m:18s}: {dict(c)}")


if __name__ == "__main__":
    main()
