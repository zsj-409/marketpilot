"""Deterministic research strategies over synthetic observations."""

import math
from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from marketpilot.memory.episodic import Episode, EpisodicMemory
from marketpilot.memory.skills import SkillMemory
from marketpilot.synthetic.environment import SyntheticEnvironment
from marketpilot.verifier.verifier import verify_recommendation


def observable_opportunity(product: dict[str, Any]) -> float:
    """A transparent heuristic over agent-safe features."""

    demand = float(product.get("demand_score", 0.0))
    margin = float(product.get("gross_margin", 0.0))
    differentiation = float(product.get("differentiation_score", 0.0))
    competition = float(product.get("competition_score", 0.0))
    risk = float(product.get("risk_score", 0.0))
    return max(
        0.0,
        min(
            1.0,
            0.35 * demand
            + 0.25 * margin
            + 0.20 * differentiation
            - 0.15 * competition
            - 0.10 * risk,
        ),
    )


def weighted_opportunity(product: dict[str, Any], weights: dict[str, float]) -> float:
    return sum(
        weights[key] * float(product.get(key, 0.0))
        for key in (
            "demand_score",
            "gross_margin",
            "differentiation_score",
            "competition_score",
            "risk_score",
        )
    )


class ResearchStrategy(ABC):
    name = "strategy"

    @abstractmethod
    def select(
        self,
        category: str,
        constraints: dict[str, float],
        environment: SyntheticEnvironment,
        difficulty: str = "easy",
    ) -> list[UUID]:
        """Return ranked candidate product IDs."""


class BaselineStrategy(ResearchStrategy):
    name = "baseline"

    def select(
        self,
        category: str,
        constraints: dict[str, float],
        environment: SyntheticEnvironment,
        difficulty: str = "easy",
    ) -> list[UUID]:
        products = environment.observable_products(category, difficulty)
        ranked = sorted(products, key=observable_opportunity, reverse=True)
        return [UUID(item["product_id"]) for item in ranked]


class BestOfNStrategy(ResearchStrategy):
    name = "best-of-n"

    def __init__(self, n: int = 4, seed: int = 42) -> None:
        self.n = max(1, n)
        self.seed = seed

    def select(
        self,
        category: str,
        constraints: dict[str, float],
        environment: SyntheticEnvironment,
        difficulty: str = "easy",
    ) -> list[UUID]:
        products = environment.observable_products(category, difficulty)
        best: list[UUID] = []
        best_score = -math.inf
        for variant in range(self.n):
            angle = 2 * math.pi * variant / self.n
            weights = {
                "demand_score": 0.5 + 0.2 * math.sin(angle),
                "gross_margin": 0.5 + 0.2 * math.cos(angle),
                "differentiation_score": 0.4,
                "competition_score": -0.4,
                "risk_score": -0.3,
            }
            ranked = sorted(
                products,
                key=lambda product: weighted_opportunity(product, weights),
                reverse=True,
            )
            top = ranked[:5]
            score = sum(
                float(product.get("demand_score", 0.0))
                + float(product.get("gross_margin", 0.0))
                - float(product.get("competition_score", 0.0))
                - float(product.get("risk_score", 0.0))
                for product in top
            )
            if score > best_score:
                best_score = score
                best = [UUID(item["product_id"]) for item in ranked]
        return best


class VerifierGuidedStrategy(ResearchStrategy):
    name = "verifier-best-of-n"

    def __init__(self, n: int = 4, seed: int = 42) -> None:
        self.n = max(1, n)
        self.seed = seed

    def select(
        self,
        category: str,
        constraints: dict[str, float],
        environment: SyntheticEnvironment,
        difficulty: str = "easy",
    ) -> list[UUID]:
        products = environment.observable_products(category, difficulty)
        sources = environment.sources_for_category(category)
        distinct_domains = len({source.get("url", "") for source in sources})

        def verifier_score(product: dict[str, object]) -> float:
            result = verify_recommendation(
                product=product,
                constraints=constraints,
                evidence_count=1 if sources else 0,
                snapshot_count=1 if sources else 0,
                distinct_domains=distinct_domains,
                risk_covered=True,
            )
            return result.score.total

        ranked = sorted(products, key=verifier_score, reverse=True)
        return [UUID(item["product_id"]) for item in ranked]


class AdaptivePlannerStrategy(ResearchStrategy):
    name = "adaptive-planner"

    def select(
        self,
        category: str,
        constraints: dict[str, float],
        environment: SyntheticEnvironment,
        difficulty: str = "easy",
    ) -> list[UUID]:
        products = environment.observable_products(category, difficulty)
        if difficulty != "hard":
            ranked = sorted(products, key=observable_opportunity, reverse=True)
            return [UUID(str(item["product_id"])) for item in ranked]

        augmented: list[dict[str, Any]] = []
        for product in products:
            item = dict(product)
            item["competition_score"] = max(
                0.0,
                min(
                    1.0,
                    0.55 * float(str(product.get("seller_count", 0))) / 100.0
                    + 0.45 * float(str(product.get("ad_cpc_proxy", 0.0))) / 2.0,
                ),
            )
            item["risk_score"] = max(
                0.0,
                min(
                    1.0,
                    0.3 * float(str(product.get("return_rate", 0.0)))
                    + 0.3 * float(str(product.get("complaint_rate", 0.0)))
                    + 0.2 * float(bool(product.get("battery", False)))
                    + 0.2 * float(bool(product.get("fragile", False))),
                ),
            )
            item["differentiation_score"] = max(
                0.0,
                min(1.0, 0.3 + 0.4 * float(str(product.get("review_velocity", 0.0)))),
            )
            augmented.append(item)
        ranked = sorted(augmented, key=observable_opportunity, reverse=True)
        return [UUID(str(item["product_id"])) for item in ranked]


class EpisodicMemoryStrategy(ResearchStrategy):
    name = "episodic-memory"

    def __init__(self) -> None:
        self.memory = EpisodicMemory()
        self.retrieval_hits = 0

    def select(
        self,
        category: str,
        constraints: dict[str, float],
        environment: SyntheticEnvironment,
        difficulty: str = "easy",
    ) -> list[UUID]:
        self.retrieval_hits += len(
            self.memory.retrieve(category=category, constraints=set(constraints))
        )
        products = environment.observable_products(category, difficulty)
        ranked = sorted(products, key=observable_opportunity, reverse=True)
        selected = [UUID(str(item["product_id"])) for item in ranked]
        if selected:
            self.memory.store(
                Episode(
                    episode_id=str(selected[0]),
                    category=category,
                    task_type="Selection",
                    constraints=frozenset(constraints),
                    evidence_patterns=("selection",),
                )
            )
        return selected


class SkillMemoryStrategy(ResearchStrategy):
    name = "skill-memory"

    def __init__(self) -> None:
        self.memory = EpisodicMemory()
        self.skills = SkillMemory()
        self.retrieval_hits = 0

    def select(
        self,
        category: str,
        constraints: dict[str, float],
        environment: SyntheticEnvironment,
        difficulty: str = "easy",
    ) -> list[UUID]:
        episodes = self.memory.retrieve(category=category, constraints=set(constraints))
        self.retrieval_hits += len(episodes)
        if episodes:
            self.skills.extract(episodes[0])
        products = environment.observable_products(category, difficulty)
        ranked = sorted(products, key=observable_opportunity, reverse=True)
        selected = [UUID(str(item["product_id"])) for item in ranked]
        if selected:
            episode = Episode(
                episode_id=str(selected[0]),
                category=category,
                task_type="Selection",
                constraints=frozenset(constraints),
                evidence_patterns=("selection", "battery", "shipping"),
            )
            self.memory.store(episode)
            self.skills.extract(episode)
        return selected


def strategy_for(name: str, n: int = 4, seed: int = 42) -> ResearchStrategy:
    if name == "best-of-n":
        return BestOfNStrategy(n=n, seed=seed)
    if name == "verifier-best-of-n":
        return VerifierGuidedStrategy(n=n, seed=seed)
    if name == "adaptive-planner":
        return AdaptivePlannerStrategy()
    if name == "episodic-memory":
        return EpisodicMemoryStrategy()
    if name == "skill-memory":
        return SkillMemoryStrategy()
    return BaselineStrategy()
