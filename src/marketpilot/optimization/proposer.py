"""Phase 5.7: Multi-Family Policy Search (Task 1).

Expands the RSI candidate space beyond AdaptiveVOI parameter perturbation:
- PolicyConfig: strongly-typed policy configuration (strategy family +
  interpretable scheduling parameters) with a stable versioned hash.
- MultiFamilyProposer: two-stage candidate search:
    Stage 1: discrete strategy-family sampling (fixed / missing-evidence /
             uncertainty / adaptive-voi / contextual-hybrid).
    Stage 2: within-family parameter perturbation + conditional (contextual)
             policies.
- ContextualHybridPolicy: a lightweight deterministic meta-controller that
  picks the next research mode from OBSERVED state features only (never
  world_id / seed / oracle / hidden truth / future results).

Candidate provenance is recorded for every proposal (incumbent /
cross-family / param-perturbation / contextual) so the optimizer can audit
where improvements come from.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from marketpilot.policy.controller import ControllerResult

from marketpilot.optimization.dream_rsi import (
    DEFAULT_PARAMS,
    PARAM_KEYS,
    ParameterizedPolicy,
)
from marketpilot.world.core import AgentWorldView, EvidenceFacet

# Strategy families the proposer can sample (cross-family search).
STRATEGY_FAMILIES: tuple[str, ...] = (
    "fixed",
    "missing-evidence",
    "uncertainty",
    "adaptive-voi",
    "contextual-hybrid",
)

# Interpretable scheduling parameters (Task 1.1). Each maps to a PolicyConfig
# field; the controller reads the ones it supports.
SCHEDULE_PARAMS: tuple[str, ...] = (
    "voi_threshold",
    "refuse_threshold",
    "min_required_evidence",
    "max_research_steps",
    "conflict_weight",
    "research_cost_weight",
    "expected_gain_weight",
    "uncertainty_weight",
    "evidence_missing_weight",
    "refresh_stale_policy",
    "exploration_preference_rho",
)


@dataclass(frozen=True)
class PolicyConfig:
    """Strongly-typed policy configuration.

    - strategy: one of STRATEGY_FAMILIES
    - weights: facet scoring weights (subset of PARAM_KEYS)
    - schedule: interpretable scheduling parameters (SCHEDULE_PARAMS)
    """

    strategy: str = "adaptive-voi"
    weights: dict[str, float] = field(default_factory=dict)
    schedule: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.strategy not in STRATEGY_FAMILIES:
            raise ValueError(f"unknown strategy family: {self.strategy}")
        for key in self.weights:
            if key not in PARAM_KEYS:
                raise ValueError(f"unknown weight key: {key}")
        for key in self.schedule:
            if key not in SCHEDULE_PARAMS:
                raise ValueError(f"unknown schedule param: {key}")

    def to_policy(self, name: str = "policy") -> ParameterizedPolicy:
        """Build a ParameterizedPolicy from this config (merged with defaults)."""
        params = dict(DEFAULT_PARAMS)
        params.update(self.weights)
        # Map schedule params onto the policy's existing param surface where
        # they overlap (voi_threshold, refuse_threshold).
        for key in ("voi_threshold", "refuse_threshold"):
            if key in self.schedule:
                params[key] = self.schedule[key]
        return ParameterizedPolicy(params, name=name, strategy=self.strategy)

    @property
    def hash(self) -> str:
        """Stable versioned hash of the config (strategy + weights + schedule)."""
        payload = json.dumps(
            {
                "strategy": self.strategy,
                "weights": {k: round(v, 6) for k, v in sorted(self.weights.items())},
                "schedule": {k: round(v, 6) for k, v in sorted(self.schedule.items())},
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def to_json(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "weights": self.weights,
            "schedule": self.schedule,
            "hash": self.hash,
        }


class ContextualHybridPolicy:
    """Lightweight deterministic meta-controller (Task 1.3).

    Picks the next research mode from OBSERVED state features ONLY:
    - key evidence missing degree
    - candidate score gap
    - unresolved evidence conflicts
    - uncertainty of observed information
    - remaining budget
    - evidence staleness (W3)

    Forbidden inputs: world_id / seed / oracle best product id / hidden true
    utility / future research results / final test-set metrics.

    It delegates the actual research steps to a base family (default
    adaptive-voi) but adjusts stop/refuse willingness from state.
    """

    def __init__(self, config: PolicyConfig) -> None:
        self.config = config
        self.base = config.to_policy(name="contextual-base")

    def choose_mode(self, view: AgentWorldView, budget_left: float) -> str:
        """Choose a research mode from observable state (deterministic)."""
        schedule = self.config.schedule
        conflict_weight = schedule.get("conflict_weight", 0.3)
        # Count unresolved conflicts across candidates (observable only).
        conflicts = 0
        missing = 0
        total_facets = 0
        for candidate in view.candidates():
            pid = candidate["product_id"]
            revealed = set(view.revealed_facets(pid))
            for facet in EvidenceFacet:
                total_facets += 1
                if facet not in revealed:
                    missing += 1
            # Conflict: revealed evidence disagrees with observable baseline.
            for facet in (EvidenceFacet.MARGIN, EvidenceFacet.DEMAND, EvidenceFacet.RISK):
                entries = view.evidence_summary(pid).get(facet.value, [])
                if not entries:
                    continue
                observed = view.observable(pid)
                base_key = f"observed_{facet.value}"
                if base_key not in observed:
                    continue
                mean = sum(e["value"] for e in entries) / len(entries)
                if abs(mean - float(observed[base_key])) > 0.15:
                    conflicts += 1
        missing_ratio = missing / total_facets if total_facets else 0.0
        # Decision rules (deterministic, observable-state only). conflict_weight
        # scales the conflict threshold: higher weight -> trigger uncertainty
        # with fewer conflicts (eager verification).
        conflict_threshold = max(1.0, 3.0 - conflict_weight * 2.0)
        if missing_ratio > 0.5 and budget_left > 3.0:
            return "missing-evidence"  # key evidence missing, budget allows
        if conflicts >= conflict_threshold:
            return "uncertainty"  # conflicts unresolved -> verify
        if budget_left < 2.0:
            return "fixed"  # low budget -> cheapest systematic fill
        return "adaptive-voi"  # default

    def execute(self, view: AgentWorldView, **kwargs: Any) -> ControllerResult:
        """Execute the contextual policy: pick mode from state, then run."""
        from marketpilot.policy.controller import (
            StrategyKind,
            controller_for,
        )

        budget = kwargs.get("budget", 10.0)
        mode = self.choose_mode(view, budget)
        strategy_map = {
            "fixed": StrategyKind.FIXED,
            "missing-evidence": StrategyKind.MISSING_EVIDENCE,
            "uncertainty": StrategyKind.UNCERTAINTY,
            "adaptive-voi": StrategyKind.ADAPTIVE_VOI,
        }
        kind = strategy_map.get(mode, StrategyKind.ADAPTIVE_VOI)
        controller = controller_for(kind)
        controller.budget = budget
        controller.max_steps = int(kwargs.get("max_steps", 12))
        controller.configure_costs(dict(view._world.costs))
        if hasattr(controller, "refresh_stale"):
            controller.refresh_stale = _has_time_drift(view)
        if hasattr(controller, "_scores"):
            controller._scores = self._scored  # type: ignore[method-assign]
        return controller.run(view)

    def _scored(self, view: AgentWorldView) -> dict[str, float]:
        """Weighted scoring from revealed evidence (config weights)."""
        weights = dict(DEFAULT_PARAMS)
        weights.update(self.config.weights)
        scores: dict[str, float] = {}
        for candidate in view.candidates():
            pid = candidate["product_id"]
            total = 0.0
            for facet in EvidenceFacet:
                entries = view.evidence_summary(pid).get(facet.value, [])
                value = 0.5
                if entries:
                    value = sum(float(e["value"]) for e in entries) / len(entries)
                total += weights[f"weight_{facet.value}"] * value
            scores[pid] = total
        return scores


def _has_time_drift(view: AgentWorldView) -> bool:
    """True if any evidence has multiple observed_at versions (W3)."""
    for by_facet in view._world.evidence.values():
        for entries in by_facet.values():
            stamps = {e.observed_at for e in entries if e.observed_at is not None}
            if len(stamps) > 1:
                return True
    return False


class MultiFamilyProposer:
    """Two-stage multi-family candidate proposer (Task 1.2 / 1.4).

    Proposal sources (recorded in `provenance`):
    - incumbent: keep the current active policy as a candidate
    - cross-family: sample a different strategy family
    - param-perturbation: perturb weights within the current family
    - contextual: build a ContextualHybridPolicy from a sampled config
    """

    def __init__(self, seed: int = 7) -> None:
        self.rng = random.Random(seed)
        self.provenance: dict[str, str] = {}
        self.proposals_made = 0

    def propose(
        self,
        incumbent: ParameterizedPolicy,
        round_index: int,
        *,
        n_candidates: int = 4,
        allow_contextual: bool = True,
    ) -> list[ParameterizedPolicy]:
        """Propose a batch of candidates (incumbent always included)."""
        candidates: list[ParameterizedPolicy] = []
        # 1. Incumbent retained.
        candidates.append(incumbent)
        self.provenance[incumbent.hash] = "incumbent"
        # 2. Cross-family + within-family + contextual.
        for i in range(n_candidates - 1):
            roll = self.rng.random()
            if allow_contextual and roll < 0.2:
                cand = self._contextual_candidate(round_index, i)
            elif roll < 0.7:
                cand = self._cross_family_candidate(round_index, i)
            else:
                cand = self._param_perturbation(incumbent, round_index, i)
            candidates.append(cand)
            self.provenance.setdefault(cand.hash, "unknown")
        self.proposals_made += n_candidates
        return candidates

    def _cross_family_candidate(self, round_index: int, i: int) -> ParameterizedPolicy:
        """Sample a different strategy family with default-ish weights."""
        family = self.rng.choice(
            [f for f in STRATEGY_FAMILIES if f != "contextual-hybrid"]
        )
        # Perturb a couple of weights within [-1, 1].
        weights: dict[str, float] = {}
        for key in list(PARAM_KEYS)[:6]:
            if self.rng.random() < 0.4:
                weights[key] = round(self.rng.uniform(-0.3, 0.9), 4)
        cfg = PolicyConfig(strategy=family, weights=weights)
        cand = cfg.to_policy(name=f"cross-family-r{round_index}-{i}")
        self.provenance[cand.hash] = f"cross-family:{family}"
        return cand

    def _param_perturbation(
        self, incumbent: ParameterizedPolicy, round_index: int, i: int
    ) -> ParameterizedPolicy:
        """Perturb the incumbent's weights within its own family."""
        params = dict(incumbent.params)
        for key in list(PARAM_KEYS)[:6]:
            params[key] = max(-1.0, min(1.0, params[key] + self.rng.uniform(-0.1, 0.1)))
        cand = ParameterizedPolicy(
            params, name=f"param-pert-r{round_index}-{i}", strategy=incumbent.strategy
        )
        self.provenance[cand.hash] = f"param-perturbation:{incumbent.strategy}"
        return cand

    def _contextual_candidate(self, round_index: int, i: int) -> ParameterizedPolicy:
        """Build a contextual-hybrid policy candidate."""
        weights: dict[str, float] = {}
        for key in list(PARAM_KEYS)[:6]:
            if self.rng.random() < 0.3:
                weights[key] = round(self.rng.uniform(-0.3, 0.9), 4)
        cfg = PolicyConfig(
            strategy="contextual-hybrid",
            weights=weights,
            schedule={"conflict_weight": round(self.rng.uniform(0.1, 0.5), 3)},
        )
        cand = cfg.to_policy(name=f"contextual-r{round_index}-{i}")
        self.provenance[cand.hash] = f"contextual:{cfg.hash}"
        return cand


def propose_batch(
    incumbent: ParameterizedPolicy,
    round_index: int,
    seed: int = 7,
    n_candidates: int = 4,
) -> list[ParameterizedPolicy]:
    """Convenience wrapper: propose a multi-family batch."""
    proposer = MultiFamilyProposer(seed=seed)
    return proposer.propose(incumbent, round_index, n_candidates=n_candidates)
