"""Final Locked Evaluation: generate the 5 core figures (Task 8).

All figures from REAL evaluation data (per_world_metrics_v2.csv).
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path("artifacts/locked_eval_v2")
FIG = OUT / "figures"


def _load() -> list[dict]:
    with open(OUT / "per_world_metrics_v2.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    data = _load()
    methods = [
        "random", "heuristic", "cheapest_first", "fixed", "missing-evidence",
        "uncertainty", "adaptive-voi", "contextual-hybrid", "full_info",
    ]
    is_ood = [r["world_id"].startswith("b31-ood") for r in data]

    # --- 1. task_success_by_difficulty.png ------------------------------
    plt.figure(figsize=(8, 5))
    # Difficulty is not recorded per-row in the CSV; aggregate TEST loss.
    for m in ["fixed", "missing-evidence", "adaptive-voi", "contextual-hybrid"]:
        losses = [
            float(r[f"{m}.task_loss"])
            for r, ood in zip(data, is_ood, strict=True)
            if not ood
        ]
        plt.bar([m], [sum(losses)], label=m)
    plt.title("Task Loss by Method (TEST, 120 worlds)")
    plt.ylabel("Total Task Loss")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG / "task_success_by_difficulty.png", dpi=120)
    plt.close()

    # --- 2. regret_vs_budget.png ---------------------------------------
    plt.figure(figsize=(8, 5))
    for m in ["fixed", "missing-evidence", "uncertainty", "adaptive-voi", "contextual-hybrid"]:
        pts = []
        for r, ood in zip(data, is_ood, strict=True):
            if ood:
                continue
            budget = float(r["budget"])
            regret = float(r[f"{m}.regret"]) if r[f"{m}.regret"] else 0.0
            pts.append((budget, regret))
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        plt.scatter(xs, ys, s=6, alpha=0.4, label=m)
    plt.xlabel("Research Budget (per-world)")
    plt.ylabel("Decision Regret")
    plt.title("Decision Regret vs Research Budget (TEST)")
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(FIG / "regret_vs_budget.png", dpi=120)
    plt.close()

    # --- 3. quality_cost_pareto.png -------------------------------------
    plt.figure(figsize=(8, 5))
    for m in methods:
        valid = sum(1 for r in data if not r["world_id"].startswith("b31-ood")
                    and r[f"{m}.outcome"] == "valid_go")
        cost = sum(float(r[f"{m}.cost"]) for r in data
                   if not r["world_id"].startswith("b31-ood"))
        plt.scatter(cost, valid, marker="o", s=60, label=m)
        plt.annotate(m, (cost, valid), textcoords="offset points", xytext=(6, 4), fontsize=7)
    plt.xlabel("Total Research Cost (TEST)")
    plt.ylabel("Valid GO Count")
    plt.title("Quality-Cost Pareto (TEST, 120 worlds)")
    plt.legend(fontsize=7, loc="lower right")
    plt.tight_layout()
    plt.savefig(FIG / "quality_cost_pareto.png", dpi=120)
    plt.close()

    # --- 4. rsi_vs_search_baselines.png --------------------------------
    # RSI optimization-efficiency comparison comes from the attribution
    # analysis (Phase 5.7/5.8 budget-matched runs); here we mark the
    # locked-task data as NOT_EVALUATED for the optimization comparison.
    plt.figure(figsize=(8, 5))
    plt.text(0.5, 0.5,
             "Full RSI vs Random Search / No-Replay / Current-Only\n"
             "optimization-efficiency comparison: see FINAL_RSI_ATTRIBUTION_REPORT\n"
             "(budget-matched Phase 5.7/5.8 runs; NOT_EVALUATED in locked task phase)",
             ha="center", va="center", fontsize=11)
    plt.axis("off")
    plt.title("RSI vs Search Baselines")
    plt.tight_layout()
    plt.savefig(FIG / "rsi_vs_search_baselines.png", dpi=120)
    plt.close()

    # --- 5. ood_robustness.png -----------------------------------------
    plt.figure(figsize=(8, 5))
    fams = ["fixed", "missing-evidence", "uncertainty", "adaptive-voi", "contextual-hybrid"]
    test_valid = [sum(1 for r in data if not r["world_id"].startswith("b31-ood")
                      and r[f"{m}.outcome"] == "valid_go") for m in fams]
    ood_valid = [sum(1 for r in data if r["world_id"].startswith("b31-ood")
                     and r[f"{m}.outcome"] == "valid_go") for m in fams]
    x = range(len(fams))
    plt.bar([i - 0.2 for i in x], [v / 120 for v in test_valid], width=0.4, label="ID TEST (120)")
    plt.bar([i + 0.2 for i in x], [v / 80 for v in ood_valid], width=0.4, label="OOD (80)")
    plt.xticks(list(x), fams, rotation=15)
    plt.ylabel("Valid GO Rate")
    plt.title("In-Distribution vs OOD Robustness")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG / "ood_robustness.png", dpi=120)
    plt.close()

    print("figures written to", FIG)


if __name__ == "__main__":
    main()
