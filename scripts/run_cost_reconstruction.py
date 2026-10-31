"""Final Results Integrity Audit: cost reconstruction from real actions
(Task 3).

Re-runs each frozen policy on TEST/OOD worlds and records EVERY executed
action (facet, product, per-action cost) to independently recompute
Cost per Valid = Sum(Executed Action Cost) / Valid GO Count.

Also checks the budget invariant: spent + next_action_cost <= budget.
Outputs to artifacts/locked_eval_audit/cost_recomputed_from_actions.csv.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from generate_benchmark_v31 import ID_FAMILIES, OOD_FAMILIES, SEED_OOD, SEED_TEST

from marketpilot.evaluation.outcomes import classify_outcome
from marketpilot.input.spec import WorldSplit
from marketpilot.optimization.dream_rsi import ParameterizedPolicy
from marketpilot.world.core import AgentWorldView, WorldOracle
from marketpilot.world.generator import generate_world

OUT = Path("artifacts/locked_eval_audit")
STATIC = ["fixed", "missing-evidence", "uncertainty", "adaptive-voi", "contextual-hybrid"]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    worlds = []
    for fam, spec in ID_FAMILIES.items():
        for seed in SEED_TEST:
            worlds.append(generate_world(
                spec, seed=seed, world_id=f"b31-{fam}-{seed}",
                split=WorldSplit.TEST, family=fam))
    for fam, spec in OOD_FAMILIES.items():
        for seed in SEED_OOD:
            worlds.append(generate_world(
                spec, seed=seed, world_id=f"b31-{fam}-{seed}",
                split=WorldSplit.TEST, family=fam))

    rows = []
    budget_violations = []
    for w in worlds:
        oracle = WorldOracle(w)
        budget = w.research_budget or 12.0
        for fam in STATIC:
            view = AgentWorldView(w)
            pol = ParameterizedPolicy(strategy=fam, name=fam)
            result = pol.execute(view)
            # Reconstruct executed actions from result.steps.
            step_costs = [s.cost for s in result.steps]
            total = sum(step_costs)
            # Budget invariant: each step must satisfy spent+next<=budget.
            spent = 0.0
            for c in step_costs:
                if spent + c > budget + 1e-9:
                    budget_violations.append({
                        "world_id": w.world_id, "method": fam,
                        "spent": round(spent, 3), "next_cost": c, "budget": budget,
                    })
                spent += c
            o = classify_outcome(result, oracle)
            rows.append({
                "world_id": w.world_id,
                "split": "ood" if w.world_id.startswith("b31-ood") else "test",
                "method": fam,
                "n_actions": len(step_costs),
                "sum_step_costs": round(total, 4),
                "result_total_cost": round(result.total_cost, 4),
                "budget": budget,
                "outcome": o.outcome_status.value,
                "valid_go": o.outcome_status.value == "valid_go",
                "evidence_sufficient": o.evidence_sufficient,
            })

    with open(OUT / "cost_recomputed_from_actions.csv", "w", newline="", encoding="utf-8") as f:
        wtr = csv.writer(f)
        wtr.writerow(["world_id", "split", "method", "n_actions", "sum_step_costs",
                      "result_total_cost", "budget", "outcome", "valid_go",
                      "evidence_sufficient"])
        for r in rows:
            wtr.writerow([r["world_id"], r["split"], r["method"], r["n_actions"],
                          r["sum_step_costs"], r["result_total_cost"], r["budget"],
                          r["outcome"], r["valid_go"], r["evidence_sufficient"]])

    # Cost per Valid (sum of action costs / valid count) — per split.
    print("=== Cost per Valid GO (recomputed from action costs) ===")
    for split in ["test", "ood"]:
        sub = [r for r in rows if r["split"] == split]
        for m in STATIC:
            ms = [r for r in sub if r["method"] == m]
            valid = sum(1 for r in ms if r["valid_go"])
            total_cost = sum(r["sum_step_costs"] for r in ms)
            cpv = total_cost / valid if valid else None
            print(f"{split} {m:18s}: valid={valid} total_cost={total_cost:.1f} "
                  f"cost/valid={cpv if cpv is None else round(cpv, 3)}")

    # Budget violations.
    print(f"\nbudget violations: {len(budget_violations)}")
    if budget_violations:
        for v in budget_violations[:5]:
            print(f"  {v['world_id']} {v['method']}: "
                  f"spent {v['spent']} + {v['next_cost']} > {v['budget']}")
        with open(OUT / "budget_violations.json", "w", encoding="utf-8") as f:
            import json

            json.dump(budget_violations, f, indent=2)


if __name__ == "__main__":
    main()
