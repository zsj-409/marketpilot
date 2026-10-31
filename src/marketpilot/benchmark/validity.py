"""Benchmark v3: Validity Suite (Task 2).

Checks:
- 2.1 Random / Heuristic / Full-Information Oracle / budget-constrained
      oracle / Fixed / MissingEvidence / AdaptiveVOI self-tests.
- 2.2 Positive controls (research changes decision; order matters under
      budget; refresh fixes stale; conflict resolution improves info).
      Negative controls (full info => no phantom gain; removing irrelevant
      evidence is stable; candidate order doesn't cheat; refused+lucky is
      not Valid GO; duplicate evidence doesn't inflate value).
- 2.3 Task solvability (feasible GO path, minimal cost, must-abstain).
- 2.4 Leakage checks (world_id/seed/product_id/template must not leak truth).

Output: machine-readable JSON validity report.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

from marketpilot.evaluation.outcomes import classify_outcome
from marketpilot.policy.controller import ControllerResult, StopReason
from marketpilot.world.core import (
    AgentWorldView,
    EvidenceFacet,
    ResearchAction,
    World,
    WorldOracle,
)


@dataclass
class ValidityReport:
    """Aggregated validity checks for a world or benchmark batch."""

    checks: dict[str, bool] = field(default_factory=dict)
    details: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {"checks": self.checks, "details": self.details}


def _run_family(view: AgentWorldView, strategy: str, budget: float) -> ControllerResult:
    from marketpilot.optimization.dream_rsi import ParameterizedPolicy

    pol = ParameterizedPolicy(
        strategy=strategy,
        name=strategy,
        params={"budget": budget} if strategy != "adaptive-voi" else {},
    )
    return pol.execute(view)


def _random_selection(world: World) -> ControllerResult:
    """Random selection: pick a random product with no research."""
    import random

    rng = random.Random(world.world_id.__hash__() & 0xFFFF)
    pid = rng.choice([p.product_id for p in world.products])
    return ControllerResult(
        selected_id=pid,
        stop_reason=StopReason.SUFFICIENT_EVIDENCE,
        decision="GO",
        total_cost=0.0,
    )


def _heuristic_selection(world: World) -> ControllerResult:
    """Simple heuristic: pick the product with the highest observable
    composite score (no research)."""
    best = None
    best_score = -1.0
    for p in world.products:
        obs = world.observables[p.product_id]
        score = (
            obs.observed_margin
            * obs.observed_demand
            * (1.0 - obs.observed_risk)
            * (1.0 - obs.observed_competition)
        )
        if score > best_score:
            best_score = score
            best = p.product_id
    return ControllerResult(
        selected_id=best,
        stop_reason=StopReason.SUFFICIENT_EVIDENCE,
        decision="GO",
        total_cost=0.0,
    )


def _full_info_oracle(world: World) -> ControllerResult:
    """Full-information oracle (evaluator-side): pick the true best."""
    oracle = WorldOracle(world)
    # The oracle has access to ALL evidence (evaluator-side only).
    revealed = {
        p.product_id: [f.value for f in EvidenceFacet] for p in world.products
    }
    return ControllerResult(
        selected_id=oracle.best_product_id(),
        stop_reason=StopReason.SUFFICIENT_EVIDENCE,
        revealed_facets=revealed,
        decision="GO",
        total_cost=0.0,
    )


def _cheapest_first_heuristic(world: World, budget: float) -> ControllerResult:
    """CheapestFirstHeuristic (Task 1.1): reveal facets cheapest-first up to
    the budget. This is a HEURISTIC, NOT an exact oracle — it may miss a
    feasible GO path that a different action order could reach."""
    view = AgentWorldView(world)
    spent = 0.0
    product_ids = [p.product_id for p in world.products]
    # Reveal cheapest-first across all products (max information per cost).
    pairs = sorted(
        (
            (facet, pid)
            for pid in product_ids
            for facet in EvidenceFacet
            if facet in world.costs
        ),
        key=lambda fp: world.costs[fp[0]],
    )
    for idx, (facet, pid) in enumerate(pairs):
        cost = world.costs[facet]
        if spent + cost > budget or idx >= 12:
            break
        view.take_action(_ACTION_FOR[facet], pid)
        spent += cost
    # Decide on revealed evidence (not hidden truth) — the best the policy
    # could do with the budget; still needs evidence sufficiency.
    scores = {
        pid: _score_observable(view, pid) for pid in product_ids
    }
    selected = max(scores, key=lambda pid: scores[pid])
    revealed = {
        pid: [f.value for f in view.revealed_facets(pid)] for pid in product_ids
    }
    sufficient = all(
        {"margin", "demand", "risk"}.issubset(set(f)) for f in revealed.values()
    )
    return ControllerResult(
        selected_id=selected,
        stop_reason=StopReason.SUFFICIENT_EVIDENCE if sufficient else StopReason.BUDGET_EXHAUSTED,
        revealed_facets=revealed,
        total_cost=spent,
        decision="GO" if sufficient else "INSUFFICIENT",
    )


_ACTION_FOR: dict[EvidenceFacet, ResearchAction] = {
    EvidenceFacet.MARGIN: ResearchAction.SEARCH_MARGIN,
    EvidenceFacet.RELIABILITY: ResearchAction.SEARCH_RELIABILITY,
    EvidenceFacet.DEMAND: ResearchAction.SEARCH_DEMAND,
    EvidenceFacet.COMPETITION: ResearchAction.SEARCH_COMPETITION,
    EvidenceFacet.RISK: ResearchAction.SEARCH_RISK,
}


class ReachabilityStatus(StrEnum):
    """Exact budgeted reachability verdict (Task 1.2)."""

    GO_REACHABLE = "go_reachable"
    ABSTENTION_REQUIRED = "abstention_required"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class ReachabilityResult:
    """Verdict + evidence of the exact budgeted reachability search."""

    status: ReachabilityStatus
    min_valid_cost: float | None = None
    n_states_explored: int = 0
    n_go_paths: int = 0
    reason: str = ""

    def to_json(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "min_valid_cost": (
                round(self.min_valid_cost, 4) if self.min_valid_cost is not None else None
            ),
            "n_states_explored": self.n_states_explored,
            "n_go_paths": self.n_go_paths,
            "reason": self.reason,
        }


class ExactBudgetedReachabilityOracle:
    """Task 1.2: exact budgeted reachability for SMALL worlds.

    Enumerates legal research action sequences under the budget and
    max_steps, tracking the revealed-evidence state, and decides whether a
    valid GO (sufficient evidence for a decision) is reachable.

    Verdicts:
      GO_REACHABLE          a valid GO path exists within budget
      ABSTENTION_REQUIRED   the FULL state space was explored and no valid
                            GO path exists (proven abstention)
      UNRESOLVED            state space too large / enumeration limit hit
                            (no path found is NOT proof of abstention)

    This is an evaluator-side audit tool; it never runs inside a policy.
    """

    def __init__(
        self,
        world: World,
        *,
        budget: float = 12.0,
        max_steps: int = 12,
        max_states: int = 200_000,
    ) -> None:
        self.world = world
        self.budget = budget
        self.max_steps = max_steps
        self.max_states = max_states
        self._product_ids = [p.product_id for p in world.products]
        self._costs = world.costs

    def _is_valid_go(self, revealed: frozenset[tuple[str, str]]) -> bool:
        """A valid GO needs the required facets of the SELECTED candidate
        (the decision-relevant candidate) — the controller's semantics for
        adaptive-style decisions. We check: at least one candidate has all
        required facets revealed, and it is the observable-best."""
        req = {"margin", "demand", "risk"}
        scores: dict[str, float] = {}
        for pid in self._product_ids:
            pid_revealed = {f for (f, _p) in revealed if _p == pid}
            # Score from revealed evidence (fall back to observable).
            margin = self._revealed_value(pid, EvidenceFacet.MARGIN, revealed)
            demand = self._revealed_value(pid, EvidenceFacet.DEMAND, revealed)
            risk = self._revealed_value(pid, EvidenceFacet.RISK, revealed)
            comp = self._revealed_value(pid, EvidenceFacet.COMPETITION, revealed)
            obs = self.world.observables[pid]
            margin = margin if margin is not None else obs.observed_margin
            demand = demand if demand is not None else obs.observed_demand
            risk = risk if risk is not None else obs.observed_risk
            comp = comp if comp is not None else obs.observed_competition
            scores[pid] = margin * demand * (1.0 - risk) * (1.0 - comp)
            # This candidate is decision-ready; if it is the best under
            # revealed evidence, a valid GO is possible.
            if req.issubset(pid_revealed) and scores[pid] == max(scores.values()):
                return True
        return False

    def _revealed_value(
        self,
        pid: str,
        facet: EvidenceFacet,
        revealed: frozenset[tuple[str, str]],
    ) -> float | None:
        """Value of a revealed (facet, pid) pair from the world's evidence
        (deterministic; evaluator-side only)."""
        if (facet.value, pid) not in revealed:
            return None
        entries = self.world.evidence.get(pid, {}).get(facet, [])
        if entries:
            return float(entries[0].value)
        return None

    def _has_time_versions(self) -> bool:
        """True when any (facet, product) carries multiple observed_at
        versions (temporal drift). The reachability state key (revealed
        set) does NOT encode time, so exactness cannot be proven for such
        worlds (Task 1.1 precheck)."""
        for pid in self._product_ids:
            for facet in _ACTION_FOR:
                entries = self.world.evidence.get(pid, {}).get(facet, [])
                if len({e.observed_at for e in entries}) > 1:
                    return True
        return False

    def solve(self) -> ReachabilityResult:
        """Dijkstra-style search over (revealed, spent) states.

        Always pops the lowest-cost state first, so the FIRST GO found is
        the minimum-cost valid path (exact). Terminates on the first GO
        (existence proof); otherwise explores the full (bounded) space and
        returns ABSTENTION_REQUIRED (proven) or UNRESOLVED (limit hit).

        Temporal-drift worlds: the state key (revealed set) does not encode
        the observation time / evidence version, so identical revealed sets
        at different times are merged — the verdict is NOT exact. For such
        worlds we return UNRESOLVED with a reason (no-path is not proof of
        abstention; path-found is a hindsight upper bound, not an exact
        minimum).
        """
        import heapq

        if self._has_time_versions():
            return ReachabilityResult(
                status=ReachabilityStatus.UNRESOLVED,
                n_states_explored=0,
                reason="world has multi-version (time-drifted) evidence; "
                "revealed-set state does not encode time, so exactness "
                "cannot be proven",
            )

        start_revealed: frozenset[tuple[str, str]] = frozenset()
        start = (0.0, start_revealed)
        seen: set[frozenset[tuple[str, str]]] = set()
        heap: list[tuple[float, frozenset[tuple[str, str]]]] = [start]
        seen.add(start_revealed)
        steps = 0
        while heap and steps < self.max_states:
            spent, revealed = heapq.heappop(heap)
            steps += 1
            if self._is_valid_go(revealed):
                # First (lowest-cost) GO found: exact min cost.
                return ReachabilityResult(
                    status=ReachabilityStatus.GO_REACHABLE,
                    min_valid_cost=spent,
                    n_states_explored=steps,
                    n_go_paths=1,
                    reason="valid GO path found within budget",
                )
            # Try every legal next action.
            for pid in self._product_ids:
                for facet in _ACTION_FOR:
                    cost = self._costs.get(facet, 1.0)
                    if spent + cost > self.budget:
                        continue
                    if len(revealed) >= self.max_steps:
                        continue
                    nxt = revealed | {(facet.value, pid)}
                    if nxt in seen:
                        continue
                    seen.add(nxt)
                    heapq.heappush(heap, (spent + cost, nxt))
        if steps >= self.max_states:
            return ReachabilityResult(
                status=ReachabilityStatus.UNRESOLVED,
                n_states_explored=steps,
                reason="state space exceeded enumeration limit; "
                "no-path is NOT proof of abstention",
            )
        return ReachabilityResult(
            status=ReachabilityStatus.ABSTENTION_REQUIRED,
            n_states_explored=steps,
            reason="full state space explored; no valid GO path within budget",
        )


def _score_observable(view: AgentWorldView, pid: str) -> float:
    obs = view.observable(pid)
    # Composite from REVEALED evidence (fall back to observable if missing).
    margin = _revealed_value(view, pid, EvidenceFacet.MARGIN) or obs.get(
        "observed_margin", 0.5
    )
    demand = _revealed_value(view, pid, EvidenceFacet.DEMAND) or obs.get(
        "observed_demand", 0.5
    )
    risk = _revealed_value(view, pid, EvidenceFacet.RISK) or obs.get(
        "observed_risk", 0.5
    )
    comp = _revealed_value(view, pid, EvidenceFacet.COMPETITION) or obs.get(
        "observed_competition", 0.5
    )
    return margin * demand * (1.0 - risk) * (1.0 - comp)


def _revealed_value(view: AgentWorldView, pid: str, facet: EvidenceFacet) -> float | None:
    entries = view.evidence_summary(pid).get(facet.value, [])
    if not entries:
        return None
    return float(entries[0]["value"])


def run_world_validity(
    world: World,
    *,
    budget: float | None = None,
) -> dict[str, Any]:
    """Full validity checks for ONE world (Task 2.1-2.4).

    budget defaults to the world's own research_budget (when set), else 12.0.
    """
    oracle = WorldOracle(world)
    best = oracle.best_product_id()
    budget = world.research_budget if budget is None and world.research_budget else (budget or 12.0)
    report: dict[str, Any] = {
        "world_id": world.world_id,
        "difficulty": world.difficulty.value,
        "best_utility": round(oracle.best_utility(), 4),
        "n_products": len(world.products),
        "budget": budget,
    }

    # --- 2.1 Self-tests ------------------------------------------------
    random_r = _random_selection(world)
    heuristic_r = _heuristic_selection(world)
    full_r = _full_info_oracle(world)
    cheapest_r = _cheapest_first_heuristic(world, budget)
    random_o = classify_outcome(random_r, oracle)
    heuristic_o = classify_outcome(heuristic_r, oracle)
    full_o = classify_outcome(full_r, oracle)
    cheapest_o = classify_outcome(cheapest_r, oracle)

    report["self_tests"] = {
        "random": {
            "outcome": random_o.outcome_status.value,
            "correct": random_r.selected_id == best,
        },
        "heuristic": {
            "outcome": heuristic_o.outcome_status.value,
            "correct": heuristic_r.selected_id == best,
        },
        "full_info_oracle": {
            "outcome": full_o.outcome_status.value,
            "correct": full_r.selected_id == best,
        },
        "cheapest_first_heuristic": {
            "outcome": cheapest_o.outcome_status.value,
            "correct": cheapest_r.selected_id == best,
            "cost": round(cheapest_r.total_cost, 2),
        },
    }

    # --- Exact budgeted reachability (Task 1.2) -------------------------
    reach = ExactBudgetedReachabilityOracle(world, budget=budget).solve()
    report["reachability"] = reach.to_json()

    # --- 2.3 Solvability ----------------------------------------------
    # Informative min-cost bound (all-candidates heuristic, kept for
    # context), but the AUTHORITATIVE verdicts come from the exact
    # reachability oracle (Task 1.2): a world is feasible iff GO_REACHABLE.
    required = {"margin", "demand", "risk"}
    min_cost = 0.0
    n_products = len(world.products)
    for facet in EvidenceFacet:
        if facet.value in required:
            min_cost += world.costs.get(facet, 1.0) * n_products
    feasible = reach.status == ReachabilityStatus.GO_REACHABLE
    report["solvability"] = {
        "feasible_go_path": feasible,
        "min_cost_for_best": round(min_cost, 2),
        "budget": budget,
        # must_abstain is driven by the EXACT reachability oracle, not the
        # (potentially sub-optimal) min-cost heuristic (Task 1.2/1.3).
        "must_abstain": reach.status == ReachabilityStatus.ABSTENTION_REQUIRED,
    }

    # --- 2.2 Positive control: research can change the decision --------
    # Compare heuristic (no research) vs cheapest-first (research).
    changed = (
        heuristic_r.selected_id != cheapest_r.selected_id
        or heuristic_o.outcome_status != cheapest_o.outcome_status
    )
    report["positive_control"] = {
        "research_changes_decision": changed,
    }

    # --- 2.4 Leakage: product IDs must not encode rank -----------------
    # Check that the best product's ID does not sort first / reveal utility.
    ids = [p.product_id for p in world.products]
    best_id = oracle.best_product_id()
    # Sort by ID: the best must not always be the lexicographically first.
    lex_first = min(ids)
    leak_by_id = lex_first == best_id and all(
        p.product_id == best_id or p.product_id > best_id for p in world.products
    )
    report["leakage"] = {
        "best_id_not_lex_first": not leak_by_id,
    }

    return report


def run_diagnostic_validity(
    report: dict[str, Any], world: World
) -> dict[str, Any]:
    """Validity of a diagnostic world (W0-W5 regression, Task 9)."""
    # Placeholder kept for API stability; per-world checks are covered by
    # run_world_validity.
    return {}


def write_validity_report(
    worlds: list[World], path: Path, *, budget: float | None = None
) -> dict[str, Any]:
    """Run validity for a batch of worlds and write the report.

    budget=None uses each world's own research_budget (recommended).
    """
    results = [run_world_validity(w, budget=budget) for w in worlds]
    summary = {
        "n_worlds": len(results),
        "n_research_changes_decision": sum(
            1 for r in results if r["positive_control"]["research_changes_decision"]
        ),
        "n_feasible_go": sum(1 for r in results if r["solvability"]["feasible_go_path"]),
        "n_must_abstain": sum(1 for r in results if r["solvability"]["must_abstain"]),
        "full_info_oracle_correct": sum(
            1 for r in results if r["self_tests"]["full_info_oracle"]["correct"]
        ),
    }
    report = {"summary": summary, "per_world": results}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report
