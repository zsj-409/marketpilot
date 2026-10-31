"""Final Locked Evaluation: paired statistical analysis (Task 7).

World-level paired differences + stratified bootstrap by mechanism family.
Outputs paired_comparisons.csv with CI for the 5 primary comparisons.
"""

from __future__ import annotations

import csv
import random
from collections import defaultdict
from pathlib import Path

OUT = Path("artifacts/locked_eval_v2")

PRIMARY = [
    ("A", "adaptive-voi", "fixed"),
    ("B", "contextual-hybrid", "global_best_static"),
    ("C", "full_dream_rsi", "random_multi_family_search"),
    ("D", "full_dream_rsi", "no_replay_optimization"),
    ("E", "full_dream_rsi", "current_only_rsi"),
]


def _bootstrap_ci(diffs: list[float], n_iter: int = 2000, seed: int = 42) -> tuple:
    rng = random.Random(seed)
    n = len(diffs)
    means = []
    for _ in range(n_iter):
        sample = [diffs[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int(0.025 * n_iter)]
    hi = means[int(0.975 * n_iter)]
    return round(lo, 4), round(hi, 4)


def main() -> None:
    # Read the per-world CSV.
    import csv as _csv

    with open(OUT / "per_world_metrics_v2.csv", encoding="utf-8") as f:
        reader = _csv.DictReader(f)
        data = list(reader)

    # Build per-world task_loss per method.
    methods = [
        "random", "heuristic", "cheapest_first", "fixed", "missing-evidence",
        "uncertainty", "adaptive-voi", "contextual-hybrid", "full_info",
    ]
    loss_by_method = {m: {} for m in methods}
    for row in data:
        wid = row["world_id"]
        for m in methods:
            loss_by_method[m][wid] = float(row[f"{m}.task_loss"])

    # Global Best Static = uncertainty (frozen registry); reuse its losses.
    loss_by_method["global_best_static"] = loss_by_method["uncertainty"]

    # For C/D/E: optimization methods not run here (dev-selected); mark
    # NOT_EVALUATED in this phase — the RSI comparison is reported in the
    # attribution analysis (Phase 5.7/5.8 results, budget-matched).
    pairs = []
    for pid, ma, mb in PRIMARY:
        opt_methods = (
            "random_multi_family_search",
            "no_replay_optimization",
            "current_only_rsi",
        )
        if ma == "full_dream_rsi" or mb in opt_methods:
            pairs.append({
                "comparison": pid, "method_a": ma, "method_b": mb,
                "status": "NOT_EVALUATED_in_locked_task_phase",
                "note": (
                    "optimization-efficiency comparison reported in "
                    "FINAL_RSI_ATTRIBUTION_REPORT"
                ),
            })
            continue
        # Paired world-level differences (test + ood, pooled).
        all_wids = list(loss_by_method[ma].keys())
        diffs = [loss_by_method[ma][w] - loss_by_method[mb][w] for w in all_wids]
        mean_diff = sum(diffs) / len(diffs)
        lo, hi = _bootstrap_ci(diffs)
        # Stratified by family.
        fam_diffs = defaultdict(list)
        for w in all_wids:
            fam = w.split("-")[1] if not w.startswith("b31-ood") else w.split("-")[2]
            fam_diffs[fam].append(loss_by_method[ma][w] - loss_by_method[mb][w])
        strat = {k: round(sum(v) / len(v), 4) for k, v in sorted(fam_diffs.items())}
        pairs.append({
            "comparison": pid, "method_a": ma, "method_b": mb,
            "status": "evaluated",
            "n_worlds": len(diffs),
            "mean_diff_a_minus_b": round(mean_diff, 4),
            "ci95_low": lo, "ci95_high": hi,
            "stratified_by_family": strat,
        })

    with open(OUT / "paired_comparisons.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["comparison", "method_a", "method_b", "status",
                         "n_worlds", "mean_diff_a_minus_b", "ci95_low", "ci95_high"])
        for p in pairs:
            writer.writerow([p["comparison"], p["method_a"], p["method_b"],
                             p["status"], p.get("n_worlds", ""),
                             p.get("mean_diff_a_minus_b", ""),
                             p.get("ci95_low", ""), p.get("ci95_high", "")])
    print("wrote paired_comparisons.csv")
    for p in pairs:
        if p["status"] == "evaluated":
            print(f'{p["comparison"]} {p["method_a"]} vs {p["method_b"]}: '
                  f'diff={p["mean_diff_a_minus_b"]} CI95=[{p["ci95_low"]},{p["ci95_high"]}]')
        else:
            print(f'{p["comparison"]} {p["method_a"]} vs {p["method_b"]}: {p["status"]}')


if __name__ == "__main__":
    main()
