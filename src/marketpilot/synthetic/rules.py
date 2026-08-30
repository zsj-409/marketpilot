"""Explicit business rules and scoring formulas."""

from marketpilot.synthetic.models import CategoryProfile, MarketRegime

GENERATOR_VERSION = "1.0.0"

CATEGORY_PROFILES: dict[str, CategoryProfile] = {
    category: CategoryProfile(
        category=category,
        price_min=price_min,
        price_max=price_max,
        cogs_ratio=cogs_ratio,
        fulfillment_ratio=fulfillment_ratio,
        shipping_weight=shipping_weight,
        return_rate_baseline=return_rate_baseline,
        regulatory_baseline=regulatory_baseline,
        seasonality=seasonality,
    )
    for (
        category,
        price_min,
        price_max,
        cogs_ratio,
        fulfillment_ratio,
        shipping_weight,
        return_rate_baseline,
        regulatory_baseline,
        seasonality,
    ) in [
        (
            "Pet Supplies",
            12,
            95,
            0.38,
            0.12,
            2.0,
            0.12,
            0.15,
            [1.0, 0.95, 0.9, 0.9, 0.95, 1.0, 1.05, 1.05, 0.95, 0.9, 1.0, 1.1],
        ),
        (
            "Home Organization",
            8,
            80,
            0.34,
            0.10,
            1.2,
            0.08,
            0.05,
            [1.0, 0.95, 1.0, 1.05, 1.05, 1.0, 1.0, 0.95, 1.05, 1.0, 1.05, 1.0],
        ),
        (
            "Kitchen Accessories",
            6,
            70,
            0.32,
            0.10,
            1.0,
            0.09,
            0.12,
            [1.05, 1.0, 0.95, 0.95, 1.0, 1.0, 0.95, 0.95, 1.05, 1.1, 1.2, 1.3],
        ),
        (
            "Outdoor Recreation",
            15,
            220,
            0.42,
            0.16,
            4.0,
            0.10,
            0.22,
            [0.7, 0.7, 0.9, 1.1, 1.25, 1.35, 1.3, 1.2, 1.0, 0.85, 0.75, 0.7],
        ),
        (
            "Beauty Tools",
            10,
            150,
            0.30,
            0.09,
            0.6,
            0.14,
            0.25,
            [1.0, 1.05, 1.0, 1.0, 1.05, 1.0, 0.95, 0.95, 1.0, 1.1, 1.15, 1.2],
        ),
        (
            "Office Accessories",
            8,
            120,
            0.36,
            0.11,
            1.4,
            0.08,
            0.08,
            [0.9, 0.95, 1.0, 1.0, 0.95, 0.9, 0.85, 0.9, 1.05, 1.0, 0.95, 0.9],
        ),
        (
            "Travel Accessories",
            9,
            140,
            0.35,
            0.12,
            1.6,
            0.09,
            0.10,
            [0.9, 0.9, 1.0, 1.1, 1.2, 1.3, 1.35, 1.2, 1.0, 0.9, 0.85, 0.85],
        ),
        (
            "Fitness Accessories",
            10,
            180,
            0.40,
            0.14,
            3.0,
            0.11,
            0.18,
            [1.05, 1.1, 1.05, 1.0, 0.95, 0.9, 0.85, 0.85, 0.95, 1.0, 1.0, 1.05],
        ),
    ]
}

REGIME_PARAMS: dict[MarketRegime, dict[str, float]] = {
    MarketRegime.EMERGING: {
        "volume": 0.35,
        "growth": 0.75,
        "sellers": 0.25,
        "reviews": 0.2,
        "cpc": 0.35,
        "margin": 0.5,
        "differentiation": 0.6,
        "risk": 0.4,
    },
    MarketRegime.GROWING: {
        "volume": 0.55,
        "growth": 0.65,
        "sellers": 0.4,
        "reviews": 0.4,
        "cpc": 0.5,
        "margin": 0.5,
        "differentiation": 0.5,
        "risk": 0.4,
    },
    MarketRegime.MATURE: {
        "volume": 0.75,
        "growth": 0.25,
        "sellers": 0.65,
        "reviews": 0.7,
        "cpc": 0.6,
        "margin": 0.4,
        "differentiation": 0.3,
        "risk": 0.4,
    },
    MarketRegime.SATURATED: {
        "volume": 0.85,
        "growth": 0.05,
        "sellers": 0.95,
        "reviews": 0.95,
        "cpc": 0.9,
        "margin": 0.25,
        "differentiation": 0.15,
        "risk": 0.55,
    },
    MarketRegime.DECLINING: {
        "volume": 0.5,
        "growth": -0.25,
        "sellers": 0.55,
        "reviews": 0.6,
        "cpc": 0.4,
        "margin": 0.3,
        "differentiation": 0.2,
        "risk": 0.5,
    },
    MarketRegime.SEASONAL: {
        "volume": 0.6,
        "growth": 0.15,
        "sellers": 0.5,
        "reviews": 0.5,
        "cpc": 0.55,
        "margin": 0.45,
        "differentiation": 0.4,
        "risk": 0.45,
    },
    MarketRegime.HIGH_MARGIN_NICHE: {
        "volume": 0.3,
        "growth": 0.3,
        "sellers": 0.15,
        "reviews": 0.2,
        "cpc": 0.3,
        "margin": 0.75,
        "differentiation": 0.85,
        "risk": 0.35,
    },
    MarketRegime.HIGH_DEMAND_HIGH_RISK: {
        "volume": 0.9,
        "growth": 0.5,
        "sellers": 0.5,
        "reviews": 0.5,
        "cpc": 0.7,
        "margin": 0.45,
        "differentiation": 0.45,
        "risk": 0.8,
    },
    MarketRegime.LOW_COMPETITION_NICHE: {
        "volume": 0.3,
        "growth": 0.4,
        "sellers": 0.1,
        "reviews": 0.1,
        "cpc": 0.25,
        "margin": 0.65,
        "differentiation": 0.75,
        "risk": 0.3,
    },
    MarketRegime.COMMODITY: {
        "volume": 0.75,
        "growth": 0.05,
        "sellers": 0.9,
        "reviews": 0.9,
        "cpc": 0.8,
        "margin": 0.2,
        "differentiation": 0.1,
        "risk": 0.5,
    },
}


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def compute_margin(selling_price: float, cogs: float, fulfillment: float) -> float:
    return clamp((selling_price - cogs - fulfillment) / selling_price, 0.0, 1.0)


def compute_scores(
    *,
    demand_raw: float,
    margin: float,
    differentiation: float,
    competition_raw: float,
    risk_raw: float,
) -> tuple[float, float, float, float, float]:
    """Return demand, competition, risk, opportunity, and risk complement scores."""

    demand = clamp(demand_raw)
    competition = clamp(competition_raw)
    risk = clamp(risk_raw)
    opportunity = clamp(
        0.35 * demand + 0.25 * margin + 0.20 * differentiation - 0.15 * competition - 0.10 * risk
    )
    return demand, competition, risk, opportunity, risk
