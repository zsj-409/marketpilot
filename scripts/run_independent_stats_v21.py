"""Independent Replication v2.1: paired statistics (Task 8).

World-level paired differences of task_loss_v21, stratified bootstrap.
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

OUT = Path("artifacts/locked_eval_v21")
STATIC = ["fixed", "missing-evidence", "uncertainty", "adaptive-voi",
          "contextual-hybrid"]


def _bootstrap_ci(diffs: list[float], n_iter: int = 2000, seed: int = 42) -> tuple:
    rng = random.Random(seed)
    n = len(diffs)
    means = []
    for _ in range(n_iter):
        sample = [diffs[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    return round(means[int(0.025 * n_iter)], 4), round(means[int(0.975 * n_iter)], 4)


def main() -> None:
    with open(OUT / "per_world_metrics_v21.csv", encoding="utf-8") as f:
        data = list(csv.DictReader(f))
    loss = {}
    for m in STATIC:
        loss[m] = {r["world_id"]: float(r[f"{m}.task_loss_v21"]) for r in data}

    # Primary comparisons (paired, world-level).
    comparisons = [
        ("adaptive_vs_fixed", "adaptive-voi", "fixed"),
        ("contextual_vs_fixed", "contextual-hybrid", "fixed"),
        ("uncertainty_vs_fixed", "uncertainty", "fixed"),
    ]
    rows_out = []
    for cid, ma, mb in comparisons:
        for split, is_ood in [("test", False), ("ood", True), ("pooled", None)]:
            if is_ood is None:
                wids = [r["world_id"] for r in data]
            else:
                wids = [r["world_id"] for r in data
                        if r["world_id"].startswith("v21-ood") == is_ood]
            diffs = [loss[ma][w] - loss[mb][w] for w in wids]
            mean = sum(diffs) / len(diffs)
            lo, hi = _bootstrap_ci(diffs)
            rows_out.append({
                "comparison": cid, "method_a": ma, "method_b": mb,
                "split": split, "n": len(diffs),
                "mean_diff_a_minus_b": round(mean, 4),
                "ci95_low": lo, "ci95_high": hi,
            })
    with open(OUT / "paired_comparisons_v21.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["comparison", "method_a", "method_b", "split", "n",
                    "mean_diff_a_minus_b", "ci95_low", "ci95_high"])
        for r in rows_out:
            w.writerow([r["comparison"], r["method_a"], r["method_b"],
                        r["split"], r["n"], r["mean_diff_a_minus_b"],
                        r["ci95_low"], r["ci95_high"]])
    print("wrote paired_comparisons_v21.csv")
    for r in rows_out:
        print(f'{r["comparison"]} [{r["split"]}]: '
              f'mean_diff={r["mean_diff_a_minus_b"]} CI95='
              f'[{r["ci95_low"]},{r["ci95_high"]}]')


if __name__ == "__main__":
    main()
