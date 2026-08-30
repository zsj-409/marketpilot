"""Explainable candidate-generation policies for DEV experiments."""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID


def _feature(product: dict[str, Any], key: str) -> float:
    value = product.get(key)
    return float(str(value)) if value is not None else 0.0


class GenerationPolicy(ABC):
    name = "generation"

    @abstractmethod
    def rank(
        self,
        products: list[dict[str, Any]],
        constraints: dict[str, float],
    ) -> list[UUID]:
        """Return candidate IDs in preference order."""


class StaticRankingPolicy(GenerationPolicy):
    name = "static-ranking"

    def rank(
        self,
        products: list[dict[str, Any]],
        constraints: dict[str, float],
    ) -> list[UUID]:
        return [
            UUID(str(product["product_id"]))
            for product in sorted(products, key=_opportunity, reverse=True)
        ]


class ConstraintFirstPolicy(GenerationPolicy):
    name = "constraint-first"

    def rank(
        self,
        products: list[dict[str, Any]],
        constraints: dict[str, float],
    ) -> list[UUID]:
        minimum_margin = constraints.get("minimum_margin", 0.0)
        maximum_risk = constraints.get("maximum_risk", 1.0)

        def viable(product: dict[str, Any]) -> bool:
            return (
                _feature(product, "gross_margin") >= minimum_margin
                and _feature(product, "risk_score") <= maximum_risk
            )

        viable_products = [product for product in products if viable(product)]
        fallback = [product for product in products if product not in viable_products]
        ranked = sorted(viable_products, key=_opportunity, reverse=True)
        ranked.extend(sorted(fallback, key=_opportunity, reverse=True))
        return [UUID(str(product["product_id"])) for product in ranked]


class EvidenceGapFirstPolicy(GenerationPolicy):
    name = "evidence-gap-first"

    def rank(
        self,
        products: list[dict[str, Any]],
        constraints: dict[str, float],
    ) -> list[UUID]:
        def evidence_score(product: dict[str, Any]) -> float:
            review_depth = min(_feature(product, "review_count") / 2000.0, 1.0)
            return review_depth + (1.0 - _feature(product, "return_rate"))

        def score(product: dict[str, Any]) -> float:
            return 0.7 * _opportunity(product) + 0.3 * evidence_score(product)

        ranked = sorted(products, key=score, reverse=True)
        return [UUID(str(product["product_id"])) for product in ranked]


class RiskFirstPolicy(GenerationPolicy):
    name = "risk-first"

    def rank(
        self,
        products: list[dict[str, Any]],
        constraints: dict[str, float],
    ) -> list[UUID]:
        def downside(product: dict[str, Any]) -> float:
            return (
                0.4 * _feature(product, "risk_score")
                + 0.3 * _feature(product, "return_rate")
                + 0.2 * _feature(product, "complaint_rate")
                + 0.1 * float(bool(product.get("battery")))
            )

        def score(product: dict[str, Any]) -> float:
            return _opportunity(product) - 0.35 * downside(product)

        ranked = sorted(products, key=score, reverse=True)
        return [UUID(str(product["product_id"])) for product in ranked]


def _opportunity(product: dict[str, Any]) -> float:
    return (
        0.35 * _feature(product, "demand_score")
        + 0.25 * _feature(product, "gross_margin")
        + 0.20 * _feature(product, "differentiation_score")
        - 0.15 * _feature(product, "competition_score")
        - 0.10 * _feature(product, "risk_score")
    )


def policy_for(name: str) -> GenerationPolicy:
    if name == "constraint-first":
        return ConstraintFirstPolicy()
    if name == "evidence-gap-first":
        return EvidenceGapFirstPolicy()
    if name == "risk-first":
        return RiskFirstPolicy()
    return StaticRankingPolicy()
