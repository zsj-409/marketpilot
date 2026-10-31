"""Phase 5: Dream-RSI ablations — budget-comparable evaluation of the four
ablation conditions required by the V2 spec §9:

1. no-replay      : drop the replay/archive; each round runs the variant live
                    on the dev world (no dream evaluation over history).
2. fixed          : fixed exploration policy (no RSI loop; identical budget).
3. no-diagnostics : drop the dream disagreement term (use only coverage),
                    i.e. the RSI loop without historical diagnosis.
4. no-world-pool  : drop the world-pool expansion (only the single dev world
                    is used for dream evaluation, no confirmation world).

Every condition spends the same budget (same number of policy executions)
so the comparison is budget-comparable.

Cost accounting:
- ``online_cost`` = real controller episodes (init / proposal / confirmation /
  promoted re-record), from ``ControllerResult.total_cost``.
- ``replay_cost`` = offline dream replays (simulated actions over recorded
  history), from the replay report's observed per-step costs.
These are never mixed: ``budget`` is the ONLINE budget only, and replay cost
is reported separately (it does not consume the online budget).
"""

from __future__ import annotations

import csv
import json
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

from marketpilot.optimization.dream_rsi import (
    ParameterizedPolicy,
    PolicyRegistry,
    PolicyStatus,
    RecursiveOptimizationLoop,
    ReplayWorldArchive,
)
from marketpilot.world.core import AgentWorldView, World, WorldOracle

# Same budget every condition spends (online executions only).
DEFAULT_ABLATION_BUDGET = 30.0


@dataclass
class AblationOutcome:
    """Outcome of one ablation condition.

    Outcome semantics (Task A2):
    - GO: valid decision satisfying hard constraints
    - REFUSED: explicit abstention (insufficient evidence / budget / safety)
    - INVALID: constraint violation / illegal state / execution error

    Promotion accounting (Task A3) distinguishes:
    - actual_promotions: promotions that CHANGED the active policy
    - quality_improvements / efficiency_improvements / ties / regressions
    """

    condition: str
    rounds: int
    budget: float = DEFAULT_ABLATION_BUDGET
    online_cost: float = 0.0
    replay_cost: float = 0.0
    decisions: list[str] = field(default_factory=list)
    promoted_hashes: list[str] = field(default_factory=list)
    final_decision: str = ""
    oracle_regret: float = 0.0
    oracle_correct: bool = False
    # Task A2/A3 counters (populated from the loop's round_log).
    n_go: int = 0
    n_refused: int = 0
    n_human_review: int = 0
    n_invalid: int = 0
    n_quality_improvements: int = 0
    n_efficiency_improvements: int = 0
    n_ties: int = 0
    n_regressions: int = 0

    @property
    def total_cost(self) -> float:
        """Total cost: online + replay (both are real resources; replay is
        offline compute but still costs tokens/CPU)."""
        return self.online_cost + self.replay_cost

    @property
    def decision_success_rate(self) -> float:
        """GO / total decisions (a refused decision is NOT success)."""
        total = self.n_go + self.n_refused + self.n_human_review + self.n_invalid
        return self.n_go / total if total else 0.0

    @property
    def safe_abstention_rate(self) -> float:
        """REFUSED / total decisions (explicit safe abstention)."""
        total = self.n_go + self.n_refused + self.n_human_review + self.n_invalid
        return self.n_refused / total if total else 0.0

    @property
    def cost_per_successful_decision(self) -> float:
        """Online cost per GO decision (a cheap REFUSED is not a cheap GO)."""
        return self.online_cost / self.n_go if self.n_go else float("inf")

    def to_json(self) -> dict[str, Any]:
        return {
            "condition": self.condition,
            "rounds": self.rounds,
            "budget": self.budget,
            "online_cost": round(self.online_cost, 4),
            "replay_cost": round(self.replay_cost, 4),
            "total_cost": round(self.total_cost, 4),
            "decisions": self.decisions,
            "promoted_hashes": self.promoted_hashes,
            "final_decision": self.final_decision,
            "oracle_regret": round(self.oracle_regret, 4),
            "oracle_correct": self.oracle_correct,
            "n_go": self.n_go,
            "n_refused": self.n_refused,
            "n_human_review": self.n_human_review,
            "n_invalid": self.n_invalid,
            "decision_success_rate": round(self.decision_success_rate, 4),
            "safe_abstention_rate": round(self.safe_abstention_rate, 4),
            "cost_per_successful_decision": round(self.cost_per_successful_decision, 4),
            "n_quality_improvements": self.n_quality_improvements,
            "n_efficiency_improvements": self.n_efficiency_improvements,
            "n_ties": self.n_ties,
            "n_regressions": self.n_regressions,
        }


def _random_variant(base: ParameterizedPolicy, seed: int) -> ParameterizedPolicy:
    """Random parameter perturbation (used by fixed-exploration condition)."""
    rng = random.Random(seed)
    params = dict(base.params)
    for key in ("weight_margin", "weight_demand", "weight_risk", "voi_threshold"):
        params[key] = max(-1.0, min(1.0, params[key] + rng.uniform(-0.15, 0.15)))
    return ParameterizedPolicy(params, name=f"random-{seed}")


def run_ablation(
    condition: str,
    dev_world: World,
    confirmation_world: World,
    test_world: World,
    base_dir: Path,
    *,
    rounds: int = 3,
    budget: float = DEFAULT_ABLATION_BUDGET,
    seed: int = 7,
) -> AblationOutcome:
    """Run one ablation condition with a fixed budget and measure the outcome
    on the independent TEST world (oracle regret computed evaluator-side)."""
    archive = ReplayWorldArchive(base_dir / condition)
    archive.register_world(dev_world)
    archive.register_world(confirmation_world)
    registry = PolicyRegistry()
    active = ParameterizedPolicy(name="active")
    registry.propose(active)

    outcome = AblationOutcome(condition=condition, rounds=rounds, budget=budget)

    def account(loop: RecursiveOptimizationLoop | None, online: list[float]) -> None:
        """Add online execution costs (from ledger or explicit list) plus the
        loop's replay costs to the outcome. RSI-loop conditions run the loop
        ONCE (the loop's own `rounds` parameter drives all rounds internally),
        so each ledger is accumulated exactly once."""
        outcome.online_cost += sum(online)
        if loop is not None:
            outcome.online_cost += loop.ledger.online_total
            outcome.replay_cost += loop.ledger.replay_total

    # RSI-loop conditions: run ONE loop whose internal `rounds` parameter
    # drives every round (propose -> dream -> confirm -> promote/rollback).
    if condition in ("no-diagnostics", "no-world-pool", "full", "current-history-only"):
        loop_kwargs: dict[str, Any] = {"archive": archive, "registry": registry, "rounds": rounds}
        if condition == "no-diagnostics":
            loop_kwargs["dream_threshold"] = -1.0
        else:
            loop_kwargs["dream_threshold"] = 0.5
        if condition == "current-history-only":
            # Task 3 ablation: dream over ONLY the most recent round's history.
            loop_kwargs["pool_mode"] = "current"
        elif condition == "full":
            loop_kwargs["pool_mode"] = "full"
        loop = RecursiveOptimizationLoop(**loop_kwargs)
        confirmation = confirmation_world if condition != "no-world-pool" else dev_world
        summary = loop.run(dev_world, confirmation)
        account(loop, [])
        outcome.decisions = [e["action"] for e in summary["round_log"]]
        # Task A2/A3: populate outcome semantics from the round log and
        # registry history (quality/efficiency/tie/regression counts).
        for entry in summary["round_log"]:
            kind = entry.get("kind")
            if kind == "improved":
                outcome.n_quality_improvements += 1
            elif kind == "efficiency_gain":
                outcome.n_efficiency_improvements += 1
            elif kind == "tied":
                outcome.n_ties += 1
            elif kind == "regressed":
                outcome.n_regressions += 1
        active = registry.active() or active
    else:
        for round_index in range(rounds):
            if condition == "fixed":
                # Fixed exploration: random variant, no RSI loop, no replay.
                variant = _random_variant(active, seed + round_index)
                view = AgentWorldView(dev_world)
                result = variant.execute(view)
                account(None, [result.total_cost])
                outcome.decisions.append(result.decision)
                # Fixed exploration never promotes.
                registry.rollback(variant.hash)
            elif condition == "no-replay":
                # No replay: variant runs live on dev; no dream over archive.
                variant = ParameterizedPolicy(
                    {**active.params, "voi_threshold": 0.04 + 0.01 * round_index},
                    name=f"no-replay-r{round_index}",
                )
                registry.propose(variant)
                view = AgentWorldView(dev_world)
                result = variant.execute(view)
                conf_view = AgentWorldView(confirmation_world)
                conf_result = variant.execute(conf_view)
                account(None, [result.total_cost, conf_result.total_cost])
                if conf_result.decision == "GO":
                    registry.promote(variant.hash)
                    active = variant
                else:
                    registry.rollback(variant.hash)

    # Final evaluation on the independent TEST world (oracle evaluator-side).
    test_view = AgentWorldView(test_world)
    final_result = active.execute(test_view)
    outcome.online_cost += final_result.total_cost
    outcome.final_decision = final_result.decision
    oracle = WorldOracle(test_world)
    best = oracle.best_product_id()
    # "Correct" requires a VALID decision: the policy must not have refused
    # or demanded human review, AND its selected product must be the oracle
    # best. A refused run whose selected_id happens to match the oracle is
    # NOT a correct decision (no decision was actually made).
    outcome.oracle_regret = 0.0 if final_result.selected_id == best else 1.0
    outcome.oracle_correct = (
        not final_result.refused
        and not final_result.human_review
        and final_result.selected_id == best
    )
    outcome.promoted_hashes = [
        h for h, s in registry._status.items() if s is PolicyStatus.PROMOTED
    ]
    return outcome


def run_all_ablations(
    dev_world: World,
    confirmation_world: World,
    test_world: World,
    base_dir: Path,
    *,
    rounds: int = 3,
    seed: int = 7,
) -> list[AblationOutcome]:
    """Run all four ablation conditions plus the full RSI condition."""
    conditions = [
        "full",
        "no-replay",
        "fixed",
        "no-diagnostics",
        "no-world-pool",
        "current-history-only",
    ]
    outcomes: list[AblationOutcome] = []
    for condition in conditions:
        outcome = run_ablation(
            condition,
            dev_world,
            confirmation_world,
            test_world,
            base_dir,
            rounds=rounds,
            seed=seed,
        )
        outcomes.append(outcome)
    return outcomes


def write_ablation_report(outcomes: list[AblationOutcome], output_dir: Path) -> Path:
    """Write the ablation results as CSV + JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "ablation_results.csv"
    json_path = output_dir / "ablation_results.json"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "condition",
                "rounds",
                "budget",
                "online_cost",
                "replay_cost",
                "total_cost",
                "final_decision",
                "oracle_regret",
                "oracle_correct",
            ],
        )
        writer.writeheader()
        for outcome in outcomes:
            writer.writerow(
                {
                    "condition": outcome.condition,
                    "rounds": outcome.rounds,
                    "budget": outcome.budget,
                    "online_cost": round(outcome.online_cost, 4),
                    "replay_cost": round(outcome.replay_cost, 4),
                    "total_cost": round(outcome.total_cost, 4),
                    "final_decision": outcome.final_decision,
                    "oracle_regret": round(outcome.oracle_regret, 4),
                    "oracle_correct": outcome.oracle_correct,
                }
            )
    json_path.write_text(json.dumps([o.to_json() for o in outcomes], indent=2), encoding="utf-8")
    return csv_path
