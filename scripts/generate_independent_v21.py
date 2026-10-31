"""Evaluation hardening v2.1: independent dataset generation (Task 5).

Fresh 120 ID worlds + 80 OOD worlds with NEW seeds (500-619 / 700-779),
never used in any prior split (v3.1 used 100-311, 400-419). Fresh hidden
product truths (new seeds => new RNG draws => new product attributes).
Manifest + hashes frozen BEFORE any evaluation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from generate_benchmark_v31 import ID_FAMILIES, OOD_FAMILIES

from marketpilot.input.spec import WorldSplit
from marketpilot.world.generator import (
    generate_world,
    world_config_hash,
)
from marketpilot.world.manifest import BenchmarkManifest

OUT = Path("artifacts/locked_eval_v21")
SEED_ID = range(500, 512)   # 12 seeds x 10 families = 120 ID worlds
SEED_OOD = range(700, 720)  # 20 seeds x 4 OOD combos = 80 OOD worlds


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    worlds = []
    rows = []
    for fam, spec in ID_FAMILIES.items():
        for seed in SEED_ID:
            wid = f"v21-{fam}-{seed}"
            w = generate_world(spec, seed=seed, world_id=wid,
                               split=WorldSplit.TEST, family=fam)
            worlds.append(w)
            rows.append({"world_id": wid, "family": fam, "split": "test",
                         "seed": seed, "world_hash": world_config_hash(w),
                         "spec_hash": spec.spec_hash()})
    for fam, spec in OOD_FAMILIES.items():
        for seed in SEED_OOD:
            wid = f"v21-{fam}-{seed}"
            w = generate_world(spec, seed=seed, world_id=wid,
                               split=WorldSplit.TEST, family=fam)
            worlds.append(w)
            rows.append({"world_id": wid, "family": fam, "split": "ood",
                         "seed": seed, "world_hash": world_config_hash(w),
                         "spec_hash": spec.spec_hash()})

    # Independence checks.
    hashes = [r["world_hash"] for r in rows]
    dup_hashes = len(hashes) - len(set(hashes))
    # No seed overlap with v3.1 splits (100-311, 400-419).
    prior_seeds = set(range(100, 312)) | set(range(400, 420))
    overlap = [r["seed"] for r in rows if r["seed"] in prior_seeds]

    manifest = BenchmarkManifest(
        benchmark_version="v2.1-independent",
        generator_version="0.2",
        evaluator_version="0.3",
        metric_contract_version="2.1",
        git_commit="(pending milestone A commit)",
        execution_mode="frozen-independent",
        world_ids=[w.world_id for w in worlds],
        world_config_hashes={w.world_id: world_config_hash(w) for w in worlds},
        seed_registry={
            row["world_id"]: row["seed"] for row in rows
        },
        research_budget=12.0,
    )
    manifest.save(OUT / "independent_dataset_manifest.json")
    dataset = {
        "version": "v2.1-independent",
        "n_id": 120, "n_ood": 80,
        "unique_world_hashes": len(set(hashes)),
        "duplicate_hashes": dup_hashes,
        "seed_overlap_with_prior_splits": overlap,
        "worlds": rows,
        "dataset_split_hash": manifest.dataset_split_hash,
    }
    (OUT / "independent_dataset.json").write_text(
        json.dumps(dataset, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"generated {len(worlds)} independent worlds "
          f"(120 ID + 80 OOD), duplicate hashes: {dup_hashes}, "
          f"seed overlap: {len(overlap)}")
    print("manifest:", OUT / "independent_dataset_manifest.json")


if __name__ == "__main__":
    main()
