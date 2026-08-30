"""Deterministic synthetic market generator."""

import json
import random
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from marketpilot.synthetic.models import (
    CategoryProfile,
    DatasetManifest,
    MarketRegime,
    ReviewSnippet,
    SyntheticProduct,
    SyntheticSource,
    TrendPoint,
)
from marketpilot.synthetic.rules import (
    CATEGORY_PROFILES,
    GENERATOR_VERSION,
    REGIME_PARAMS,
    clamp,
    compute_margin,
    compute_scores,
)

DATASET_VERSION = "v1"

_BRANDS = [
    "Nimbus",
    "Cedar",
    "Aster",
    "Lumen",
    "Orbit",
    "Fable",
    "Zephyr",
    "Mosaic",
    "Harbor",
    "Vertex",
]
_SUBCATEGORIES = {
    "Pet Supplies": ["Feeders", "Grooming", "Toys"],
    "Home Organization": ["Storage", "Shelving", "Desk"],
    "Kitchen Accessories": ["Prep", "Storage", "Utensils"],
    "Outdoor Recreation": ["Camping", "Hiking", "Water"],
    "Beauty Tools": ["Skin", "Hair", "Nails"],
    "Office Accessories": ["Desk", "Cables", "Lighting"],
    "Travel Accessories": ["Packing", "Comfort", "Security"],
    "Fitness Accessories": ["Recovery", "Grip", "Mobility"],
}


class SyntheticMarketGenerator:
    """Generate an internally consistent synthetic market from explicit rules."""

    def __init__(self, seed: int = 42, products_per_category: int = 18) -> None:
        self.seed = seed
        self.products_per_category = products_per_category

    def generate(
        self,
    ) -> tuple[
        list[SyntheticProduct], list[TrendPoint], list[ReviewSnippet], list[SyntheticSource]
    ]:
        rng = random.Random(self.seed)
        products: list[SyntheticProduct] = []
        trends: list[TrendPoint] = []
        reviews: list[ReviewSnippet] = []
        sources: list[SyntheticSource] = []

        index = 0
        for category, profile in CATEGORY_PROFILES.items():
            regimes = list(MarketRegime)
            for position in range(self.products_per_category):
                regime = regimes[position % len(regimes)]
                product = self._make_product(rng, profile, regime, category, index)
                products.append(product)
                trends.extend(self._make_trends(product))
                reviews.extend(self._make_reviews(rng, product))
                index += 1
            sources.extend(
                self._make_sources(profile, category, products[-self.products_per_category :])
            )
        return products, trends, reviews, sources

    def _make_product(
        self,
        rng: random.Random,
        profile: CategoryProfile,
        regime: MarketRegime,
        category: str,
        index: int,
    ) -> SyntheticProduct:
        params = REGIME_PARAMS[regime]
        product_id = uuid5(NAMESPACE_URL, f"marketpilot:synthetic:{self.seed}:{index}")
        price = round(rng.uniform(profile.price_min, profile.price_max), 2)
        cogs = round(price * profile.cogs_ratio * rng.uniform(0.92, 1.08), 2)
        fulfillment = round(price * profile.fulfillment_ratio * rng.uniform(0.9, 1.1), 2)
        margin = compute_margin(price, cogs, fulfillment)

        base_volume = 800 + params["volume"] * 9000
        monthly_search_volume = max(50, int(base_volume * rng.uniform(0.85, 1.15)))
        search_growth_3m = round(params["growth"] * rng.uniform(0.9, 1.1), 3)
        search_growth_12m = round(search_growth_3m * rng.uniform(0.7, 1.3), 3)
        seasonality_index = round(1.0 + rng.uniform(-0.25, 0.25), 3)

        seller_count = max(1, int(4 + params["sellers"] * 95 * rng.uniform(0.85, 1.15)))
        median_competitor_reviews = max(0, int(params["reviews"] * 4000 * rng.uniform(0.8, 1.2)))
        median_competitor_rating = round(
            clamp(3.4 + params["sellers"] * 1.1 + rng.uniform(-0.2, 0.2), 1.0, 5.0), 2
        )
        ad_cpc_proxy = round(0.15 + params["cpc"] * 1.6 * rng.uniform(0.9, 1.1), 2)
        acquisition_difficulty = clamp(params["cpc"] + params["sellers"] * 0.35)
        competition_density = clamp(params["sellers"])

        rating = round(clamp(median_competitor_rating + rng.uniform(-0.35, 0.35), 1.0, 5.0), 2)
        review_count = max(1, int(5 + params["reviews"] * 3000 * rng.uniform(0.8, 1.2)))
        review_velocity = round(0.2 + params["growth"] * 0.8, 3)

        fragile = rng.random() < 0.22
        battery = rng.random() < 0.28
        liquid = rng.random() < 0.12
        oversize = profile.shipping_weight > 3.5 or rng.random() < 0.1
        shipping_volume = round(profile.shipping_weight * 0.002 + rng.uniform(0.001, 0.004), 4)
        physical_risk = 0.2 * fragile + 0.25 * battery + 0.2 * liquid + 0.2 * oversize
        return_rate = round(
            clamp(
                profile.return_rate_baseline + physical_risk * 0.12 + params["risk"] * 0.06,
                0.0,
                0.5,
            ),
            3,
        )
        complaint_rate = round(clamp(return_rate * 0.55 + (1 - rating / 5) * 0.12, 0.0, 1.0), 3)

        regulatory_risk = clamp(
            profile.regulatory_baseline + 0.2 * battery + 0.15 * liquid + params["risk"] * 0.25
        )
        ip_risk = round(clamp(params["differentiation"] * 0.15 + rng.uniform(0.0, 0.25)), 3)
        saturation_risk = clamp(params["sellers"])
        risk_raw = clamp(
            0.30 * physical_risk
            + 0.25 * regulatory_risk
            + 0.20 * return_rate
            + 0.15 * saturation_risk
            + 0.10 * ip_risk
        )

        differentiation_score = clamp(params["differentiation"] + rng.uniform(-0.1, 0.1))
        demand_raw = clamp(
            0.45 * params["volume"]
            + 0.35 * max(search_growth_3m, 0.0)
            + 0.2 * (1 - abs(seasonality_index - 1))
        )
        demand_score, competition_score, risk_score, opportunity_score, _ = compute_scores(
            demand_raw=demand_raw,
            margin=margin,
            differentiation=differentiation_score,
            competition_raw=competition_density,
            risk_raw=risk_raw,
        )
        future_demand_realization = clamp(
            params["volume"] * 0.7 + params["growth"] * 0.3 + rng.uniform(-0.25, 0.25)
        )
        future_risk_realization = clamp(risk_raw + rng.uniform(-0.15, 0.15))
        latent_opportunity_score = clamp(0.6 * opportunity_score + 0.4 * future_demand_realization)
        latent_risk_score = clamp(0.6 * risk_score + 0.4 * future_risk_realization)

        estimated_monthly_units = max(
            5, int(monthly_search_volume * 0.018 * (0.7 + params["growth"]))
        )
        revenue_proxy = round(estimated_monthly_units * price, 2)

        return SyntheticProduct(
            product_id=product_id,
            category=category,
            subcategory=rng.choice(_SUBCATEGORIES[category]),
            brand=rng.choice(_BRANDS),
            title=(
                f"{rng.choice(_BRANDS)} {rng.choice(['Pro', 'Air', 'Plus', 'Mini'])} "
                f"{rng.choice(_SUBCATEGORIES[category])}"
            ),
            regime=regime,
            selling_price=price,
            estimated_cogs=cogs,
            fulfillment_cost=fulfillment,
            gross_margin=margin,
            monthly_search_volume=monthly_search_volume,
            search_growth_3m=search_growth_3m,
            search_growth_12m=search_growth_12m,
            seasonality_index=seasonality_index,
            estimated_monthly_units=estimated_monthly_units,
            revenue_proxy=revenue_proxy,
            seller_count=seller_count,
            competition_density=competition_density,
            median_competitor_reviews=median_competitor_reviews,
            median_competitor_rating=median_competitor_rating,
            rating=rating,
            review_count=review_count,
            review_velocity=review_velocity,
            return_rate=return_rate,
            complaint_rate=complaint_rate,
            shipping_weight=round(profile.shipping_weight * rng.uniform(0.8, 1.2), 2),
            shipping_volume=shipping_volume,
            fragile=fragile,
            battery=battery,
            liquid=liquid,
            oversize=oversize,
            regulatory_risk=regulatory_risk,
            ip_risk=ip_risk,
            saturation_risk=saturation_risk,
            ad_cpc_proxy=ad_cpc_proxy,
            acquisition_difficulty=acquisition_difficulty,
            differentiation_score=differentiation_score,
            demand_score=demand_score,
            competition_score=competition_score,
            risk_score=risk_score,
            opportunity_score=opportunity_score,
            latent_opportunity_score=latent_opportunity_score,
            latent_risk_score=latent_risk_score,
            latent_market_state=regime,
        )

    def _make_trends(self, product: SyntheticProduct) -> list[TrendPoint]:
        base_month = date(2025, 1, 1)
        seasonality = CATEGORY_PROFILES[product.category].seasonality
        points: list[TrendPoint] = []
        for offset in range(12):
            month = base_month + timedelta(days=31 * offset)
            month = month.replace(day=1)
            seasonal = seasonality[offset]
            search_index = max(
                0.0,
                round(
                    product.monthly_search_volume
                    * (1 + product.search_growth_3m * offset / 12)
                    * seasonal,
                    2,
                ),
            )
            units_index = max(
                0.0,
                round(
                    product.estimated_monthly_units
                    * (1 + product.search_growth_12m * offset / 12)
                    * seasonal,
                    2,
                ),
            )
            points.append(
                TrendPoint(
                    product_id=product.product_id,
                    month=month,
                    search_index=search_index,
                    units_index=units_index,
                )
            )
        return points

    def _make_reviews(self, rng: random.Random, product: SyntheticProduct) -> list[ReviewSnippet]:
        themes = ["ease of use", "build quality", "value for money"]
        if product.battery:
            themes.append("battery life")
        if product.fragile or product.oversize:
            themes.append("shipping damage")
        if product.liquid:
            themes.append("leakage")
        if product.return_rate > 0.18:
            themes.append("material quality")
        snippets: list[ReviewSnippet] = []
        count = rng.randint(6, 8)
        for i in range(count):
            theme = themes[i % len(themes)]
            snippets.append(
                ReviewSnippet(
                    review_id=uuid5(NAMESPACE_URL, f"marketpilot:review:{product.product_id}:{i}"),
                    product_id=product.product_id,
                    rating=round(
                        clamp(
                            product.rating
                            + rng.uniform(-0.8, 0.8)
                            - (0.3 if product.complaint_rate > 0.2 else 0.0),
                            1,
                            5,
                        ),
                        1,
                    ),
                    text=(
                        f"Customers frequently mention {theme} for this "
                        f"{product.subcategory.lower()} product."
                    ),
                    theme=theme,
                    month=date(2025, (i % 12) + 1, 1),
                )
            )
        return snippets

    def _make_sources(
        self,
        profile: CategoryProfile,
        category: str,
        products: list[SyntheticProduct],
    ) -> list[SyntheticSource]:
        sources: list[SyntheticSource] = []
        summaries = [
            f"{product.title}: price {product.selling_price}, "
            f"review depth {product.median_competitor_reviews}, "
            f"seller count {product.seller_count}, "
            f"return rate {product.return_rate}, ad CPC {product.ad_cpc_proxy}."
            for product in products
        ]
        reviews = [
            f"{product.title}: customers mention battery reliability and ease of use."
            for product in products
        ]
        shipping = [
            f"{product.title}: shipping weight {product.shipping_weight}kg, "
            f"fragile={product.fragile}, battery={product.battery}."
            for product in products
        ]
        sources.append(
            SyntheticSource(
                source_id=uuid5(NAMESPACE_URL, f"marketpilot:source:{category}:market"),
                category=category,
                source_type="market_summary",
                title=f"{category} market summary",
                url=f"https://synthetic.market/{category.lower().replace(' ', '-')}/market",
                published_at=date(2025, 6, 1),
                text=" ".join(summaries),
            )
        )
        sources.append(
            SyntheticSource(
                source_id=uuid5(NAMESPACE_URL, f"marketpilot:source:{category}:reviews"),
                category=category,
                source_type="review_page",
                title=f"{category} customer review themes",
                url=f"https://synthetic.market/{category.lower().replace(' ', '-')}/reviews",
                published_at=date(2025, 7, 1),
                text=" ".join(reviews),
            )
        )
        sources.append(
            SyntheticSource(
                source_id=uuid5(NAMESPACE_URL, f"marketpilot:source:{category}:shipping"),
                category=category,
                source_type="shipping_note",
                title=f"{category} shipping notes",
                url=f"https://synthetic.market/{category.lower().replace(' ', '-')}/shipping",
                published_at=date(2025, 8, 1),
                text=" ".join(shipping),
            )
        )
        return sources

    def write(self, directory: Path) -> DatasetManifest:
        directory.mkdir(parents=True, exist_ok=True)
        products, trends, reviews, sources = self.generate()
        manifest = DatasetManifest(
            dataset="synthetic-market-v1",
            version=DATASET_VERSION,
            generator_version=GENERATOR_VERSION,
            seed=self.seed,
            categories=list(CATEGORY_PROFILES),
            product_count=len(products),
            review_count=len(reviews),
            source_count=len(sources),
            created_at=datetime.now(UTC).isoformat(),
        )
        self._write_jsonl(
            directory / "products.jsonl",
            [
                p.model_dump(
                    mode="json",
                    exclude={
                        "latent_opportunity_score",
                        "latent_risk_score",
                        "latent_market_state",
                    },
                )
                for p in products
            ],
        )
        self._write_jsonl(directory / "trends.jsonl", [t.model_dump(mode="json") for t in trends])
        self._write_jsonl(directory / "reviews.jsonl", [r.model_dump(mode="json") for r in reviews])
        self._write_jsonl(directory / "sources.jsonl", [s.model_dump(mode="json") for s in sources])
        v2_sources = self._make_sources_v2(products)
        self._write_jsonl(
            directory / "sources_v2.jsonl",
            [s.model_dump(mode="json") for s in v2_sources],
        )
        self._write_jsonl(
            directory / "ground_truth.jsonl",
            [
                {
                    "product_id": str(p.product_id),
                    "latent_opportunity_score": p.latent_opportunity_score,
                    "latent_risk_score": p.latent_risk_score,
                    "latent_market_state": p.latent_market_state.value,
                }
                for p in products
            ],
        )
        config = {
            "dataset": manifest.dataset,
            "version": manifest.version,
            "generator_version": manifest.generator_version,
            "seed": self.seed,
            "products_per_category": self.products_per_category,
            "categories": manifest.categories,
        }
        (directory / "generation_config.json").write_text(
            json.dumps(config, indent=2), encoding="utf-8"
        )
        (directory / "manifest.json").write_text(
            manifest.model_dump_json(indent=2), encoding="utf-8"
        )
        return manifest

    def _make_sources_v2(self, products: list[SyntheticProduct]) -> list[SyntheticSource]:
        by_category: dict[str, list[SyntheticProduct]] = {}
        for product in products:
            by_category.setdefault(product.category, []).append(product)

        sources: list[SyntheticSource] = []
        for category, category_products in by_category.items():
            facet_text = {
                "broad": (
                    "Overview comparison. "
                    + " ".join(f"{p.title} at price {p.selling_price}" for p in category_products)
                ),
                "constraints": (
                    "Eligibility constraints and required conditions. "
                    + " ".join(
                        f"{p.title} margin {p.gross_margin:.2f}, risk {p.risk_score:.2f}"
                        for p in category_products
                    )
                ),
                "performance": (
                    "Performance and capability. "
                    + " ".join(
                        f"{p.title} demand {p.demand_score:.2f}, differentiation "
                        f"{p.differentiation_score:.2f}"
                        for p in category_products
                    )
                ),
                "price": (
                    "Price cost and hidden cost. "
                    + " ".join(
                        f"{p.title} price {p.selling_price}, cogs {p.estimated_cogs}, "
                        f"fulfillment {p.fulfillment_cost}"
                        for p in category_products
                    )
                ),
                "reliability": (
                    "Reliability maintenance and durability. "
                    + " ".join(
                        f"{p.title} return rate {p.return_rate}, rating {p.rating}"
                        for p in category_products
                    )
                ),
                "downside": (
                    "Downside failure modes and defects. "
                    + " ".join(
                        f"{p.title} battery={p.battery}, fragile={p.fragile}, "
                        f"complaint {p.complaint_rate}"
                        for p in category_products
                    )
                ),
                "uncertainty": (
                    "Uncertain evidence gaps and missing information. "
                    + " ".join(f"{p.title} evidence is incomplete" for p in category_products)
                ),
                "distractor": (
                    "General lifestyle and unrelated brand content. "
                    + " ".join(
                        f"{p.title} appears in brand storytelling" for p in category_products
                    )
                ),
            }
            for facet, text in facet_text.items():
                sources.append(
                    SyntheticSource(
                        source_id=uuid5(
                            NAMESPACE_URL,
                            f"marketpilot:source-v2:{category}:{facet}",
                        ),
                        category=category,
                        source_type=f"{facet}_facet",
                        title=f"{category} {facet} evidence",
                        url=(
                            f"https://synthetic.market/v2/"
                            f"{category.lower().replace(' ', '-')}/{facet}"
                        ),
                        published_at=date(2025, 9, 1),
                        text=text,
                        evidence_facets=[facet],
                    )
                )
        return sources

    def _write_jsonl(self, path: Path, items: list[dict[str, object]]) -> None:
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for item in items:
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")
