"""Final Results Integrity Audit: remaining machine-readable outputs.

- split_specific_paired_differences.csv (Task 4)
- locked_method_coverage.csv (Task 7)
- metric_version_audit.json (Task 5/8)
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

OUT = Path("artifacts/locked_eval_audit")
V2 = Path("artifacts/locked_eval_v2")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with open(V2 / "per_world_metrics_v2.csv", encoding="utf-8") as f:
        data = list(csv.DictReader(f))

    # --- Task 4: split-specific paired differences -----------------------
    pairs = [("adaptive-voi", "fixed"), ("contextual-hybrid", "global_best_static")]
    gbs = "fixed"  # v2 frozen registry
    with open(OUT / "split_specific_paired_differences.csv",
              "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["comparison", "method_a", "method_b", "split",
                    "mean_diff_a_minus_b", "n_worlds"])
        for ma, mb in pairs:
            mb_actual = gbs if mb == "global_best_static" else mb
            for split, is_ood in [("test", False), ("ood", True)]:
                diffs = []
                for r in data:
                    if r["world_id"].startswith("b31-ood") != is_ood:
                        continue
                    diffs.append(
                        float(r[f"{ma}.task_loss"]) - float(r[f"{mb_actual}.task_loss"])
                    )
                mean = sum(diffs) / len(diffs) if diffs else None
                w.writerow([f"{ma}_vs_{mb}", ma, mb, split,
                            round(mean, 4) if mean is not None else "", len(diffs)])
    print("wrote split_specific_paired_differences.csv")

    # --- Task 7: method coverage ------------------------------------------
    methods_required = [
        "fixed", "missing-evidence", "uncertainty", "adaptive-voi",
        "contextual-hybrid", "global_best_static", "random_multi_family_search",
        "full_dream_rsi", "current_only_rsi", "no_replay_optimization",
    ]
    coverage = []
    for m in methods_required:
        if m in ["random_multi_family_search", "full_dream_rsi",
                 "current_only_rsi", "no_replay_optimization"]:
            coverage.append({
                "method": m,
                "per_world_metrics": "NO",
                "test_ood_executed": "NO",
                "note": "optimization-efficiency method; only W1/W4 historical ablation "
                        "(exploratory). NOT part of the frozen-policy task evaluation.",
            })
        elif m == "global_best_static":
            coverage.append({
                "method": m,
                "per_world_metrics": "YES (as gbs_family=fixed)",
                "test_ood_executed": "YES (identical to fixed: same policy hash)",
                "note": "selected on DEV; frozen registry v2 records family=fixed",
            })
        else:
            in_csv = any(f"{m}.outcome" in r for r in data)
            coverage.append({
                "method": m,
                "per_world_metrics": "YES" if in_csv else "NO",
                "test_ood_executed": "YES" if in_csv else "NO",
                "note": "frozen static policy",
            })
    with open(OUT / "locked_method_coverage.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["method", "per_world_metrics", "test_ood_executed", "note"])
        for c in coverage:
            w.writerow([c["method"], c["per_world_metrics"], c["test_ood_executed"], c["note"]])
    print("wrote locked_method_coverage.csv")

    # --- Task 5/8: metric version audit -----------------------------------
    audit = {
        "benchmark_version": "v3.1",
        "sealed_at_commit": "16c7e87",
        "sealed_reachability": {
            "go_reachable": 404, "abstention_required": 36, "unresolved": 0,
        },
        "post_precheck_reachability": {
            "go_reachable": 348, "abstention_required": 36, "unresolved": 56,
        },
        "reachability_change": {
            "cause": "Task 1.1 precheck: drift-family worlds carry multi-version "
                     "time evidence; revealed-set state does not encode time, so "
                     "exactness unproven -> UNRESOLVED",
            "timing": "BEFORE first locked test execution (precheck phase)",
            "protocol_amendment": "evaluation_plan.json v1.0 note covers UNRESOLVED handling",
        },
        "evaluator_versions": {
            "sealed": "0.2 (no _has_time_versions check)",
            "post_fix": "0.2 + _has_time_versions (working tree, unversioned)",
            "gap": "v2 run did not bump evaluator_version to 0.3 — recorded here",
        },
        "metric_contract": {
            "version": "2.0",
            "issue": "WRONG_GO with insufficient evidence is charged decision_regret "
                     "(~0.25) instead of an unsafe-recommendation penalty; this makes "
                     "abstention (cost 1.0) look worse than guessing. Requires v2.1 "
                     "contract revision (frozen BEFORE any new locked test).",
            "not_silently_changed": True,
        },
        "original_lock_test": {
            "commit": "2522aec",
            "status": "INVALIDATED",
            "cause": "shared AgentWorldView across methods -> evidence leakage, "
                     "zero-cost phantom GOs",
        },
        "v2_lock_test": {
            "status": "VALID (fresh view per method)",
            "output_dir": "artifacts/locked_eval_v2",
            "evaluator_version_note": "unversioned working-tree code; commit pending",
        },
    }
    (OUT / "metric_version_audit.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("wrote metric_version_audit.json")


if __name__ == "__main__":
    main()
