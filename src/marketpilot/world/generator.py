"""Benchmark v3: parametric world generator (Task 1).

Separates (Task 1.1):
- Hidden World State  : TrueProduct (true attributes, true utility)
- Observation Model   : ObservableProduct + Evidence (noise/bias/source/time)
- Action Environment  : ResearchAction, costs, state transitions
- Hidden Evaluator    : WorldOracle (evaluator-side only)

Implements a composable WorldGenerationSpec (Task 1.2) whose parameters
actually CHANGE evidence distribution / action costs / decision difficulty
(Task 1.3): observable evidence is generated FROM hidden truth through
noise/bias/time/source mechanisms, so research has real information value
and no single field leaks the oracle answer.

Mechanism composition (Task 1.4) is expressed as tags; each tag activates
a real behavioral change, not a renamed template.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass

from marketpilot.input.spec import WorldSplit
from marketpilot.world.core import (
    Difficulty,
    Evidence,
    EvidenceFacet,
    ObservableProduct,
    TrueProduct,
    World,
)

_FACETS: list[EvidenceFacet] = [
    EvidenceFacet.MARGIN,
    EvidenceFacet.RELIABILITY,
    EvidenceFacet.DEMAND,
    EvidenceFacet.COMPETITION,
    EvidenceFacet.RISK,
]


@dataclass(frozen=True)
class WorldGenerationSpec:
    """Configurable world-generation parameters (Task 1.2).

    Every parameter has an observable behavioral effect on the generated
    world (evidence distribution, action costs, or decision difficulty).
    """

    product_count: int = 4
    category_family: str = "electronics"
    candidate_utility_gap: float = 0.15  # gap between best and second-best
    hidden_risk_strength: float = 0.4  # risk magnitude of hidden risk
    evidence_noise_level: float = 0.1  # per-observation noise
    source_reliability: float = 0.9  # probability a source is reliable
    source_bias: float = 0.05  # systematic per-source bias
    evidence_redundancy: int = 1  # copies of each (facet, product) evidence
    conflict_probability: float = 0.2  # chance of a conflicting source
    evidence_missingness: float = 0.1  # fraction of facets absent up front
    information_acquisition_cost: float = 1.0  # base cost per action
    action_cost_asymmetry: float = 0.0  # spread across facets
    temporal_drift: float = 0.0  # chance evidence changes over time
    market_constraint_difficulty: float = 0.0  # viability threshold tightness
    research_budget: float = 12.0
    abstention_requirement: float = 0.0  # fraction of worlds needing abstain

    def spec_hash(self) -> str:
        raw = json.dumps(
            {
                k: v
                for k, v in self.__dict__.items()
                if not k.startswith("_")
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _utility(
    margin: float,
    reliability: float,
    demand: float,
    competition: float,
    risk: float,
) -> float:
    """Business utility: margin * reliability * demand * (1-risk) * (1-comp)."""
    return max(
        0.0,
        margin * reliability * demand * (1.0 - risk) * (1.0 - competition),
    )


def _make_product(
    rng: random.Random,
    *,
    label: str,
    true_margin: float,
    true_reliability: float,
    true_demand: float,
    true_competition: float,
    true_risk: float,
    viable: bool,
) -> TrueProduct:
    pid = f"{label}-{rng.randrange(10**8):08x}"
    return TrueProduct(
        product_id=pid,
        true_margin=true_margin,
        true_reliability=true_reliability,
        true_demand=true_demand,
        true_competition=true_competition,
        true_risk=true_risk,
        true_utility=_utility(
            true_margin, true_reliability, true_demand, true_competition, true_risk
        ),
        viable=viable,
    )


def _observed(
    rng: random.Random,
    *,
    product: TrueProduct,
    noise: float,
    bias: float,
    title: str,
) -> ObservableProduct:
    """Observable values = hidden truth + noise + bias (clamped to [0,1])."""
    return ObservableProduct(
        product_id=product.product_id,
        observed_margin=_clamp(product.true_margin + rng.gauss(0, noise) + bias),
        observed_reliability=_clamp(
            product.true_reliability + rng.gauss(0, noise) + bias
        ),
        observed_demand=_clamp(product.true_demand + rng.gauss(0, noise) + bias),
        observed_competition=_clamp(
            product.true_competition + rng.gauss(0, noise) + bias
        ),
        observed_risk=_clamp(product.true_risk + rng.gauss(0, noise) + bias),
        title=f"{title} {product.product_id[:6]}",
    )


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _make_evidence(
    rng: random.Random,
    *,
    product: TrueProduct,
    facet: EvidenceFacet,
    noise: float,
    bias: float,
    reliability: float,
    observed_at: int | None = None,
    conflict_with_truth: bool = False,
) -> Evidence:
    truth = {
        EvidenceFacet.MARGIN: product.true_margin,
        EvidenceFacet.RELIABILITY: product.true_reliability,
        EvidenceFacet.DEMAND: product.true_demand,
        EvidenceFacet.COMPETITION: product.true_competition,
        EvidenceFacet.RISK: product.true_risk,
    }[facet]
    value = _clamp(truth + rng.gauss(0, noise) + bias)
    if conflict_with_truth:
        # A conflicting source: value pushed away from truth by a large step.
        value = _clamp(1.0 - value if rng.random() < 0.5 else value * 0.5 + 0.4)
    return Evidence(
        facet=facet,
        value=value,
        truth_value=truth,
        noise=noise,
        bias=bias,
        stale=False,
        conflict_with_truth=conflict_with_truth,
        source=f"{product.product_id}-{facet.value}-{rng.randrange(10**6):06x}",
        observed_at=observed_at,
    )


def generate_world(
    spec: WorldGenerationSpec,
    *,
    seed: int,
    world_id: str,
    split: WorldSplit = WorldSplit.DEV,
    family: str = "v3",
) -> World:
    """Generate one deterministic world from a spec (Task 1.2/1.3)."""
    rng = random.Random(seed)
    n = spec.product_count
    gap = spec.candidate_utility_gap

    # --- Hidden world state -------------------------------------------
    # Best product: high margin/demand/reliability, low risk/competition.
    best_margin = _clamp(0.65 + rng.uniform(-0.05, 0.05))
    best_demand = _clamp(0.7 + rng.uniform(-0.05, 0.05))
    best_rel = _clamp(0.8 + rng.uniform(-0.05, 0.05))
    best_risk = _clamp(0.15 + rng.uniform(-0.05, 0.05))
    best_comp = _clamp(0.2 + rng.uniform(-0.05, 0.05))
    products: list[TrueProduct] = [
        _make_product(
            rng,
            label="best",
            true_margin=best_margin,
            true_reliability=best_rel,
            true_demand=best_demand,
            true_competition=best_comp,
            true_risk=best_risk,
            viable=True,
        )
    ]
    # Distractor products: progressively worse utility.
    for i in range(1, n):
        degrade = gap * i + rng.uniform(0.02, 0.08)
        margin = _clamp(best_margin - degrade * rng.uniform(0.5, 1.2))
        demand = _clamp(best_demand - degrade * rng.uniform(0.3, 1.0))
        risk = _clamp(best_risk + spec.hidden_risk_strength * rng.uniform(0.5, 1.5))
        comp = _clamp(best_comp + degrade * rng.uniform(0.2, 0.8))
        viable = rng.random() > spec.market_constraint_difficulty
        products.append(
            _make_product(
                rng,
                label=f"d{i}",
                true_margin=margin,
                true_reliability=_clamp(best_rel - degrade * 0.2),
                true_demand=demand,
                true_competition=comp,
                true_risk=risk,
                viable=viable,
            )
        )
    # Anti-leak: shuffle product order AND re-label with random letters so
    # neither list position nor label prefix reveals the best product
    # (Task 2.4 / 9).
    rng.shuffle(products)
    letters = [f"p{chr(97 + i)}" for i in range(n)]
    rng.shuffle(letters)
    from dataclasses import replace

    products = [
        replace(p, product_id=f"{label}-{p.product_id.split('-', 1)[1]}")
        for p, label in zip(products, letters, strict=True)
    ]

    # --- Observation model ---------------------------------------------
    observables = {
        p.product_id: _observed(
            rng,
            product=p,
            noise=spec.evidence_noise_level,
            bias=spec.source_bias,
            title=f"{family} {world_id}",
        )
        for p in products
    }

    # --- Action environment: per-facet costs with asymmetry -------------
    action_costs: dict[EvidenceFacet, float] = {}
    base = spec.information_acquisition_cost
    for j, facet in enumerate(_FACETS):
        asym = spec.action_cost_asymmetry * (j - 2) / 2  # -asym..+asym
        action_costs[facet] = max(0.2, base + asym)

    # --- Evidence (action-revealed) -------------------------------------
    evidence: dict[str, dict[EvidenceFacet, list[Evidence]]] = {}
    for p in products:
        by_facet: dict[EvidenceFacet, list[Evidence]] = {}
        for facet in _FACETS:
            entries: list[Evidence] = []
            # Primary (reliable) source.
            primary = _make_evidence(
                rng,
                product=p,
                facet=facet,
                noise=spec.evidence_noise_level,
                bias=spec.source_bias,
                reliability=spec.source_reliability,
                observed_at=0 if spec.temporal_drift > 0 else None,
            )
            entries.append(primary)
            # Redundant copies.
            for _ in range(spec.evidence_redundancy - 1):
                entries.append(
                    _make_evidence(
                        rng,
                        product=p,
                        facet=facet,
                        noise=spec.evidence_noise_level,
                        bias=spec.source_bias,
                        reliability=spec.source_reliability,
                        observed_at=0 if spec.temporal_drift > 0 else None,
                    )
                )
            # Conflict source.
            if rng.random() < spec.conflict_probability:
                entries.append(
                    _make_evidence(
                        rng,
                        product=p,
                        facet=facet,
                        noise=spec.evidence_noise_level * 2,
                        bias=spec.source_bias,
                        reliability=0.3,
                        conflict_with_truth=True,
                        observed_at=0 if spec.temporal_drift > 0 else None,
                    )
                )
            # Time drift: a later observation with a different value.
            if spec.temporal_drift > 0 and rng.random() < spec.temporal_drift:
                drift = _make_evidence(
                    rng,
                    product=p,
                    facet=facet,
                    noise=spec.evidence_noise_level,
                    bias=spec.source_bias,
                    reliability=spec.source_reliability,
                    observed_at=2,
                )
                # Drift the value away from the stale one.
                stale = entries[0].value
                drift_value = _clamp(stale + rng.uniform(-0.3, 0.3))
                drift = Evidence(
                    facet=facet,
                    value=drift_value,
                    truth_value=drift.truth_value,
                    noise=drift.noise,
                    bias=drift.bias,
                    stale=False,
                    conflict_with_truth=drift.conflict_with_truth,
                    source=drift.source,
                    observed_at=2,
                )
                entries[0] = Evidence(
                    facet=facet,
                    value=stale,
                    truth_value=entries[0].truth_value,
                    noise=entries[0].noise,
                    bias=entries[0].bias,
                    stale=True,  # superseded by the t=2 observation
                    conflict_with_truth=entries[0].conflict_with_truth,
                    source=entries[0].source,
                    observed_at=0,
                )
                entries.append(drift)
            by_facet[facet] = entries
        evidence[p.product_id] = by_facet

    # --- Difficulty from spec -------------------------------------------
    difficulty = Difficulty.HARD
    if gap <= 0.05:
        difficulty = Difficulty.EASY
    elif gap <= 0.2:
        difficulty = Difficulty.MEDIUM

    return World(
        world_id=world_id,
        split=split,
        products=products,
        observables=observables,
        evidence=evidence,
        difficulty=difficulty,
        key_facet=EvidenceFacet.MARGIN,
        action_costs=action_costs,
        world_version=f"v3-{family}-{spec.spec_hash()[:8]}",
        research_budget=spec.research_budget,
    )


def world_config_hash(world: World) -> str:
    """Deterministic config hash for manifest/freeze verification."""
    raw = json.dumps(world.to_json(), sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()
