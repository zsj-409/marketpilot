"""Benchmark v3 Pilot (Task 4): generate ~60 dev worlds across mechanism
families and parameter regions; run validity suite; report distribution.

Also demonstrates Task 5 split policy (family/mechanism-grouped, no
cross-partition market reuse).
"""

from __future__ import annotations

import json
from pathlib import Path

from marketpilot.benchmark.validity import (
    write_validity_report,
)
from marketpilot.world.core import WorldSplit
from marketpilot.world.generator import (
    WorldGenerationSpec,
    generate_world,
    world_config_hash,
)

OUT = Path("artifacts/benchmark_v3")


def _families() -> list[tuple[str, WorldGenerationSpec]]:
    """Mechanism families (Task 1.4): each changes real behavior."""
    return [
        ("conflict", WorldGenerationSpec(
            conflict_probability=0.6, source_reliability=0.6)),
        ("noisy", WorldGenerationSpec(
            evidence_noise_level=0.3, source_bias=0.1)),
        ("asym-cost", WorldGenerationSpec(
            action_cost_asymmetry=0.8, information_acquisition_cost=1.5)),
        ("redundant", WorldGenerationSpec(
            evidence_redundancy=3, conflict_probability=0.1)),
        ("drift", WorldGenerationSpec(
            temporal_drift=0.6, evidence_noise_level=0.1)),
        ("scarce", WorldGenerationSpec(
            evidence_missingness=0.4, research_budget=2.0)),
        ("multi-cand", WorldGenerationSpec(
            product_count=6, candidate_utility_gap=0.08)),
        ("strict", WorldGenerationSpec(
            market_constraint_difficulty=0.6, candidate_utility_gap=0.1)),
        ("cheap", WorldGenerationSpec(
            information_acquisition_cost=0.5, conflict_probability=0.3)),
        ("balanced", WorldGenerationSpec()),
    ]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    worlds: list = []
    manifest_rows: list[dict] = []
    families = _families()
    # 6 seeds x 10 families = 60 dev worlds (Pilot scale).
    seeds = [7, 8, 9, 10, 11, 12]
    for fam_name, spec in families:
        for seed in seeds:
            wid = f"pilot-{fam_name}-{seed}"
            w = generate_world(
                spec,
                seed=seed,
                world_id=wid,
                split=WorldSplit.DEV,
                family=fam_name,
            )
            worlds.append(w)
            manifest_rows.append(
                {
                    "world_id": wid,
                    "world_family": fam_name,
                    "generator_seed": seed,
                    "world_version": w.world_version,
                    "world_config_hash": world_config_hash(w),
                    "split": w.split.value,
                    "difficulty": w.difficulty.value,
                    "n_products": len(w.products),
                    "spec_hash": spec.spec_hash(),
                }
            )

    # Determinism re-check on a sample.
    w1 = worlds[0]
    w2 = generate_world(
        families[0][1], seed=seeds[0], world_id=w1.world_id, family=families[0][0]
    )
    deterministic = world_config_hash(w1) == world_config_hash(w2)

    # Validity suite (per-world research_budget is used automatically).
    validity = write_validity_report(worlds, OUT / "pilot_validity.json")

    # Pilot manifest.
    manifest = {
        "benchmark_version": "v3-pilot",
        "n_worlds": len(worlds),
        "deterministic_reproducible": deterministic,
        "generator_families": [f[0] for f in families],
        "seeds": seeds,
        "worlds": manifest_rows,
    }
    (OUT / "pilot_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Split-policy demonstration (Task 5): family-grouped partitions.
    split_plan = _split_plan(families)
    (OUT / "split_plan.json").write_text(
        json.dumps(split_plan, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("=== Benchmark v3 Pilot ===")
    print(f"worlds: {len(worlds)} | deterministic: {deterministic}")
    s = validity["summary"]
    print(f"research changes decision: {s['n_research_changes_decision']}/{s['n_worlds']}")
    print(f"feasible GO: {s['n_feasible_go']} | must abstain: {s['n_must_abstain']}")
    print(f"full-info oracle correct: {s['full_info_oracle_correct']}/{s['n_worlds']}")
    print("\nper-family difficulty:")
    from collections import Counter

    by_fam = Counter(r["world_id"].split("-")[1] for r in manifest_rows)
    for fam, count in sorted(by_fam.items()):
        print(f"  {fam}: {count}")


def _split_plan(families: list[tuple[str, WorldGenerationSpec]]) -> dict:
    """Task 5: family-grouped split — same family NEVER spans dev/test."""
    # 10 families: 6 -> Generation DEV, 2 -> Confirmation DEV, 2 -> TEST
    # (OOD uses unseen mechanism combos, defined later).
    dev_fams = [f[0] for f in families[:6]]
    conf_fams = [f[0] for f in families[6:8]]
    test_fams = [f[0] for f in families[8:10]]
    return {
        "generation_dev_families": dev_fams,
        "confirmation_dev_families": conf_fams,
        "heldout_test_families": test_fams,
        "ood_stress": "unseen mechanism combos (e.g. drift+conflict+asym-cost)",
        "rule": "same family never spans dev/test; markets are instance-unique",
    }


if __name__ == "__main__":
    main()
