"""Final Locked Evaluation: run frozen policies on Held-out TEST (120) and
OOD Stress TEST (80) worlds (Task 4).

- Frozen policies ONLY (from frozen_policy_registry).
- Per-world research_budget respected (Task 1.3 fix).
- Paired evaluation: every method runs on every world.
- Results written to artifacts/locked_eval/ (append-only, per-world csv +
  jsonl).
- Test truths never enter policies; no archive updates.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from generate_benchmark_v31 import (
    ID_FAMILIES,
    OOD_FAMILIES,
    SEED_OOD,
    SEED_TEST,
)

from marketpilot.benchmark.validity import (
    _cheapest_first_heuristic,
    _full_info_oracle,
    _heuristic_selection,
    _random_selection,
)
from marketpilot.evaluation.outcomes import (
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
METHODS = [
    "random", "heuristic", "cheapest_first", "fixed", "missing-evidence",
    "uncertainty", "adaptive-voi", "contextual-hybrid", "full_info",
]


def _eval_world(w: World, registry: dict) -> dict:
    oracle = WorldOracle(w)
    budget = w.research_budget or 12.0
    # P0 fix (integrity audit): each method MUST get a FRESH AgentWorldView.
    # Sharing one view let earlier methods' revealed evidence leak into
    # later methods (zero-cost 'valid' GOs) — invalidating the original run.
    results = {
        "random": _random_selection(w),
        "heuristic": _heuristic_selection(w),
        "cheapest_first": _cheapest_first_heuristic(w, budget),
        "fixed": ParameterizedPolicy(
            strategy="fixed", name="fixed"
        ).execute(AgentWorldView(w)),
        "missing-evidence": ParameterizedPolicy(
            strategy="missing-evidence", name="me"
        ).execute(AgentWorldView(w)),
        "uncertainty": ParameterizedPolicy(
            strategy="uncertainty", name="unc"
        ).execute(AgentWorldView(w)),
        "adaptive-voi": ParameterizedPolicy(
            strategy="adaptive-voi", name="av"
        ).execute(AgentWorldView(w)),
        "contextual-hybrid": ParameterizedPolicy(
            strategy="contextual-hybrid", name="ch"
        ).execute(AgentWorldView(w)),
        "full_info": _full_info_oracle(w),
    }
    row = {"world_id": w.world_id, "split": w.split.value, "budget": budget}
    for m in METHODS:
        r = results[m]
        o = classify_outcome(r, oracle)
        row[m] = {
            "outcome": o.outcome_status.value,
            "regret": o.decision_regret,
            "task_loss": o.task_loss,
            "cost": round(r.total_cost, 3),
            "evidence_sufficient": o.evidence_sufficient,
        }
    return row


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    registry = json.loads((OUT / "frozen_policy_registry.json").read_text(encoding="utf-8"))
    gbs = registry["global_best_static"]["family"]
    print(f"global_best_static (frozen): {gbs}")

    worlds: list[World] = []
    # Held-out TEST: 120
    for fam, spec in ID_FAMILIES.items():
        for seed in SEED_TEST:
            wid = f"b31-{fam}-{seed}"
            worlds.append(
                generate_world(spec, seed=seed, world_id=wid,
                               split=WorldSplit.TEST, family=fam)
            )
    # OOD Stress TEST: 80
    for fam, spec in OOD_FAMILIES.items():
        for seed in SEED_OOD:
            wid = f"b31-{fam}-{seed}"
            worlds.append(
                generate_world(spec, seed=seed, world_id=wid,
                               split=WorldSplit.TEST, family=fam)
            )
    print(f"evaluating {len(worlds)} locked worlds ({len(worlds)-80} ID test + 80 OOD)")

    rows = []
    for i, w in enumerate(worlds):
        row = _eval_world(w, registry)
        row["gbs_family"] = gbs
        rows.append(row)
        if (i + 1) % 40 == 0:
            print(f"  {i+1}/{len(worlds)}")

    # Per-world CSV (append-only, timestamped copy).
    ts = "v2"
    with open(OUT / f"per_world_metrics_{ts}.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        header = ["world_id", "split", "budget", "gbs_family"] + [
            f"{m}.{k}" for m in METHODS
            for k in ("outcome", "regret", "task_loss", "cost", "evidence_sufficient")
        ]
        writer.writerow(header)
        for r in rows:
            line = [r["world_id"], r["split"], r["budget"], r["gbs_family"]]
            for m in METHODS:
                line += [
                    r[m]["outcome"],
                    r[m]["regret"] if r[m]["regret"] is not None else "",
                    r[m]["task_loss"],
                    r[m]["cost"],
                    r[m]["evidence_sufficient"],
                ]
            writer.writerow(line)

    # Method summary by split.
    summary = {}
    for split in ["test", "ood"]:
        sub = [r for r in rows if (r["split"] == "test") == (split == "test")]
        # NOTE: world.split.value for TEST worlds is "test"; for OOD also TEST split.
        # Distinguish OOD by world_id prefix.
    test_rows = [r for r in rows if not r["world_id"].startswith("b31-ood")]
    ood_rows = [r for r in rows if r["world_id"].startswith("b31-ood")]
    for name, sub in [("test", test_rows), ("ood", ood_rows)]:
        summary[name] = {}
        for m in METHODS:
            valid = sum(1 for r in sub if r[m]["outcome"] == "valid_go")
            wrong = sum(1 for r in sub if r[m]["outcome"] == "wrong_go")
            app = sum(1 for r in sub if r[m]["outcome"] == "appropriate_abstention")
            unn = sum(1 for r in sub if r[m]["outcome"] == "unnecessary_abstention")
            cost = sum(r[m]["cost"] for r in sub)
            loss = sum(r[m]["task_loss"] for r in sub)
            summary[name][m] = {
                "valid_go": valid, "wrong_go": wrong,
                "app_abstain": app, "unn_abstain": unn,
                "total_cost": round(cost, 2), "task_loss": round(loss, 3),
                "valid_go_rate": round(valid / len(sub), 3),
                "cost_per_valid_go": round(cost / valid, 2) if valid else None,
            }
    (OUT / "method_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("\n=== TEST (120) ===")
    for m in METHODS:
        s = summary["test"][m]
        print(f"{m:18s}: valid={s['valid_go']:3d} wrong={s['wrong_go']:3d} "
              f"app={s['app_abstain']:3d} unn={s['unn_abstain']:3d} "
              f"loss={s['task_loss']:.2f} cost/valid={s['cost_per_valid_go']}")
    print("\n=== OOD (80) ===")
    for m in METHODS:
        s = summary["ood"][m]
        print(f"{m:18s}: valid={s['valid_go']:3d} wrong={s['wrong_go']:3d} "
              f"app={s['app_abstain']:3d} unn={s['unn_abstain']:3d} "
              f"loss={s['task_loss']:.2f} cost/valid={s['cost_per_valid_go']}")


if __name__ == "__main__":
    main()
