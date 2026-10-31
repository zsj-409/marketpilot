"""Benchmark v3.1: generate the 440-world frozen dataset (Task 6).

Splits (family-grouped, instance-unique):
- Generation DEV: 160  (10 ID families x 16 seeds)
- Confirmation DEV: 80 (10 ID families x 8 seeds, different seed range)
- Held-out TEST: 120   (10 ID families x 12 seeds, disjoint seed range)
- OOD Stress TEST: 80  (4 OOD mechanism combos x 20 seeds)

OOD combos (Task 5, pre-registered structural changes):
  O1 temporal drift + evidence conflict
  O2 hidden risk + asymmetric action cost
  O3 multi-candidate + entity ambiguity
  O4 source reliability shift + tool failure (high missingness)

Independence: each latent market instance (spec + seed) appears in exactly
one split; hidden truths are never renamed across partitions.
"""

from __future__ import annotations

import json
from pathlib import Path

from marketpilot.benchmark.validity import (
    ExactBudgetedReachabilityOracle,
)
from marketpilot.input.spec import WorldSplit
from marketpilot.world.generator import (
    WorldGenerationSpec,
    generate_world,
    world_config_hash,
)
from marketpilot.world.manifest import BenchmarkManifest

OUT = Path("artifacts/benchmark_v3")

# 10 ID mechanism families (reuse Pilot families).
ID_FAMILIES: dict[str, WorldGenerationSpec] = {
    "conflict": WorldGenerationSpec(
        conflict_probability=0.6, source_reliability=0.6),
    "noisy": WorldGenerationSpec(
        evidence_noise_level=0.3, source_bias=0.1),
    "asym-cost": WorldGenerationSpec(
        action_cost_asymmetry=0.8, information_acquisition_cost=1.5),
    "redundant": WorldGenerationSpec(
        evidence_redundancy=3, conflict_probability=0.1),
    "drift": WorldGenerationSpec(
        temporal_drift=0.6, evidence_noise_level=0.1),
    "scarce": WorldGenerationSpec(
        evidence_missingness=0.4, research_budget=2.0),
    "multi-cand": WorldGenerationSpec(
        product_count=6, candidate_utility_gap=0.08),
    "strict": WorldGenerationSpec(
        market_constraint_difficulty=0.6, candidate_utility_gap=0.1),
    "cheap": WorldGenerationSpec(
        information_acquisition_cost=0.5, conflict_probability=0.3),
    "balanced": WorldGenerationSpec(),
}

# 4 OOD mechanism combos (pre-registered structural changes, Task 5).
OOD_FAMILIES: dict[str, WorldGenerationSpec] = {
    "ood-drift-conflict": WorldGenerationSpec(
        temporal_drift=0.5, conflict_probability=0.5,
        evidence_noise_level=0.2, source_reliability=0.5),
    "ood-risk-asym": WorldGenerationSpec(
        hidden_risk_strength=0.6, action_cost_asymmetry=0.9,
        information_acquisition_cost=1.8),
    "ood-multi-ambiguity": WorldGenerationSpec(
        product_count=8, candidate_utility_gap=0.05,
        evidence_noise_level=0.25, source_bias=0.15),
    "ood-src-toolfail": WorldGenerationSpec(
        source_reliability=0.4, evidence_missingness=0.5,
        conflict_probability=0.3, research_budget=8.0),
}

# Seed ranges: disjoint per split (instance-unique).
SEED_DEV = range(100, 116)       # 16
SEED_CONF = range(200, 208)      # 8
SEED_TEST = range(300, 312)      # 12
SEED_OOD = range(400, 420)       # 20


def _worlds_for(
    fam_name: str,
    spec: WorldGenerationSpec,
    seeds: range,
    split: WorldSplit,
) -> list:
    worlds = []
    for seed in seeds:
        wid = f"b31-{fam_name}-{seed}"
        worlds.append(
            generate_world(
                spec, seed=seed, world_id=wid, split=split, family=fam_name
            )
        )
    return worlds


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    all_worlds: list = []
    rows: list[dict] = []
    split_counts: dict[str, int] = {}

    # --- ID splits ------------------------------------------------------
    plans = [
        ("generation_dev", ID_FAMILIES, SEED_DEV, WorldSplit.DEV),
        ("confirmation_dev", ID_FAMILIES, SEED_CONF, WorldSplit.DEV),
        ("heldout_test", ID_FAMILIES, SEED_TEST, WorldSplit.TEST),
    ]
    for split_name, fams, seeds, split in plans:
        count = 0
        for fam, spec in fams.items():
            for w in _worlds_for(fam, spec, seeds, split):
                all_worlds.append(w)
                count += 1
                rows.append({
                    "world_id": w.world_id,
                    "world_family": fam,
                    "split": split_name,
                    "generator_seed": next(
                        s for s in seeds if f"-{s}" in w.world_id
                    ),
                    "world_hash": world_config_hash(w),
                    "spec_hash": spec.spec_hash(),
                    "difficulty": w.difficulty.value,
                })
        split_counts[split_name] = count

    # --- OOD split ------------------------------------------------------
    ood_count = 0
    for fam, spec in OOD_FAMILIES.items():
        for w in _worlds_for(fam, spec, SEED_OOD, WorldSplit.TEST):
            all_worlds.append(w)
            ood_count += 1
            rows.append({
                "world_id": w.world_id,
                "world_family": fam,
                "split": "ood_stress",
                "generator_seed": next(
                    s for s in SEED_OOD if f"-{s}" in w.world_id
                ),
                "world_hash": world_config_hash(w),
                "spec_hash": spec.spec_hash(),
                "difficulty": w.difficulty.value,
                "ood_combo": fam,
            })
    split_counts["ood_stress"] = ood_count

    total = sum(split_counts.values())
    print(f"generated {total} worlds:", split_counts)

    # --- Reachability + validity on a sample budget ----------------------
    # For exactness, run the reachability oracle on every world (it is fast
    # for small worlds). UNRESOLVED worlds are flagged, not faked.
    reach_stats = {"go_reachable": 0, "abstention_required": 0, "unresolved": 0}
    for w in all_worlds:
        budget = w.research_budget or 12.0
        r = ExactBudgetedReachabilityOracle(
            w, budget=budget, max_states=50_000
        ).solve()
        reach_stats[r.status.value] += 1
        # Annotate the row with the verdict.
        for row in rows:
            if row["world_id"] == w.world_id:
                row["reachability"] = r.status.value
                row["min_valid_cost"] = r.min_valid_cost
                break
    print("reachability:", reach_stats)

    # --- Manifest -------------------------------------------------------
    manifest = BenchmarkManifest(
        benchmark_version="v3.1",
        generator_version="0.2",
        evaluator_version="0.2",
        metric_contract_version="2.0",
        git_commit=(
            subprocess_git_hash()
        ),
        execution_mode="frozen",
        world_ids=[w.world_id for w in all_worlds],
        world_config_hashes={
            w.world_id: world_config_hash(w) for w in all_worlds
        },
        seed_registry={
            w.world_id: next(
                s for s in (
                    *SEED_DEV, *SEED_CONF, *SEED_TEST, *SEED_OOD
                ) if f"-{s}" in w.world_id
            )
            for w in all_worlds
        },
        research_budget=12.0,
    )
    manifest.save(OUT / "benchmark_v31_manifest.json")

    # --- Split manifest ------------------------------------------------
    split_manifest = {
        "benchmark_version": "v3.1",
        "metric_contract_version": "2.0",
        "split_counts": split_counts,
        "total": total,
        "id_families": list(ID_FAMILIES),
        "ood_combos": list(OOD_FAMILIES),
        "seed_ranges": {
            "generation_dev": list(SEED_DEV),
            "confirmation_dev": list(SEED_CONF),
            "heldout_test": list(SEED_TEST),
            "ood_stress": list(SEED_OOD),
        },
        "rows": rows,
        "reachability_stats": reach_stats,
        "dataset_split_hash": manifest.dataset_split_hash,
    }
    (OUT / "split_manifest_v31.json").write_text(
        json.dumps(split_manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("manifest written:", OUT / "benchmark_v31_manifest.json")
    print("split manifest written:", OUT / "split_manifest_v31.json")


def subprocess_git_hash() -> str:
    import subprocess

    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True
        )
        return out.stdout.strip()[:12]
    except Exception:
        return "unknown"


if __name__ == "__main__":
    main()
