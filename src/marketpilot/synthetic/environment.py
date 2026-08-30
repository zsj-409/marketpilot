"""Synthetic environment that hides latent ground truth from research agents."""

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from marketpilot.synthetic.models import SyntheticProduct


class SyntheticEnvironment:
    """Load a generated dataset and expose only agent-safe observations."""

    def __init__(self, dataset_dir: Path) -> None:
        self.dataset_dir = dataset_dir
        self.products: dict[UUID, SyntheticProduct] = {
            UUID(str(item["product_id"])): SyntheticProduct.model_validate(item)
            for item in self._read_jsonl(dataset_dir / "products.jsonl")
        }
        self.ground_truth: dict[UUID, dict[str, object]] = {
            UUID(str(item["product_id"])): item
            for item in self._read_jsonl(dataset_dir / "ground_truth.jsonl")
        }
        self.sources: list[dict[str, object]] = self._read_jsonl(dataset_dir / "sources.jsonl")

    def observable_products(
        self,
        category: str,
        difficulty: str = "easy",
    ) -> list[dict[str, Any]]:
        """Return agent-safe product observations without latent fields."""

        products = []
        for product in self.products.values():
            if product.category != category:
                continue
            observation = {
                "product_id": str(product.product_id),
                "category": product.category,
                "subcategory": product.subcategory,
                "title": product.title,
                "selling_price": product.selling_price,
                "gross_margin": product.gross_margin,
                "monthly_search_volume": product.monthly_search_volume,
                "search_growth_3m": product.search_growth_3m,
                "search_growth_12m": product.search_growth_12m,
                "seller_count": product.seller_count,
                "median_competitor_reviews": product.median_competitor_reviews,
                "median_competitor_rating": product.median_competitor_rating,
                "rating": product.rating,
                "review_count": product.review_count,
                "return_rate": product.return_rate,
                "complaint_rate": product.complaint_rate,
                "fragile": product.fragile,
                "battery": product.battery,
                "liquid": product.liquid,
                "oversize": product.oversize,
                "regulatory_risk": product.regulatory_risk,
                "ip_risk": product.ip_risk,
                "ad_cpc_proxy": product.ad_cpc_proxy,
                "differentiation_score": product.differentiation_score,
                "demand_score": product.demand_score,
                "competition_score": product.competition_score,
                "risk_score": product.risk_score,
            }
            if difficulty == "medium":
                seed = int(product.product_id.int % 1000)
                observation["demand_score"] = round(
                    max(0.0, min(1.0, product.demand_score + ((seed % 7) - 3) * 0.015)), 4
                )
                observation.pop("differentiation_score", None)
                observation.pop("risk_score", None)
            elif difficulty == "hard":
                seed = int(product.product_id.int % 1000)
                observation["demand_score"] = round(
                    max(0.0, min(1.0, product.demand_score + ((seed % 9) - 4) * 0.02)), 4
                )
                observation["gross_margin"] = round(
                    max(0.0, min(1.0, product.gross_margin + ((seed % 5) - 2) * 0.02)), 4
                )
                observation.pop("differentiation_score", None)
                observation.pop("risk_score", None)
                observation.pop("competition_score", None)
            products.append(observation)
        return products

    def sources_for_category(self, category: str) -> list[dict[str, Any]]:
        return [source for source in self.sources if source.get("category") == category]

    def ground_truth_for(self, product_id: UUID) -> dict[str, object]:
        return self.ground_truth[product_id]

    def _read_jsonl(self, path: Path) -> list[dict[str, object]]:
        with path.open("r", encoding="utf-8") as handle:
            return [dict(json.loads(line)) for line in handle if line.strip()]
