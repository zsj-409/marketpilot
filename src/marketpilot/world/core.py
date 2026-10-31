"""Phase 2: Synthetic Market v3 — controlled research worlds.

Design goals (from the V2 spec):
- hidden true product attributes (latent utility/risk), oracle-only
- noisy/biased observable evidence
- action-conditioned evidence revelation (different research actions reveal
  different facets)
- missing / conflicting / stale evidence
- difficulty tiers
- strict Oracle/Agent isolation
- world-level data split (dev / confirmation / test)

The first deliverable is the minimal task that PROVES "acquiring a key piece
of evidence can change the decision": a decision that flips from WRONG to
RIGHT when the right action is taken, and stays WRONG when a cheaper/wrong
action is taken.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any
from uuid import NAMESPACE_URL, uuid5

from marketpilot.input.spec import WorldSplit

if TYPE_CHECKING:
    from pathlib import Path


class EvidenceFacet(StrEnum):
    """Action-revealed evidence facets."""

    MARKET = "market"
    MARGIN = "margin"
    RELIABILITY = "reliability"
    COMPETITION = "competition"
    RISK = "risk"
    DEMAND = "demand"


class ResearchAction(StrEnum):
    """Actions an agent can take; each reveals different evidence."""

    SEARCH_MARKET = "search_market"
    SEARCH_MARGIN = "search_margin"
    SEARCH_RELIABILITY = "search_reliability"
    SEARCH_COMPETITION = "search_competition"
    SEARCH_RISK = "search_risk"
    SEARCH_DEMAND = "search_demand"
    STOP = "stop"


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Decision(StrEnum):
    GO = "GO"
    NO_GO = "NO_GO"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True)
class TrueProduct:
    """Hidden ground-truth product attributes (oracle-only)."""

    product_id: str
    true_margin: float
    true_reliability: float
    true_demand: float
    true_competition: float
    true_risk: float
    true_utility: float
    viable: bool


@dataclass(frozen=True)
class ObservableProduct:
    """Agent-visible (noisy/biased) product attributes."""

    product_id: str
    title: str
    observed_margin: float
    observed_reliability: float
    observed_demand: float
    observed_competition: float
    observed_risk: float

    def to_json(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "title": self.title,
            "observed_margin": round(self.observed_margin, 4),
            "observed_reliability": round(self.observed_reliability, 4),
            "observed_demand": round(self.observed_demand, 4),
            "observed_competition": round(self.observed_competition, 4),
            "observed_risk": round(self.observed_risk, 4),
        }


@dataclass
class Evidence:
    """One piece of observed evidence (may be noisy/biased/stale/conflicting)."""

    facet: EvidenceFacet
    value: float
    truth_value: float
    noise: float
    bias: float
    stale: bool
    conflict_with_truth: bool
    source: str
    # W3: observation time step. Evidence acquired at a later time may differ
    # from earlier evidence of the same facet (time drift). None = static.
    observed_at: int | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "facet": self.facet.value,
            "value": round(self.value, 4),
            "truth_value": round(self.truth_value, 4),
            "noise": round(self.noise, 4),
            "bias": round(self.bias, 4),
            "stale": self.stale,
            "conflict_with_truth": self.conflict_with_truth,
            "source": self.source,
            "observed_at": self.observed_at,
        }


@dataclass
class World:
    """One frozen research world: true products + action-revealed evidence."""

    world_id: str
    split: WorldSplit
    products: list[TrueProduct]
    observables: dict[str, ObservableProduct]
    evidence: dict[str, dict[EvidenceFacet, list[Evidence]]]
    difficulty: Difficulty
    # Evidence-revealed threshold above which an agent can flip to a correct
    # decision. This is per-world and set at construction time.
    key_facet: EvidenceFacet = EvidenceFacet.MARGIN
    # W2: per-world research action costs (facet -> cost). Defaults to the
    # controller's standard costs; diagnostic worlds override this.
    action_costs: dict[EvidenceFacet, float] | None = None
    # W3: world version for replay indexing (state/observation identity).
    world_version: str = "v3"
    # Benchmark v3.1: per-world research budget (None = use controller default).
    research_budget: float | None = None

    @property
    def costs(self) -> dict[EvidenceFacet, float]:
        """Effective action costs (world-configured or standard defaults)."""
        if self.action_costs is None:
            from marketpilot.policy.controller import _DEFAULT_FACET_COST

            return dict(_DEFAULT_FACET_COST)
        return dict(self.action_costs)

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"world_{self.world_id}.json").write_text(
            json.dumps(self.to_json(), indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "world_id": self.world_id,
            "split": self.split.value,
            "difficulty": self.difficulty.value,
            "key_facet": self.key_facet.value,
            "world_version": self.world_version,
            "action_costs": (
                {facet.value: round(cost, 4) for facet, cost in self.action_costs.items()}
                if self.action_costs is not None
                else None
            ),
            "products": [
                {
                    "product_id": p.product_id,
                    "true_margin": p.true_margin,
                    "true_reliability": p.true_reliability,
                    "true_demand": p.true_demand,
                    "true_competition": p.true_competition,
                    "true_risk": p.true_risk,
                    "true_utility": p.true_utility,
                    "viable": p.viable,
                }
                for p in self.products
            ],
            "observables": {pid: obs.to_json() for pid, obs in self.observables.items()},
            "evidence": {
                pid: {
                    facet.value: [e.to_json() for e in entries]
                    for facet, entries in by_facet.items()
                }
                for pid, by_facet in self.evidence.items()
            },
        }


class WorldOracle:
    """Strict oracle: only evaluators may read hidden truth.

    The oracle is a separate object; agents and policies never receive it.
    """

    def __init__(self, world: World) -> None:
        self._world = world
        self._by_id = {p.product_id: p for p in world.products}

    def true_utility(self, product_id: str) -> float:
        return self._by_id[product_id].true_utility

    def true_viable(self, product_id: str) -> bool:
        return self._by_id[product_id].viable

    def best_product_id(self) -> str:
        return max(
            self._by_id,
            key=lambda pid: (self._by_id[pid].true_utility, self._by_id[pid].viable),
        )

    def best_utility(self) -> float:
        return self._by_id[self.best_product_id()].true_utility

    def regret(self, selected_id: str | None) -> float:
        if selected_id is None:
            return self.best_utility()
        return self.best_utility() - self._by_id[selected_id].true_utility

    def true_by_id(self) -> dict[str, TrueProduct]:
        return dict(self._by_id)


class AgentWorldView:
    """Agent-visible world: observables + action-revealed evidence only.

    This is the ONLY interface research policies may use. It never exposes
    oracle truth, never accepts a policy hint, and never reveals future
    branches.
    """

    def __init__(self, world: World) -> None:
        self._world = world
        self._revealed: dict[str, set[EvidenceFacet]] = {}
        # W3: deterministic world time. Advances on each non-STOP action.
        # Never uses real system time (benchmark must be reproducible).
        self._time = 0

    @property
    def world_id(self) -> str:
        return self._world.world_id

    @property
    def world_version(self) -> str:
        return self._world.world_version

    @property
    def difficulty(self) -> Difficulty:
        return self._world.difficulty

    @property
    def time(self) -> int:
        """Current deterministic world time step (W3)."""
        return self._time

    def state_signature(self) -> str:
        """Deterministic signature of the current agent-visible state.

        Includes world id/version, the current time, and which facets are
        revealed per product. Two views with the same signature are in the
        same replayable state; a time difference changes the signature (W3).
        """
        import hashlib

        revealed = {
            pid: [facet.value for facet in sorted(facets)] for pid, facets in self._revealed.items()
        }
        payload = {
            "world_id": self._world.world_id,
            "world_version": self._world.world_version,
            "time": self._time,
            "revealed": revealed,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]

    def candidates(self) -> list[dict[str, Any]]:
        return [obs.to_json() for obs in self._world.observables.values()]

    def observable(self, product_id: str) -> dict[str, Any]:
        return self._world.observables[product_id].to_json()

    def take_action(
        self,
        action: ResearchAction,
        product_id: str | None = None,
        *,
        refresh: bool = False,
    ) -> list[Evidence]:
        """Reveal evidence for one action. STOP reveals nothing.

        W3: if the world's evidence carries `observed_at` time steps, the
        revealed evidence is the one whose `observed_at` matches the current
        view time; time advances by 1 after a non-STOP action.
        `refresh=True` re-queries an ALREADY-revealed facet at the CURRENT
        time (Task E): this is how a policy re-observes drifted evidence. It
        still costs one time step; it never goes BACKWARD in time.
        """
        if action is ResearchAction.STOP:
            return []
        facet = _ACTION_FACET[action]
        if product_id is None:
            product_id = self._world.products[0].product_id
        if not refresh:
            self._revealed.setdefault(product_id, set()).add(facet)
        entries = self._world.evidence.get(product_id, {}).get(facet, [])
        # W3 time-drift: pick the entry whose observed_at == current time
        # (falls back to the latest entry <= time, or the last entry).
        if entries:
            matching = [e for e in entries if e.observed_at == self._time]
            if matching:
                entries = matching
            else:
                past = [
                    e for e in entries if e.observed_at is not None and e.observed_at <= self._time
                ]
                entries = [max(past, key=lambda e: e.observed_at or 0)] if past else [entries[-1]]
        # Advance deterministic world time (never real clock).
        self._time += 1
        return list(entries)

    def revealed_facets(self, product_id: str) -> list[EvidenceFacet]:
        return sorted(self._revealed.get(product_id, set()))

    def evidence_summary(self, product_id: str) -> dict[str, list[dict[str, Any]]]:
        revealed = self._revealed.get(product_id, set())
        by_facet = self._world.evidence.get(product_id, {})
        return {facet.value: [e.to_json() for e in by_facet.get(facet, [])] for facet in revealed}


_ACTION_FACET: dict[ResearchAction, EvidenceFacet] = {
    ResearchAction.SEARCH_MARKET: EvidenceFacet.MARKET,
    ResearchAction.SEARCH_MARGIN: EvidenceFacet.MARGIN,
    ResearchAction.SEARCH_RELIABILITY: EvidenceFacet.RELIABILITY,
    ResearchAction.SEARCH_COMPETITION: EvidenceFacet.COMPETITION,
    ResearchAction.SEARCH_RISK: EvidenceFacet.RISK,
    ResearchAction.SEARCH_DEMAND: EvidenceFacet.DEMAND,
}


class DeterministicPolicy:
    """Simple heuristic policies for the minimal-world self-checks."""

    def __init__(self, actions: tuple[ResearchAction, ...]) -> None:
        self.actions = actions

    def run(self, view: AgentWorldView) -> dict[str, Any]:
        revealed: dict[str, dict[str, Any]] = {}
        for action in self.actions:
            for candidate in view.candidates():
                pid = candidate["product_id"]
                evidence = view.take_action(action, pid)
                for item in evidence:
                    revealed.setdefault(pid, {}).setdefault(item.facet.value, []).append(item.value)
        # Score each candidate from revealed evidence only (unrevealed -> 0.5 neutral).
        scores: dict[str, float] = {}
        for candidate in view.candidates():
            pid = candidate["product_id"]
            margin = _mean(revealed.get(pid, {}).get("margin", []))
            demand = _mean(revealed.get(pid, {}).get("demand", []))
            risk = _mean(revealed.get(pid, {}).get("risk", []))
            if margin is None:
                margin = 0.5
            if demand is None:
                demand = 0.5
            if risk is None:
                risk = 0.5
            scores[pid] = 0.5 * margin + 0.3 * demand - 0.2 * risk
        best = max(scores, key=lambda pid: scores[pid]) if scores else None
        return {
            "selected_id": best,
            "score": scores.get(best or "", 0.0),
            "scores": scores,
            "revealed_facets": {pid: view.revealed_facets(pid) for pid in scores},
        }


class RandomPolicy:
    """Random action policy for self-check baseline."""

    def run(self, view: AgentWorldView) -> dict[str, Any]:
        import random

        rng = random.Random(0)
        actions = list(ResearchAction)
        chosen = rng.choice(actions[:-1])  # never STOP
        result: dict[str, Any] = {}
        for candidate in view.candidates():
            evidence = view.take_action(chosen, candidate["product_id"])
            result[candidate["product_id"]] = [e.value for e in evidence]
        scores = {
            pid: sum(result.get(pid, [])) / max(len(result.get(pid, [])), 1) for pid in result
        }
        best = max(scores, key=lambda pid: scores[pid]) if scores else None
        return {
            "selected_id": best,
            "score": scores.get(best or "", 0.0),
            "scores": scores,
        }


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def build_minimal_world(
    *,
    seed: int = 7,
    split: WorldSplit = WorldSplit.DEV,
    world_id: str = "minimal-dev",
) -> World:
    """Build the minimal world that proves evidence acquisition changes decisions.

    Two products: A (true viable, high true margin but BAD observed margin) and
    B (true non-viable, low true margin but GOOD observed margin). Without the
    margin evidence, the agent chooses B (WRONG). With the margin evidence, the
    agent chooses A (RIGHT).
    """
    import random

    rng = random.Random(seed)

    a = TrueProduct(
        product_id=str(uuid5(NAMESPACE_URL, "marketpilot:world:minimal:product-a")),
        true_margin=0.72,
        true_reliability=0.8,
        true_demand=0.6,
        true_competition=0.4,
        true_risk=0.3,
        true_utility=0.74,
        viable=True,
    )
    b = TrueProduct(
        product_id=str(uuid5(NAMESPACE_URL, "marketpilot:world:minimal:product-b")),
        true_margin=0.28,
        true_reliability=0.7,
        true_demand=0.65,
        true_competition=0.35,
        true_risk=0.45,
        true_utility=0.38,
        viable=False,
    )

    observables = {
        str(a.product_id): ObservableProduct(
            product_id=str(a.product_id),
            title="Aster Air Grooming",
            observed_margin=0.35,  # biased low
            observed_reliability=0.75,
            observed_demand=0.55,
            observed_competition=0.45,
            observed_risk=0.4,
        ),
        str(b.product_id): ObservableProduct(
            product_id=str(b.product_id),
            title="Lumen Pro Feeder",
            observed_margin=0.55,  # biased high
            observed_reliability=0.7,
            observed_demand=0.6,
            observed_competition=0.4,
            observed_risk=0.35,
        ),
    }

    evidence: dict[str, dict[EvidenceFacet, list[Evidence]]] = {}
    for pid, product in ((str(a.product_id), a), (str(b.product_id), b)):
        by_facet: dict[EvidenceFacet, list[Evidence]] = {}
        # margin evidence: for A, revealed evidence is ACCURATE (high margin);
        # for B, revealed evidence is accurate too (low margin). The bias lives
        # in the observable baseline, not the revealed evidence.
        by_facet[EvidenceFacet.MARGIN] = [
            Evidence(
                facet=EvidenceFacet.MARGIN,
                value=_clamp(product.true_margin + rng.uniform(-0.03, 0.03)),
                truth_value=product.true_margin,
                noise=0.03,
                bias=0.0,
                stale=False,
                conflict_with_truth=False,
                source=f"margin-report:{pid}",
            )
        ]
        by_facet[EvidenceFacet.DEMAND] = [
            Evidence(
                facet=EvidenceFacet.DEMAND,
                value=_clamp(product.true_demand + rng.uniform(-0.05, 0.05)),
                truth_value=product.true_demand,
                noise=0.05,
                bias=0.0,
                stale=False,
                conflict_with_truth=False,
                source=f"demand-report:{pid}",
            )
        ]
        by_facet[EvidenceFacet.RISK] = [
            Evidence(
                facet=EvidenceFacet.RISK,
                value=_clamp(product.true_risk + rng.uniform(-0.05, 0.05)),
                truth_value=product.true_risk,
                noise=0.05,
                bias=0.0,
                stale=False,
                conflict_with_truth=False,
                source=f"risk-report:{pid}",
            )
        ]
        evidence[pid] = by_facet

    return World(
        world_id=world_id,
        split=split,
        products=[a, b],
        observables=observables,
        evidence=evidence,
        difficulty=Difficulty.EASY,
        key_facet=EvidenceFacet.MARGIN,
    )


def build_dev_conf_test_worlds(
    *,
    seed: int = 7,
    base_dir: Path,
) -> dict[str, World]:
    """Build a dev / confirmation / test world trio for the minimal task."""
    worlds = {
        "minimal-dev": build_minimal_world(seed=seed, split=WorldSplit.DEV, world_id="minimal-dev"),
        "minimal-confirmation": build_minimal_world(
            seed=seed + 1, split=WorldSplit.CONFIRMATION, world_id="minimal-confirmation"
        ),
        "minimal-test": build_minimal_world(
            seed=seed + 2, split=WorldSplit.TEST, world_id="minimal-test"
        ),
    }
    base_dir.mkdir(parents=True, exist_ok=True)
    for world in worlds.values():
        world.save(base_dir)
    return worlds


def write_world_manifest(worlds: dict[str, World], base_dir: Path) -> None:
    """Write a manifest that records world hashes and splits (frozen corpus)."""
    manifest = {
        "version": "v3-minimal",
        "worlds": {
            world_id: {
                "split": world.split.value,
                "difficulty": world.difficulty.value,
                "hash": _world_hash(world),
            }
            for world_id, world in worlds.items()
        },
    }
    (base_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _world_hash(world: World) -> str:
    payload = world.to_json()
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def load_worlds(base_dir: Path) -> dict[str, World]:
    """Load frozen worlds from a directory (world_<id>.json files)."""
    worlds: dict[str, World] = {}
    for path in base_dir.glob("world_*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        products = [
            TrueProduct(
                product_id=item["product_id"],
                true_margin=float(item["true_margin"]),
                true_reliability=float(item["true_reliability"]),
                true_demand=float(item["true_demand"]),
                true_competition=float(item["true_competition"]),
                true_risk=float(item["true_risk"]),
                true_utility=float(item["true_utility"]),
                viable=bool(item["viable"]),
            )
            for item in data["products"]
        ]
        observables = {pid: ObservableProduct(**item) for pid, item in data["observables"].items()}
        evidence = {
            pid: {
                EvidenceFacet(facet): [
                    Evidence(
                        facet=EvidenceFacet(facet),
                        value=float(e["value"]),
                        truth_value=float(e["truth_value"]),
                        noise=float(e["noise"]),
                        bias=float(e["bias"]),
                        stale=bool(e["stale"]),
                        conflict_with_truth=bool(e["conflict_with_truth"]),
                        source=e["source"],
                        observed_at=e.get("observed_at"),
                    )
                    for e in entries
                ]
                for facet, entries in by_facet.items()
            }
            for pid, by_facet in data["evidence"].items()
        }
        action_costs = None
        if data.get("action_costs") is not None:
            action_costs = {
                EvidenceFacet(facet): float(cost) for facet, cost in data["action_costs"].items()
            }
        worlds[data["world_id"]] = World(
            world_id=data["world_id"],
            split=WorldSplit(data["split"]),
            products=products,
            observables=observables,
            evidence=evidence,
            difficulty=Difficulty(data["difficulty"]),
            key_facet=EvidenceFacet(data["key_facet"]),
            action_costs=action_costs,
            world_version=data.get("world_version", "v3"),
        )
    return worlds


def _make_product(
    *,
    rng: Any,
    label: str,
    true_margin: float,
    true_reliability: float,
    true_demand: float,
    true_competition: float,
    true_risk: float,
    viable: bool,
) -> TrueProduct:
    """Build a TrueProduct with a deterministic utility from its attributes."""
    utility = _clamp(
        0.35 * true_margin
        + 0.25 * true_demand
        + 0.15 * true_reliability
        - 0.15 * true_competition
        - 0.2 * true_risk
    )
    return TrueProduct(
        product_id=str(uuid5(NAMESPACE_URL, f"marketpilot:world:diag:{label}")),
        true_margin=round(true_margin, 4),
        true_reliability=round(true_reliability, 4),
        true_demand=round(true_demand, 4),
        true_competition=round(true_competition, 4),
        true_risk=round(true_risk, 4),
        true_utility=round(utility, 4),
        viable=viable,
    )


def _make_observable(
    *,
    product: TrueProduct,
    title: str,
    bias_margin: float = 0.0,
    bias_demand: float = 0.0,
    bias_risk: float = 0.0,
) -> ObservableProduct:
    """Agent-visible product: true attributes + controllable bias."""
    return ObservableProduct(
        product_id=product.product_id,
        title=title,
        observed_margin=_clamp(product.true_margin + bias_margin),
        observed_reliability=round(product.true_reliability, 4),
        observed_demand=_clamp(product.true_demand + bias_demand),
        observed_competition=round(product.true_competition, 4),
        observed_risk=_clamp(product.true_risk + bias_risk),
    )


def _make_evidence(
    *,
    facet: EvidenceFacet,
    value: float,
    truth: float,
    noise: float = 0.0,
    bias: float = 0.0,
    conflict: bool = False,
    source: str,
    observed_at: int | None = None,
) -> Evidence:
    return Evidence(
        facet=facet,
        value=_clamp(value),
        truth_value=round(truth, 4),
        noise=noise,
        bias=bias,
        stale=False,
        conflict_with_truth=conflict,
        source=source,
        observed_at=observed_at,
    )


def build_diagnostic_world(
    *,
    kind: str,
    seed: int = 7,
    split: WorldSplit = WorldSplit.DEV,
    world_id: str = "diag",
    n_products: int = 4,
) -> World:
    """Build one of the six diagnostic world mechanisms (W0..W5).

    kind:
      W0 no-info-negative-control : all key evidence visible up front; any
            reasonable policy decides correctly. Used to verify the harness
            does NOT claim improvement where none exists.
      W1 hidden-risk              : observable evidence is biased toward a
            non-oracle product; the key risk/margin evidence is only revealed
            by research. NO score tie at init (unlike minimal world).
      W2 budget-and-value         : action costs differ; a cheap low-value
            action and an expensive high-value action exist. Different action
            order under a strict budget yields different decisions.
      W3 time-drift               : evidence carries observed_at; the same
            facet re-observed at a later time can return a different value.
      W4 multi-candidate-conflict : 3-5 candidates with partial-missing and
            conflicting evidence; no fixed-order max() cheating.
      W5 true-history-branches    : multiple research branches from the same
            start state are recorded; only state-compatible transitions may
            be replayed; cross-world/unknown-action refusals are testable.

    All worlds are deterministic: fixed seed, no real clock.
    """
    import random

    rng = random.Random(seed)

    if kind == "W0":
        # All key evidence visible; no bias. Naive == oracle.
        a = _make_product(
            rng=rng,
            label="w0-a",
            true_margin=0.7,
            true_reliability=0.8,
            true_demand=0.6,
            true_competition=0.3,
            true_risk=0.25,
            viable=True,
        )
        b = _make_product(
            rng=rng,
            label="w0-b",
            true_margin=0.3,
            true_reliability=0.7,
            true_demand=0.55,
            true_competition=0.4,
            true_risk=0.5,
            viable=False,
        )
        observables = {
            a.product_id: _make_observable(product=a, title="W0 Good"),
            b.product_id: _make_observable(product=b, title="W0 Bad"),
        }
        evidence = {
            pid: {
                facet: [
                    _make_evidence(
                        facet=facet,
                        value=truth,
                        truth=truth,
                        source=f"{kind}-{pid}-{facet.value}",
                    )
                ]
                for facet, truth in (
                    (EvidenceFacet.MARGIN, p.true_margin),
                    (EvidenceFacet.DEMAND, p.true_demand),
                    (EvidenceFacet.RISK, p.true_risk),
                )
            }
            for pid, p in ((a.product_id, a), (b.product_id, b))
        }
        return World(
            world_id=world_id,
            split=split,
            products=[a, b],
            observables=observables,
            evidence=evidence,
            difficulty=Difficulty.EASY,
            key_facet=EvidenceFacet.MARGIN,
            world_version="W0-v1",
        )

    if kind == "W1":
        # Hidden risk: observable evidence biased toward the BAD product; the
        # risk facet (key) is only revealed by research. No score tie: the bad
        # product has clearly better observable demand + margin.
        a = _make_product(
            rng=rng,
            label="w1-a",
            true_margin=0.68,
            true_reliability=0.78,
            true_demand=0.58,
            true_competition=0.35,
            true_risk=0.22,
            viable=True,
        )
        b = _make_product(
            rng=rng,
            label="w1-b",
            true_margin=0.30,
            true_reliability=0.72,
            true_demand=0.85,
            true_competition=0.3,
            true_risk=0.55,
            viable=False,
        )
        # Bias observables so B looks better: higher demand, higher margin.
        observables = {
            a.product_id: _make_observable(
                product=a,
                title="W1 Solid",
                bias_margin=-0.15,
                bias_demand=-0.1,
            ),
            b.product_id: _make_observable(
                product=b,
                title="W1 Shiny",
                bias_margin=0.1,
                bias_demand=0.1,
            ),
        }
        evidence = {
            pid: {
                facet: [
                    _make_evidence(
                        facet=facet,
                        value=truth,
                        truth=truth,
                        source=f"{kind}-{pid}-{facet.value}",
                    )
                ]
                for facet, truth in (
                    (EvidenceFacet.MARGIN, p.true_margin),
                    (EvidenceFacet.DEMAND, p.true_demand),
                    (EvidenceFacet.RISK, p.true_risk),
                )
            }
            for pid, p in ((a.product_id, a), (b.product_id, b))
        }
        return World(
            world_id=world_id,
            split=split,
            products=[a, b],
            observables=observables,
            evidence=evidence,
            difficulty=Difficulty.MEDIUM,
            key_facet=EvidenceFacet.RISK,
            world_version="W1-v1",
        )

    if kind == "W2":
        # Budget/value: margin research is EXPENSIVE but high-value; demand is
        # CHEAP but low-value. Under a strict budget, an order that spends on
        # demand first may run out before margin -> wrong decision.
        a = _make_product(
            rng=rng,
            label="w2-a",
            true_margin=0.72,
            true_reliability=0.8,
            true_demand=0.5,
            true_competition=0.3,
            true_risk=0.25,
            viable=True,
        )
        b = _make_product(
            rng=rng,
            label="w2-b",
            true_margin=0.25,
            true_reliability=0.7,
            true_demand=0.9,
            true_competition=0.35,
            true_risk=0.5,
            viable=False,
        )
        # Bias observables: B looks much better on demand (cheap signal).
        observables = {
            a.product_id: _make_observable(product=a, title="W2 A", bias_demand=-0.15),
            b.product_id: _make_observable(product=b, title="W2 B", bias_demand=0.15),
        }
        evidence = {
            pid: {
                facet: [
                    _make_evidence(
                        facet=facet,
                        value=truth,
                        truth=truth,
                        source=f"{kind}-{pid}-{facet.value}",
                    )
                ]
                for facet, truth in (
                    (EvidenceFacet.MARGIN, p.true_margin),
                    (EvidenceFacet.DEMAND, p.true_demand),
                    (EvidenceFacet.RISK, p.true_risk),
                )
            }
            for pid, p in ((a.product_id, a), (b.product_id, b))
        }
        return World(
            world_id=world_id,
            split=split,
            products=[a, b],
            observables=observables,
            evidence=evidence,
            difficulty=Difficulty.MEDIUM,
            key_facet=EvidenceFacet.MARGIN,
            world_version="W2-v1",
            # Margin expensive (3.0), demand cheap (0.5), risk mid (1.5).
            action_costs={
                EvidenceFacet.MARKET: 1.0,
                EvidenceFacet.MARGIN: 3.0,
                EvidenceFacet.RELIABILITY: 1.2,
                EvidenceFacet.COMPETITION: 1.0,
                EvidenceFacet.RISK: 1.5,
                EvidenceFacet.DEMAND: 0.5,
            },
        )

    if kind == "W3":
        # Time drift: demand evidence at t=0 says high; at t=2 it says low.
        # Re-observing after time advances yields a DIFFERENT legal value.
        a = _make_product(
            rng=rng,
            label="w3-a",
            true_margin=0.7,
            true_reliability=0.8,
            true_demand=0.6,
            true_competition=0.3,
            true_risk=0.25,
            viable=True,
        )
        b = _make_product(
            rng=rng,
            label="w3-b",
            true_margin=0.3,
            true_reliability=0.7,
            true_demand=0.6,
            true_competition=0.4,
            true_risk=0.5,
            viable=False,
        )
        observables = {
            a.product_id: _make_observable(product=a, title="W3 A"),
            b.product_id: _make_observable(product=b, title="W3 B"),
        }
        # Demand for A: t=0 high (0.7), t=2 low (0.4) -> a stale-then-corrected
        # signal. Same action, different legal observation at different times.
        evidence = {
            a.product_id: {
                EvidenceFacet.MARGIN: [
                    _make_evidence(
                        facet=EvidenceFacet.MARGIN, value=0.7, truth=0.7, source="w3-a-margin"
                    ),
                ],
                EvidenceFacet.DEMAND: [
                    _make_evidence(
                        facet=EvidenceFacet.DEMAND,
                        value=0.7,
                        truth=0.6,
                        source="w3-a-demand-t0",
                        observed_at=0,
                    ),
                    _make_evidence(
                        facet=EvidenceFacet.DEMAND,
                        value=0.4,
                        truth=0.6,
                        source="w3-a-demand-t2",
                        observed_at=2,
                    ),
                ],
                EvidenceFacet.RISK: [
                    _make_evidence(
                        facet=EvidenceFacet.RISK, value=0.25, truth=0.25, source="w3-a-risk"
                    ),
                ],
            },
            b.product_id: {
                EvidenceFacet.MARGIN: [
                    _make_evidence(
                        facet=EvidenceFacet.MARGIN, value=0.3, truth=0.3, source="w3-b-margin"
                    ),
                ],
                EvidenceFacet.DEMAND: [
                    _make_evidence(
                        facet=EvidenceFacet.DEMAND, value=0.6, truth=0.6, source="w3-b-demand"
                    ),
                ],
                EvidenceFacet.RISK: [
                    _make_evidence(
                        facet=EvidenceFacet.RISK, value=0.5, truth=0.5, source="w3-b-risk"
                    ),
                ],
            },
        }
        return World(
            world_id=world_id,
            split=split,
            products=[a, b],
            observables=observables,
            evidence=evidence,
            difficulty=Difficulty.MEDIUM,
            key_facet=EvidenceFacet.MARGIN,
            world_version="W3-v1",
        )

    if kind == "W4":
        # Multi-candidate + conflict: 4 candidates; some evidence conflicts
        # with truth; one product is genuinely best. No fixed-order max().
        specs = [
            ("w4-a", 0.7, 0.8, 0.6, 0.3, 0.2, True),
            ("w4-b", 0.62, 0.75, 0.55, 0.4, 0.3, True),
            ("w4-c", 0.45, 0.7, 0.5, 0.35, 0.4, False),
            ("w4-d", 0.3, 0.65, 0.45, 0.45, 0.55, False),
        ]
        products = [
            _make_product(
                rng=rng,
                label=label,
                true_margin=m,
                true_reliability=r,
                true_demand=d,
                true_competition=c,
                true_risk=risk,
                viable=v,
            )
            for label, m, r, d, c, risk, v in specs
        ]
        observables = {
            p.product_id: _make_observable(product=p, title=f"W4 {p.product_id[-1]}")
            for p in products
        }
        w4_evidence: dict[str, dict[EvidenceFacet, list[Evidence]]] = {}
        for p in products:
            by_facet = {
                EvidenceFacet.MARGIN: [
                    _make_evidence(
                        facet=EvidenceFacet.MARGIN,
                        value=p.true_margin,
                        truth=p.true_margin,
                        source=f"w4-{p.product_id}-margin",
                    ),
                ],
                EvidenceFacet.DEMAND: [
                    _make_evidence(
                        facet=EvidenceFacet.DEMAND,
                        value=p.true_demand,
                        truth=p.true_demand,
                        source=f"w4-{p.product_id}-demand",
                    ),
                ],
                EvidenceFacet.RISK: [
                    _make_evidence(
                        facet=EvidenceFacet.RISK,
                        value=p.true_risk,
                        truth=p.true_risk,
                        source=f"w4-{p.product_id}-risk",
                    ),
                ],
            }
            # Product C has a conflict: its demand evidence says HIGH but truth
            # is low (conflict_with_truth=True). Identify by the exact uuid
            # derived from its label.
            if p.product_id == str(uuid5(NAMESPACE_URL, "marketpilot:world:diag:w4-c")):
                by_facet[EvidenceFacet.DEMAND] = [
                    _make_evidence(
                        facet=EvidenceFacet.DEMAND,
                        value=0.9,
                        truth=p.true_demand,
                        conflict=True,
                        source="w4-c-demand-conflict",
                    )
                ]
            w4_evidence[p.product_id] = by_facet
        return World(
            world_id=world_id,
            split=split,
            products=products,
            observables=observables,
            evidence=w4_evidence,
            difficulty=Difficulty.HARD,
            key_facet=EvidenceFacet.MARGIN,
            world_version="W4-v1",
        )

    if kind == "W5":
        # True-history branches (Task 4.1): the SAME start state has multiple
        # ALREADY-EXECUTED research branches recorded. The demand facet for
        # the best product carries MULTIPLE evidence entries from DIFFERENT
        # branches (different observed_at / source); a policy that re-queries
        # at a different time or via a different branch sees a different
        # legal observation. Unobserved branches remain rejected by replay.
        a = _make_product(
            rng=rng, label="w5-a", true_margin=0.68, true_reliability=0.78,
            true_demand=0.58, true_competition=0.35, true_risk=0.22, viable=True,
        )
        b = _make_product(
            rng=rng, label="w5-b", true_margin=0.30, true_reliability=0.72,
            true_demand=0.85, true_competition=0.3, true_risk=0.55, viable=False,
        )
        c = _make_product(
            rng=rng, label="w5-c", true_margin=0.45, true_reliability=0.7,
            true_demand=0.6, true_competition=0.4, true_risk=0.4, viable=False,
        )
        observables = {
            a.product_id: _make_observable(
                product=a, title="W5 Branch A", bias_margin=-0.1,
            ),
            b.product_id: _make_observable(
                product=b, title="W5 Branch B", bias_margin=0.1, bias_demand=0.1,
            ),
            c.product_id: _make_observable(product=c, title="W5 Branch C"),
        }
        w5_evidence: dict[str, dict[EvidenceFacet, list[Evidence]]] = {}
        for pid, p in (
            (a.product_id, a), (b.product_id, b), (c.product_id, c),
        ):
            w5_by_facet: dict[EvidenceFacet, list[Evidence]] = {
                EvidenceFacet.MARGIN: [
                    _make_evidence(
                        facet=EvidenceFacet.MARGIN, value=p.true_margin,
                        truth=p.true_margin, source=f"w5-{p.product_id}-margin",
                    )
                ],
                EvidenceFacet.RISK: [
                    _make_evidence(
                        facet=EvidenceFacet.RISK, value=p.true_risk,
                        truth=p.true_risk, source=f"w5-{p.product_id}-risk",
                    )
                ],
            }
            if pid == a.product_id:
                # MULTI-BRANCH demand: branch 1 (t=0) says high, branch 2 (t=2)
                # says low — two legal observations from different branches.
                w5_by_facet[EvidenceFacet.DEMAND] = [
                    _make_evidence(
                        facet=EvidenceFacet.DEMAND, value=0.75, truth=p.true_demand,
                        source="w5-a-demand-branch1", observed_at=0,
                    ),
                    _make_evidence(
                        facet=EvidenceFacet.DEMAND, value=0.45, truth=p.true_demand,
                        source="w5-a-demand-branch2", observed_at=2,
                    ),
                ]
            else:
                w5_by_facet[EvidenceFacet.DEMAND] = [
                    _make_evidence(
                        facet=EvidenceFacet.DEMAND, value=p.true_demand,
                        truth=p.true_demand, source=f"w5-{p.product_id}-demand",
                    )
                ]
            w5_evidence[pid] = w5_by_facet
        return World(
            world_id=world_id, split=split, products=[a, b, c],
            observables=observables, evidence=w5_evidence,
            difficulty=Difficulty.MEDIUM, key_facet=EvidenceFacet.MARGIN,
            world_version="W5-v2",
        )

    raise ValueError(f"unknown diagnostic world kind: {kind}")


def build_diagnostic_worlds(
    *,
    seed: int = 7,
    base_dir: Path,
) -> dict[str, World]:
    """Build the full diagnostic world suite (W0..W5) as dev worlds + a
    confirmation/test trio for each mechanism."""
    kinds = ["W0", "W1", "W2", "W3", "W4", "W5"]
    worlds: dict[str, World] = {}
    for kind in kinds:
        for split, suffix, extra_seed in (
            (WorldSplit.DEV, "dev", 0),
            (WorldSplit.CONFIRMATION, "conf", 1),
            (WorldSplit.TEST, "test", 2),
        ):
            world = build_diagnostic_world(
                kind=kind,
                seed=seed + extra_seed,
                split=split,
                world_id=f"{kind}-{suffix}",
            )
            worlds[world.world_id] = world
    base_dir.mkdir(parents=True, exist_ok=True)
    for world in worlds.values():
        world.save(base_dir)
    write_world_manifest(worlds, base_dir)
    return worlds
