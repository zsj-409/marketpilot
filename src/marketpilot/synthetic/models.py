"""Typed synthetic market models."""

from datetime import date
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MarketRegime(StrEnum):
    """Explicit market regimes that influence generated features."""

    EMERGING = "emerging"
    GROWING = "growing"
    MATURE = "mature"
    SATURATED = "saturated"
    DECLINING = "declining"
    SEASONAL = "seasonal"
    HIGH_MARGIN_NICHE = "high-margin-niche"
    HIGH_DEMAND_HIGH_RISK = "high-demand-high-risk"
    LOW_COMPETITION_NICHE = "low-competition-niche"
    COMMODITY = "commodity"


class CategoryProfile(BaseModel):
    """Business rules that shape every product in a category."""

    model_config = ConfigDict(frozen=True)

    category: str
    price_min: float
    price_max: float
    cogs_ratio: float = Field(ge=0.1, le=0.9)
    fulfillment_ratio: float = Field(ge=0.02, le=0.5)
    shipping_weight: float = Field(ge=0.1, le=20)
    return_rate_baseline: float = Field(ge=0.0, le=0.5)
    regulatory_baseline: float = Field(ge=0.0, le=1.0)
    seasonality: list[float] = Field(min_length=12, max_length=12)


class SyntheticProduct(BaseModel):
    """A synthetic product with observable features and hidden ground truth."""

    model_config = ConfigDict(frozen=True)

    product_id: UUID
    category: str
    subcategory: str
    brand: str
    title: str
    regime: MarketRegime

    selling_price: float
    estimated_cogs: float
    fulfillment_cost: float
    gross_margin: float

    monthly_search_volume: int
    search_growth_3m: float
    search_growth_12m: float
    seasonality_index: float

    estimated_monthly_units: int
    revenue_proxy: float

    seller_count: int
    competition_density: float
    median_competitor_reviews: int
    median_competitor_rating: float

    rating: float
    review_count: int
    review_velocity: float

    return_rate: float
    complaint_rate: float

    shipping_weight: float
    shipping_volume: float
    fragile: bool
    battery: bool
    liquid: bool
    oversize: bool

    regulatory_risk: float
    ip_risk: float
    saturation_risk: float

    ad_cpc_proxy: float
    acquisition_difficulty: float

    differentiation_score: float
    demand_score: float
    competition_score: float
    risk_score: float
    opportunity_score: float

    latent_opportunity_score: float = 0.0
    latent_risk_score: float = 0.0
    latent_market_state: MarketRegime = MarketRegime.EMERGING


class TrendPoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    product_id: UUID
    month: date
    search_index: float
    units_index: float


class ReviewSnippet(BaseModel):
    model_config = ConfigDict(frozen=True)

    review_id: UUID
    product_id: UUID
    rating: float = Field(ge=1, le=5)
    text: str
    theme: str
    month: date


class SyntheticSource(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: UUID
    category: str
    source_type: str
    title: str
    url: str
    published_at: date
    text: str
    evidence_facets: list[str] = Field(default_factory=list)


class DatasetManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    dataset: str
    version: str
    generator_version: str
    seed: int
    categories: list[str]
    product_count: int
    review_count: int
    source_count: int
    created_at: str
