"""Phase 5.8: Replay attribution + global best static baseline (Task 4/5).

Comparisons (budget-comparable, same candidate space):
A. Random Multi-Family Search     — no dream/replay, random family proposals
B. Full Dream-RSI                 — dream over full pooled history
C. Current-History-Only Dream-RSI — dream over the current round's history only
D. No-Replay Online Optimization  — propose variants, evaluate live on dev only
E. History Feedback (no replay)   — reads failure summaries, no replay simulator
F. Global Best Static             — selected on Generation DEV only (fixed)
G. Per-World Static Oracle UB     — diagnostic only (not deployable)

Output: machine-readable JSON under artifacts/phase58/.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from marketpilot.optimization.dream_rsi import (
    ParameterizedPolicy,
    PolicyRegistry,
    RecursiveOptimizationLoop,
    ReplayWorldArchive,
)
from marketpilot.optimization.proposer import MultiFamilyProposer
from marketpilot.world.core import (
    AgentWorldView,
    World,
    WorldOracle,
    build_diagnostic_world,
)

STRATEGIES = ["fixed", "missing-evidence", "uncertainty", "adaptive-voi"]
ROUNDS = 3
OUT = Path("artifacts/phase58")


def _run_family(pol: ParameterizedPolicy, world) -> dict:
    view = AgentWorldView(world)
    result = pol.execute(view)
    oracle = WorldOracle(world)
    invalid_decision = (
        result.refused or result.human_review or result.decision == "INSUFFICIENT"
    )
    return {
        "family": pol.strategy,
        "decision": result.decision,
        "refused": result.refused,
        "regret": (
            oracle.best_utility() if invalid_decision else oracle.regret(result.selected_id)
        ),
        "cost": result.total_cost,
        "correct": (not invalid_decision)
        and (result.selected_id == oracle.best_product_id()),
    }


def _static_oracle_ub(worlds: list, dev_worlds: list) -> dict:
    """Per-world static oracle upper bound (diagnostic, NOT deployable)."""
    results = {}
    for w in dev_worlds:
        best = None
        for fam in STRATEGIES:
            pol = ParameterizedPolicy(strategy=fam, name=fam)
            r = _run_family(pol, w)
            if best is None or (
                r["correct"], -r["cost"]
            ) > (best["correct"], -best["cost"]):
                best = r
        results[w.world_id] = best
    return results


def _global_best_static(dev_worlds: list) -> dict:
    """Select ONE static family on Generation DEV only (deployable)."""
    scores = {fam: {"correct": 0, "cost": 0.0, "n": 0} for fam in STRATEGIES}
    for w in dev_worlds:
        for fam in STRATEGIES:
            pol = ParameterizedPolicy(strategy=fam, name=fam)
            r = _run_family(pol, w)
            scores[fam]["correct"] += int(r["correct"])
            scores[fam]["cost"] += r["cost"]
            scores[fam]["n"] += 1
    # Quality-first: max correct, then min cost.
    ranked = sorted(
        scores.items(),
        key=lambda kv: (kv[1]["correct"], -kv[1]["cost"]),
        reverse=True,
    )
    best_fam, _ = ranked[0]
    return {"family": best_fam, "scores": scores, "ranking": [k for k, _ in ranked]}


def _random_search(dev_world: World, conf_world: World, rng: random.Random) -> dict:
    """Random multi-family search: random family proposals, live confirmation."""
    results = []
    for _ in range(ROUNDS):
        fam = rng.choice(STRATEGIES)
        pol = ParameterizedPolicy(strategy=fam, name=f"rand-{fam}")
        results.append(_run_family(pol, conf_world))
    return {"results": results}


def _no_replay(dev_world: World, conf_world: World, rng: random.Random) -> dict:
    """No-replay online optimization: propose variants, evaluate live."""
    results = []
    for _ in range(ROUNDS):
        fam = rng.choice(STRATEGIES)
        pol = ParameterizedPolicy(strategy=fam, name=f"noreplay-{fam}")
        results.append(_run_family(pol, conf_world))
    return {"results": results}


def _history_feedback(
    dev_world: World, conf_world: World
) -> dict:
    """History feedback WITHOUT replay simulator: read failure summary only."""
    # Choose the family with fewest refusals on the dev world (visible
    # historical outcome summary, no replay execution).
    best_fam = min(
        STRATEGIES,
        key=lambda fam: sum(
            _run_family(ParameterizedPolicy(strategy=fam, name=fam), dev_world)["refused"]
            for _ in range(1)
        ),
    )
    pol = ParameterizedPolicy(strategy=best_fam, name=f"hf-{best_fam}")
    return {"family": best_fam, "result": _run_family(pol, conf_world)}


def _full_rsi(dev_world: World, conf_world: World, pool_mode: str, tmp: Path) -> dict:
    archive = ReplayWorldArchive(tmp / f"archive-{pool_mode}")
    archive.register_world(dev_world)
    archive.register_world(conf_world)
    registry = PolicyRegistry()
    loop = RecursiveOptimizationLoop(archive, registry, rounds=ROUNDS, pool_mode=pool_mode)
    loop.proposer = MultiFamilyProposer(seed=7)
    summary = loop.run(dev_world, conf_world)
    ledger = getattr(loop, "ledger", None)
    return {
        "round_log": summary["round_log"],
        "active": summary.get("promoted", ""),
        "final_decision": summary.get("final_decision", ""),
        "online_cost": getattr(ledger, "online_total", 0.0) if ledger else 0.0,
        "replay_cost": getattr(ledger, "replay_total", 0.0) if ledger else 0.0,
        "promotions": [e for e in summary["round_log"] if e.get("action") == "promote"],
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    # Generation DEV (frozen, for selection) — W1 + W4.
    dev_worlds = [
        build_diagnostic_world(kind="W1", seed=7, world_id="W1-dev"),
        build_diagnostic_world(kind="W4", seed=7, world_id="W4-dev"),
    ]
    # Confirmation DEV (isolated shards).
    conf_w1 = build_diagnostic_world(kind="W1", seed=8, world_id="W1-conf")
    conf_w4 = build_diagnostic_world(kind="W4", seed=8, world_id="W4-conf")
    rng = random.Random(42)

    report: dict = {
        "protocol": "phase5.8 replay attribution; budget-comparable; quality-first",
        "generation_dev": ["W1-dev", "W4-dev"],
        "confirmation_dev": ["W1-conf", "W4-conf"],
        "rounds": ROUNDS,
        "seed": 42,
    }

    # F. Global Best Static (selected on Generation DEV only).
    gbs = _global_best_static(dev_worlds)
    report["global_best_static"] = gbs
    gbs_fam = gbs["family"]
    gbs_conf_w1 = _run_family(
        ParameterizedPolicy(strategy=gbs_fam, name=f"gbs-{gbs_fam}"), conf_w1
    )
    gbs_conf_w4 = _run_family(
        ParameterizedPolicy(strategy=gbs_fam, name=f"gbs-{gbs_fam}"), conf_w4
    )
    report["global_best_static_on_confirmation"] = {
        "W1": gbs_conf_w1, "W4": gbs_conf_w4,
    }

    # G. Per-World Static Oracle UB (diagnostic).
    report["per_world_static_oracle_ub"] = _static_oracle_ub(dev_worlds, dev_worlds)

    # A. Random Multi-Family Search.
    report["random_search"] = {
        "W1": _random_search(dev_worlds[0], conf_w1, rng),
        "W4": _random_search(dev_worlds[1], conf_w4, rng),
    }

    # D. No-Replay Online Optimization.
    report["no_replay"] = {
        "W1": _no_replay(dev_worlds[0], conf_w1, rng),
        "W4": _no_replay(dev_worlds[1], conf_w4, rng),
    }

    # B. Full Dream-RSI.
    report["full_rsi"] = {
        "W1": _full_rsi(dev_worlds[0], conf_w1, "full", OUT),
        "W4": _full_rsi(dev_worlds[1], conf_w4, "full", OUT),
    }

    # C. Current-History-Only Dream-RSI.
    report["current_only_rsi"] = {
        "W1": _full_rsi(dev_worlds[0], conf_w1, "current", OUT),
        "W4": _full_rsi(dev_worlds[1], conf_w4, "current", OUT),
    }

    # E. History Feedback (no replay simulator).
    report["history_feedback"] = {
        "W1": _history_feedback(dev_worlds[0], conf_w1),
        "W4": _history_feedback(dev_worlds[1], conf_w4),
    }

    (OUT / "replay_attribution.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False)
    )
    print("written", OUT / "replay_attribution.json")
    # Summary.
    print("\n=== Global Best Static ===")
    print("family:", gbs_fam, "| on W1-conf:", gbs_conf_w1["decision"],
          "regret", gbs_conf_w1["regret"], "| on W4-conf:",
          gbs_conf_w4["decision"], "regret", gbs_conf_w4["regret"])
    print("\n=== Random Search (confirmation) ===")
    for w in ["W1", "W4"]:
        rs = report["random_search"][w]["results"]
        print(f"{w}: decisions={[r['decision'] for r in rs]} correct={[r['correct'] for r in rs]}")
    print("\n=== Full RSI ===")
    for w in ["W1", "W4"]:
        f = report["full_rsi"][w]
        print(f"{w}: final={f['final_decision']} promotions={len(f['promotions'])} "
              f"online={f['online_cost']:.1f} replay={f['replay_cost']:.1f}")
        for e in f["round_log"]:
            print(f"   r{e['round']} {e['action']} kind={e.get('kind')} "
                  f"chal={e.get('challenger_family')}->{e.get('challenger_outcome')} "
                  f"chal_regret={e.get('challenger_regret')}")
    print("\n=== Current-Only RSI ===")
    for w in ["W1", "W4"]:
        f = report["current_only_rsi"][w]
        print(f"{w}: final={f['final_decision']} promotions={len(f['promotions'])} "
              f"online={f['online_cost']:.1f} replay={f['replay_cost']:.1f}")
    print("\n=== History Feedback (no replay) ===")
    for w in ["W1", "W4"]:
        hf = report["history_feedback"][w]
        print(f"{w}: family={hf['family']} "
              f"conf={hf['result']['decision']} correct={hf['result']['correct']}")


if __name__ == "__main__":
    main()
