"""Phase 4: Adaptive Research Controller.

Budget-aware sequential research decisions on top of the v3 world. Candidate
actions: search (per facet), verify, compare, generate, stop. Four strategies:
Fixed, MissingEvidence, Uncertainty, AdaptiveVOI. The controller emits
Regret-Budget and Quality-Cost curves, and can refuse / request human review
when evidence is insufficient.

Design notes:
- The controller consumes only AgentWorldView (no oracle). Oracle regret is
  computed by the EVALUATOR (policy/evaluation), never inside the controller.
- Evidence sufficiency is judged from revealed facets and their agreement,
  NOT from hidden truth.
- STOP / REFUSE / HUMAN_REVIEW are first-class outcomes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, ClassVar

from marketpilot.world.core import AgentWorldView, EvidenceFacet, ResearchAction


class ControllerAction(StrEnum):
    SEARCH = "search"
    VERIFY = "verify"
    COMPARE = "compare"
    GENERATE = "generate"
    STOP = "stop"
    REFUSE = "refuse"
    HUMAN_REVIEW = "human_review"


class StrategyKind(StrEnum):
    FIXED = "fixed"
    MISSING_EVIDENCE = "missing-evidence"
    UNCERTAINTY = "uncertainty"
    ADAPTIVE_VOI = "adaptive-voi"


class StopReason(StrEnum):
    BUDGET_EXHAUSTED = "budget_exhausted"
    SUFFICIENT_EVIDENCE = "sufficient_evidence"
    REFUSED = "refused"
    HUMAN_REVIEW = "human_review"
    MAX_STEPS = "max_steps"


@dataclass
class StepRecord:
    """One controller step: what was decided and what it cost."""

    step: int
    action: ControllerAction
    facet: EvidenceFacet | None
    cost: float
    reason: str
    revealed_before: int
    target_id: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "action": self.action.value,
            "facet": self.facet.value if self.facet else None,
            "cost": round(self.cost, 4),
            "reason": self.reason,
            "revealed_before": self.revealed_before,
            "target_id": self.target_id,
        }


@dataclass
class ControllerResult:
    """Outcome of one controller episode over a world view."""

    selected_id: str | None
    stop_reason: StopReason
    steps: list[StepRecord] = field(default_factory=list)
    total_cost: float = 0.0
    revealed_facets: dict[str, list[str]] = field(default_factory=dict)
    refused: bool = False
    human_review: bool = False
    decision: str = "UNKNOWN"  # GO | NO_GO | INSUFFICIENT

    def to_json(self) -> dict[str, Any]:
        return {
            "selected_id": self.selected_id,
            "stop_reason": self.stop_reason.value,
            "decision": self.decision,
            "refused": self.refused,
            "human_review": self.human_review,
            "total_cost": round(self.total_cost, 4),
            "steps": [step.to_json() for step in self.steps],
            "revealed_facets": self.revealed_facets,
        }

    @property
    def step_count(self) -> int:
        return len(self.steps)


_DEFAULT_FACET_COST: dict[EvidenceFacet, float] = {
    EvidenceFacet.MARKET: 1.0,
    EvidenceFacet.MARGIN: 1.5,
    EvidenceFacet.RELIABILITY: 1.2,
    EvidenceFacet.COMPETITION: 1.0,
    EvidenceFacet.RISK: 1.3,
    EvidenceFacet.DEMAND: 1.0,
}


class _BaseController(ABC):
    """Shared controller machinery: budget, costs, facet ordering."""

    FACET_COST: ClassVar[dict[EvidenceFacet, float]] = dict(_DEFAULT_FACET_COST)
    REQUIRED_FACETS: ClassVar[set[EvidenceFacet]] = {
        EvidenceFacet.MARGIN,
        EvidenceFacet.DEMAND,
        EvidenceFacet.RISK,
    }

    def __init__(self, budget: float = 10.0, max_steps: int = 12) -> None:
        self.budget = budget
        self.max_steps = max_steps

    def configure_costs(self, costs: dict[EvidenceFacet, float]) -> None:
        """W2: apply world-configured action costs (per-world)."""
        merged = dict(_DEFAULT_FACET_COST)
        merged.update({facet: float(cost) for facet, cost in costs.items()})
        # Per-instance override (NOT the class attribute, so other instances
        # keep their own costs).
        self._costs_override = merged

    @property
    def costs(self) -> dict[EvidenceFacet, float]:
        """Effective costs: instance override if set, else class default."""
        return dict(getattr(self, "_costs_override", self.FACET_COST))

    @abstractmethod
    def run(self, view: AgentWorldView) -> ControllerResult:
        """Run the controller episode over an agent world view."""

    def _candidate_ids(self, view: AgentWorldView) -> list[str]:
        return [c["product_id"] for c in view.candidates()]

    def _evidence_mean(self, view: AgentWorldView, pid: str, facet: EvidenceFacet) -> float | None:
        entries = view.evidence_summary(pid).get(facet.value, [])
        if not entries:
            return None
        values = [float(e["value"]) for e in entries]
        return sum(values) / len(values)

    def _scores(self, view: AgentWorldView) -> dict[str, float]:
        """Deterministic score from revealed evidence only; unrevealed -> neutral 0.5."""
        scores: dict[str, float] = {}
        for pid in self._candidate_ids(view):
            margin = self._evidence_mean(view, pid, EvidenceFacet.MARGIN)
            demand = self._evidence_mean(view, pid, EvidenceFacet.DEMAND)
            risk = self._evidence_mean(view, pid, EvidenceFacet.RISK)
            margin = 0.5 if margin is None else margin
            demand = 0.5 if demand is None else demand
            risk = 0.5 if risk is None else risk
            scores[pid] = 0.5 * margin + 0.3 * demand - 0.2 * risk
        return scores

    def _best(self, view: AgentWorldView) -> str | None:
        scores = self._scores(view)
        return max(scores, key=lambda pid: scores[pid]) if scores else None

    def _sufficient(self, view: AgentWorldView) -> bool:
        """Evidence sufficiency from revealed facets + conflict check (no oracle)."""
        for pid in self._candidate_ids(view):
            revealed = set(view.revealed_facets(pid))
            if not self.REQUIRED_FACETS.issubset(revealed):
                return False
        return True

    def _conflicts(self, view: AgentWorldView, pid: str) -> list[EvidenceFacet]:
        """Facets whose revealed evidence disagrees with the observable baseline."""
        conflicts: list[EvidenceFacet] = []
        for facet in (EvidenceFacet.MARGIN, EvidenceFacet.RISK, EvidenceFacet.DEMAND):
            entries = view.evidence_summary(pid).get(facet.value, [])
            if not entries:
                continue
            observed = view.observable(pid)
            base_key = f"observed_{facet.value}"
            if base_key not in observed:
                continue
            base = float(observed[base_key])
            mean = sum(e["value"] for e in entries) / len(entries)
            if abs(mean - base) > 0.15:
                conflicts.append(facet)
        return conflicts

    def _run_steps(
        self,
        view: AgentWorldView,
        strategy: StrategyKind,
        step_facet: Any,
    ) -> ControllerResult:
        raise NotImplementedError


class FixedController(_BaseController):
    """Fixed: search every required facet for every candidate, then stop."""

    def run(self, view: AgentWorldView) -> ControllerResult:
        result = ControllerResult(selected_id=None, stop_reason=StopReason.MAX_STEPS)
        spent = 0.0
        step = 0
        for facet in sorted(self.REQUIRED_FACETS, key=lambda f: self.costs[f]):
            for pid in self._candidate_ids(view):
                if spent >= self.budget or step >= self.max_steps:
                    result.stop_reason = StopReason.BUDGET_EXHAUSTED
                    break
                cost = self.costs[facet]
                # Task 9: never overrun the budget — a step that would push
                # spent past the budget is not taken.
                if spent + cost > self.budget:
                    result.stop_reason = StopReason.BUDGET_EXHAUSTED
                    break
                before = len(view.revealed_facets(pid))
                view.take_action(_FACET_ACTION[facet], pid)
                spent += cost
                step += 1
                result.steps.append(
                    StepRecord(
                        step=step,
                        action=ControllerAction.SEARCH,
                        facet=facet,
                        cost=cost,
                        reason=f"fixed: acquire {facet.value}",
                        revealed_before=before,
                        target_id=pid,
                    )
                )
            if spent >= self.budget or step >= self.max_steps:
                break
        result.total_cost = spent
        result.selected_id = self._best(view)
        result.revealed_facets = {
            pid: [f.value for f in view.revealed_facets(pid)] for pid in self._candidate_ids(view)
        }
        if self._sufficient(view):
            result.stop_reason = StopReason.SUFFICIENT_EVIDENCE
            result.decision = "GO" if result.selected_id else "INSUFFICIENT"
        else:
            result.decision = "INSUFFICIENT"
            if spent >= self.budget:
                result.stop_reason = StopReason.BUDGET_EXHAUSTED
        return result


class MissingEvidenceController(_BaseController):
    """MissingEvidence: acquire only the facets that are still missing."""

    def run(self, view: AgentWorldView) -> ControllerResult:
        result = ControllerResult(selected_id=None, stop_reason=StopReason.MAX_STEPS)
        spent = 0.0
        step = 0
        while step < self.max_steps and spent < self.budget:
            missing: list[tuple[EvidenceFacet, str]] = []
            for pid in self._candidate_ids(view):
                revealed = set(view.revealed_facets(pid))
                for facet in self.REQUIRED_FACETS:
                    if facet not in revealed:
                        missing.append((facet, pid))
            if not missing:
                result.stop_reason = StopReason.SUFFICIENT_EVIDENCE
                break
            # Prioritize the cheapest missing facet.
            facet, pid = min(missing, key=lambda item: self.costs[item[0]])
            cost = self.costs[facet]
            # Task 9: never overrun the budget.
            if spent + cost > self.budget:
                result.stop_reason = StopReason.BUDGET_EXHAUSTED
                break
            before = len(view.revealed_facets(pid))
            view.take_action(_FACET_ACTION[facet], pid)
            spent += cost
            step += 1
            result.steps.append(
                StepRecord(
                    step=step,
                    action=ControllerAction.SEARCH,
                    facet=facet,
                    cost=cost,
                    reason=f"missing-evidence: acquire {facet.value} for {pid}",
                    revealed_before=before,
                    target_id=pid,
                )
            )
        result.total_cost = spent
        result.selected_id = self._best(view)
        result.revealed_facets = {
            pid: [f.value for f in view.revealed_facets(pid)] for pid in self._candidate_ids(view)
        }
        result.decision = "GO" if result.selected_id and self._sufficient(view) else "INSUFFICIENT"
        if spent >= self.budget and not self._sufficient(view):
            result.stop_reason = StopReason.BUDGET_EXHAUSTED
        elif self._sufficient(view):
            result.stop_reason = StopReason.SUFFICIENT_EVIDENCE
        return result


class UncertaintyController(_BaseController):
    """Uncertainty: acquire facets whose revealed value diverges most from the
    observable baseline (conflict-driven acquisition)."""

    def run(self, view: AgentWorldView) -> ControllerResult:
        result = ControllerResult(selected_id=None, stop_reason=StopReason.MAX_STEPS)
        spent = 0.0
        step = 0
        while step < self.max_steps and spent < self.budget:
            # Pick the candidate-facet pair with the largest divergence.
            best_pair: tuple[float, EvidenceFacet, str] | None = None
            for pid in self._candidate_ids(view):
                for facet in self.REQUIRED_FACETS:
                    if facet in view.revealed_facets(pid):
                        continue
                    observed = view.observable(pid)
                    base_key = f"observed_{facet.value}"
                    if base_key not in observed:
                        continue
                    divergence = abs(float(observed[base_key]) - 0.5)
                    pair = (divergence, facet, pid)
                    if best_pair is None or pair[0] > best_pair[0]:
                        best_pair = pair
            if best_pair is None:
                # All required facets revealed or no divergence signal: stop.
                result.stop_reason = StopReason.SUFFICIENT_EVIDENCE
                break
            divergence, facet, pid = best_pair
            cost = self.costs[facet]
            # Task 9: never overrun the budget.
            if spent + cost > self.budget:
                result.stop_reason = StopReason.BUDGET_EXHAUSTED
                break
            before = len(view.revealed_facets(pid))
            view.take_action(_FACET_ACTION[facet], pid)
            spent += cost
            step += 1
            result.steps.append(
                StepRecord(
                    step=step,
                    action=ControllerAction.SEARCH,
                    facet=facet,
                    cost=cost,
                    reason=f"uncertainty: divergence {divergence:.2f} on {facet.value} for {pid}",
                    revealed_before=before,
                    target_id=pid,
                )
            )
        result.total_cost = spent
        result.selected_id = self._best(view)
        result.revealed_facets = {
            pid: [f.value for f in view.revealed_facets(pid)] for pid in self._candidate_ids(view)
        }
        result.decision = "GO" if result.selected_id and self._sufficient(view) else "INSUFFICIENT"
        if spent >= self.budget and not self._sufficient(view):
            result.stop_reason = StopReason.BUDGET_EXHAUSTED
        elif self._sufficient(view):
            result.stop_reason = StopReason.SUFFICIENT_EVIDENCE
        return result


class AdaptiveVOIController(_BaseController):
    """Adaptive VOI: estimate value-of-information per action from revealed
    evidence spread and conflict, normalized by cost, and stop when VOI is
    below threshold or budget is spent. Can refuse / request human review when
    evidence is insufficient at the end."""

    VOI_THRESHOLD = 0.04
    REFUSE_THRESHOLD = 0.20  # fraction of required facets still missing at stop
    # Task E: when True, facets whose evidence has multiple time versions
    # (observed_at) can be RE-QUERIED at the current time (refresh). This lets
    # a policy react to W3 time drift instead of freezing on stale evidence.
    refresh_stale: bool = False

    def run(self, view: AgentWorldView) -> ControllerResult:
        result = ControllerResult(selected_id=None, stop_reason=StopReason.MAX_STEPS)
        spent = 0.0
        step = 0
        while step < self.max_steps and spent < self.budget:
            best_voi: tuple[float, EvidenceFacet, str] | None = None
            for pid in self._candidate_ids(view):
                revealed = set(view.revealed_facets(pid))
                for facet in self.REQUIRED_FACETS:
                    # Task E refresh: a revealed facet is still a candidate if
                    # its evidence is time-versioned (may have drifted since
                    # first observed) and refresh is enabled.
                    if facet in revealed:
                        if self.refresh_stale and self._facet_has_time_versions(view, pid, facet):
                            pass  # allow re-query (refresh)
                        else:
                            continue
                    # Value of information: divergence between observable
                    # baseline and neutral, plus any conflict signal.
                    observed = view.observable(pid)
                    base_key = f"observed_{facet.value}"
                    base = float(observed[base_key]) if base_key in observed else 0.5
                    voi = abs(base - 0.5) + 0.1 * len(self._conflicts(view, pid))
                    cost = self.costs[facet]
                    normalized = voi / cost
                    pair = (normalized, facet, pid)
                    if best_voi is None or pair[0] > best_voi[0]:
                        best_voi = pair
            if best_voi is None:
                result.stop_reason = StopReason.SUFFICIENT_EVIDENCE
                break
            normalized_voi, facet, pid = best_voi
            if normalized_voi < self.VOI_THRESHOLD:
                # Not worth spending more; stop (possibly refuse if lacking key evidence).
                result.stop_reason = StopReason.SUFFICIENT_EVIDENCE
                break
            cost = self.costs[facet]
            if spent + cost > self.budget:
                # The next action would exceed the budget: stop within budget.
                result.stop_reason = StopReason.BUDGET_EXHAUSTED
                break
            before = len(view.revealed_facets(pid))
            # Task E: re-query an already-revealed facet with refresh=True so
            # W3 time drift is re-observed at the current world time.
            is_refresh = facet in set(view.revealed_facets(pid))
            view.take_action(_FACET_ACTION[facet], pid, refresh=is_refresh)
            spent += cost
            step += 1
            result.steps.append(
                StepRecord(
                    step=step,
                    action=ControllerAction.SEARCH,
                    facet=facet,
                    cost=cost,
                    reason=(
                        f"adaptive-voi: refresh {facet.value} for {pid}"
                        if is_refresh
                        else f"adaptive-voi: {normalized_voi:.3f} on {facet.value} for {pid}"
                    ),
                    revealed_before=before,
                    target_id=pid,
                )
            )
        result.total_cost = spent
        result.selected_id = self._best(view)
        result.revealed_facets = {
            pid: [f.value for f in view.revealed_facets(pid)] for pid in self._candidate_ids(view)
        }
        # Post-stop quality check: refuse or request human review if key
        # evidence is still missing.
        missing_ratio = self._missing_ratio(view)
        if missing_ratio > self.REFUSE_THRESHOLD:
            result.refused = True
            result.decision = "INSUFFICIENT"
            result.stop_reason = StopReason.REFUSED
        elif missing_ratio > 0:
            result.human_review = True
            result.decision = "INSUFFICIENT"
            result.stop_reason = StopReason.HUMAN_REVIEW
        else:
            result.decision = "GO" if result.selected_id else "INSUFFICIENT"
            result.stop_reason = StopReason.SUFFICIENT_EVIDENCE
        return result

    def _missing_ratio(self, view: AgentWorldView) -> float:
        """Missing ratio over the SELECTED candidate only (decision-critical)."""
        selected = self._best(view)
        if selected is None:
            return 1.0
        revealed = set(view.revealed_facets(selected))
        required = self.REQUIRED_FACETS
        missing = sum(1 for facet in required if facet not in revealed)
        return missing / len(required)

    def _facet_has_time_versions(
        self, view: AgentWorldView, pid: str, facet: EvidenceFacet
    ) -> bool:
        """Task E: True if a facet's recorded evidence carries multiple
        distinct observed_at values (i.e. the world models time drift for it),
        meaning a re-query could return a DIFFERENT value than the first read."""
        entries = view._world.evidence.get(pid, {}).get(facet, [])
        stamps = {e.observed_at for e in entries if e.observed_at is not None}
        return len(stamps) > 1


_FACET_ACTION: dict[EvidenceFacet, ResearchAction] = {
    EvidenceFacet.MARKET: ResearchAction.SEARCH_MARKET,
    EvidenceFacet.MARGIN: ResearchAction.SEARCH_MARGIN,
    EvidenceFacet.RELIABILITY: ResearchAction.SEARCH_RELIABILITY,
    EvidenceFacet.COMPETITION: ResearchAction.SEARCH_COMPETITION,
    EvidenceFacet.RISK: ResearchAction.SEARCH_RISK,
    EvidenceFacet.DEMAND: ResearchAction.SEARCH_DEMAND,
}


def controller_for(strategy: StrategyKind) -> _BaseController:
    if strategy is StrategyKind.FIXED:
        return FixedController()
    if strategy is StrategyKind.MISSING_EVIDENCE:
        return MissingEvidenceController()
    if strategy is StrategyKind.UNCERTAINTY:
        return UncertaintyController()
    if strategy is StrategyKind.ADAPTIVE_VOI:
        return AdaptiveVOIController()
    raise ValueError(f"unknown strategy: {strategy}")


def run_controller_episode(
    view: AgentWorldView,
    strategy: StrategyKind,
    *,
    budget: float = 10.0,
    max_steps: int = 12,
) -> ControllerResult:
    """Run one controller episode; evaluator computes regret separately."""
    controller = controller_for(strategy)
    controller.budget = budget
    controller.max_steps = max_steps
    return controller.run(view)
