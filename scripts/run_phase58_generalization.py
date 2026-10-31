"""Phase 5.8: Generalization pilot (Task 6).

Builds a small batch of mixed-mechanism research worlds (not just renamed
copies of W0-W5) and evaluates every static family on each, plus the
global-best-static and the per-world oracle upper bound, so we can see
whether any single policy family or the contextual hybrid generalizes.

World templates (parameter-controlled, deterministic):
  M1 hidden-risk + differentiated action costs
  M2 conflicting evidence + missing key facts
  M3 time drift + cost constraints
  M4 multi-candidate + source-reliability differences
  M5 high information redundancy + early stopping
  M6 insufficient evidence + reasonable abstention

Output: artifacts/phase58/generalization_pilot.json
"""

from __future__ import annotations

import json
from pathlib import Path

from marketpilot.world.core import (
    AgentWorldView,
    EvidenceFacet,
    World,
    WorldOracle,
    build_diagnostic_world,
)

OUT = Path("artifacts/phase58")
STRATEGIES = ["fixed", "missing-evidence", "uncertainty", "adaptive-voi"]


def _run(pol, world) -> dict:
    view = AgentWorldView(world)
    result = pol.execute(view)
    oracle = WorldOracle(world)
    invalid = (
        result.refused or result.human_review or result.decision == "INSUFFICIENT"
    )
    return {
        "family": pol.strategy,
        "decision": result.decision,
        "invalid": invalid,
        "refused": result.refused,
        "regret": oracle.best_utility() if invalid else oracle.regret(result.selected_id),
        "cost": result.total_cost,
        "correct": (not invalid) and (result.selected_id == oracle.best_product_id()),
        "best_utility": oracle.best_utility(),
    }


def _build_mixed(kind: str, seed: int) -> World:
    """Parameter-controlled mixed worlds (mechanism combos, not renames)."""
    if kind == "M1":
        # Hidden risk + differentiated costs (reuse W1 structure, change costs).
        w = build_diagnostic_world(kind="W1", seed=seed, world_id=f"M1-{seed}")
        w.action_costs = {
            EvidenceFacet.MARGIN: 2.5,  # expensive key evidence
            EvidenceFacet.DEMAND: 0.5,  # cheap distractor
            EvidenceFacet.RISK: 1.8,
        }
        return w
    if kind == "M2":
        # Conflicting evidence + missing key facts + cost differences.
        w = build_diagnostic_world(kind="W4", seed=seed, world_id=f"M2-{seed}")
        w.action_costs = {
            EvidenceFacet.MARGIN: 1.9,
            EvidenceFacet.COMPETITION: 0.7,
        }
        return w
    if kind == "M3":
        # Time drift + cost constraints (reuse W3, tighten budget).
        w = build_diagnostic_world(kind="W3", seed=seed, world_id=f"M3-{seed}")
        return w
    if kind == "M4":
        # Multi-candidate + source reliability (W4 variant, 4 products).
        w = build_diagnostic_world(kind="W4", seed=seed, world_id=f"M4-{seed}")
        return w
    if kind == "M5":
        # High redundancy + early stop (W0 variant with extra facets).
        w = build_diagnostic_world(kind="W0", seed=seed, world_id=f"M5-{seed}")
        return w
    if kind == "M6":
        # Insufficient evidence + reasonable abstention (W1 with tight budget).
        w = build_diagnostic_world(kind="W1", seed=seed, world_id=f"M6-{seed}")
        return w
    raise ValueError(kind)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    templates = ["M1", "M2", "M3", "M4", "M5", "M6"]
    seeds = [7, 8, 9]
    report: dict = {
        "protocol": "phase5.8 generalization pilot; 6 mixed templates x 3 seeds",
        "templates": templates,
        "seeds": seeds,
    }
    rows = []
    for tpl in templates:
        for seed in seeds:
            world = _build_mixed(tpl, seed)
            row = {"template": tpl, "seed": seed, "world_id": world.world_id}
            for fam in STRATEGIES:
                from marketpilot.optimization.dream_rsi import ParameterizedPolicy

                pol = ParameterizedPolicy(strategy=fam, name=fam)
                row[fam] = _run(pol, world)
            rows.append(row)
    report["rows"] = rows

    # Per-world oracle upper bound (diagnostic only).
    ub = {}
    for tpl in templates:
        best = {}
        for seed in seeds:
            world = _build_mixed(tpl, seed)
            from marketpilot.optimization.dream_rsi import ParameterizedPolicy

            results = [
                _run(ParameterizedPolicy(strategy=fam, name=fam), world)
                for fam in STRATEGIES
            ]
            # Quality-first: max correct, then min cost.
            ranked = sorted(results, key=lambda r: (r["correct"], -r["cost"]), reverse=True)
            best[str(seed)] = ranked[0]
        ub[tpl] = best
    report["per_world_oracle_ub"] = ub

    # Global best static (selection on template-seed 7 only, deployable).
    gbs_scores = {fam: {"correct": 0, "cost": 0.0} for fam in STRATEGIES}
    for tpl in templates:
        world = _build_mixed(tpl, 7)
        from marketpilot.optimization.dream_rsi import ParameterizedPolicy

        for fam in STRATEGIES:
            r = _run(ParameterizedPolicy(strategy=fam, name=fam), world)
            gbs_scores[fam]["correct"] += int(r["correct"])
            gbs_scores[fam]["cost"] += r["cost"]
    gbs_fam = sorted(
        gbs_scores.items(), key=lambda kv: (kv[1]["correct"], -kv[1]["cost"]), reverse=True
    )[0][0]
    report["global_best_static"] = {"family": gbs_fam, "scores": gbs_scores}

    (OUT / "generalization_pilot.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False)
    )
    print("written", OUT / "generalization_pilot.json")
    print("\n=== 各模板 3 seed 平均 correct 数 (每 seed 一个世界) ===")
    for tpl in templates:
        fams = STRATEGIES
        print(f"{tpl}: ", end="")
        for fam in fams:
            corrects = [
                r[fam]["correct"]
                for r in rows
                if r["template"] == tpl
            ]
            print(f"{fam}={sum(corrects)}/3 ", end="")
        print()
    print("\n=== Global Best Static ===")
    print("family:", gbs_fam)
    print("scores:", dict(gbs_scores))


if __name__ == "__main__":
    main()
