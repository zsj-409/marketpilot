"""Evaluation hardening v2.1: behavioral equivalence diagnosis (Task 3).

Compares action sequences of Fixed / MissingEvidence / Uncertainty /
ContextualHybrid / AdaptiveVOI on Generation DEV worlds:
- facet acquisition order
- candidate research order
- stop position
- actual cost
- outcome
- sequence overlap (Jaccard on action tuples)
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from generate_benchmark_v31 import ID_FAMILIES, SEED_DEV

from marketpilot.evaluation.outcomes import classify_outcome
from marketpilot.input.spec import WorldSplit
from marketpilot.optimization.dream_rsi import ParameterizedPolicy
from marketpilot.world.core import AgentWorldView, WorldOracle
from marketpilot.world.generator import generate_world

OUT = Path("artifacts/locked_eval_v2")
FAMS = ["fixed", "missing-evidence", "uncertainty", "adaptive-voi", "contextual-hybrid"]


def _action_seq(result) -> list[tuple]:
    """(facet, target) tuples from the executed steps."""
    return [
        (s.facet.value if s.facet else "stop", s.target_id[:8] if s.target_id else "-")
        for s in result.steps
    ]


def main() -> None:
    rows = []
    for fam, spec in ID_FAMILIES.items():
        for seed in SEED_DEV:
            w = generate_world(spec, seed=seed, world_id=f"b31-{fam}-{seed}",
                               split=WorldSplit.DEV, family=fam)
            oracle = WorldOracle(w)
            seqs = {}
            for m in FAMS:
                view = AgentWorldView(w)
                pol = ParameterizedPolicy(strategy=m, name=m)
                r = pol.execute(view)
                seqs[m] = _action_seq(r)
                o = classify_outcome(r, oracle)
                rows.append({
                    "world_id": w.world_id, "family": fam, "method": m,
                    "n_actions": len(r.steps), "cost": round(r.total_cost, 2),
                    "outcome": o.outcome_status.value,
                    "reason": o.reason_code,
                })
    # Summary: per-method avg cost / actions / outcome distribution.
    with open(OUT / "behavioral_equivalence.csv", "w", newline="", encoding="utf-8") as f:
        wtr = csv.writer(f)
        wtr.writerow(["world_id", "family", "method", "n_actions", "cost",
                      "outcome", "reason"])
        for r in rows:
            wtr.writerow([r["world_id"], r["family"], r["method"], r["n_actions"],
                          r["cost"], r["outcome"], r["reason"]])
    print("wrote behavioral_equivalence.csv")
    print("\n=== per-method aggregates (DEV 160) ===")
    for m in FAMS:
        sub = [r for r in rows if r["method"] == m]
        costs = [r["cost"] for r in sub]
        actions = [r["n_actions"] for r in sub]

        oc = Counter(r["outcome"] for r in sub)
        print(f"{m:18s}: avg_cost={sum(costs)/len(costs):.2f} "
              f"avg_actions={sum(actions)/len(actions):.1f} "
              f"outcomes={dict(oc)}")
    # Cross-method action-sequence identity on a sample.
    print("\n=== action-sequence identity (balanced family, seed 100) ===")
    w = generate_world(ID_FAMILIES["balanced"], seed=100, world_id="b31-balanced-100",
                       split=WorldSplit.DEV, family="balanced")
    seqs = {}
    for m in FAMS:
        view = AgentWorldView(w)
        r = ParameterizedPolicy(strategy=m, name=m).execute(view)
        seqs[m] = _action_seq(r)
        print(f"{m:18s}: n={len(r.steps)} first3={seqs[m][:3]} cost={r.total_cost}")
    # Jaccard similarity between pairs.
    print("\n=== pairwise sequence Jaccard (balanced-100) ===")
    for i, a in enumerate(FAMS):
        for b in FAMS[i + 1:]:
            sa, sb = set(seqs[a]), set(seqs[b])
            j = len(sa & sb) / len(sa | sb) if (sa | sb) else 1.0
            print(f"  {a} vs {b}: Jaccard={j:.2f} | {a}-only={len(sa-sb)} "
                  f"{b}-only={len(sb-sa)}")


if __name__ == "__main__":
    main()
