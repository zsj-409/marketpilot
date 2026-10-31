"""Product entity recognition (Phase 1).

Deterministic, offline extraction of product entities from research text.
This is a lightweight recognizer (regex + keyword lexicon), explicitly NOT a
neural NER system. It is sufficient for structured normalization and for
evidence-entity linkage in the synthetic and real pipelines.
"""

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from marketpilot.input.errors import InputError


class ProductEntity(BaseModel):
    """One recognized product-related entity mention."""

    model_config = ConfigDict(frozen=True)

    kind: str = Field(min_length=1, max_length=50)  # category | brand | product | sku
    value: str = Field(min_length=1, max_length=300)
    normalized: str = Field(min_length=1, max_length=300)
    confidence: float = Field(ge=0, le=1)
    span_start: int = Field(ge=0)
    span_end: int = Field(ge=0)


# category keyword lexicon (canonical -> aliases)
_CATEGORY_ALIASES: dict[str, tuple[str, ...]] = {
    "pet supplies": ("pet supplies", "pet", "pet food", "pet feeder"),
    "home organization": ("home organization", "storage", "shelving", "organizer"),
    "kitchen accessories": ("kitchen", "kitchen accessories", "cookware", "utensils"),
    "outdoor recreation": ("outdoor", "camping", "hiking", "hiking gear"),
    "beauty tools": ("beauty", "beauty tools", "hair", "skin care"),
    "office accessories": ("office", "office accessories", "desk", "cables"),
    "travel accessories": ("travel", "luggage", "packing", "travel gear"),
    "fitness accessories": ("fitness", "gym", "fitness accessories", "recovery"),
}

# brand keyword lexicon (canonical -> aliases)
_BRAND_ALIASES: dict[str, tuple[str, ...]] = {
    "nimbus": ("nimbus",),
    "cedar": ("cedar",),
    "aster": ("aster",),
    "lumen": ("lumen",),
    "orbit": ("orbit",),
    "fable": ("fable",),
    "zephyr": ("zephyr",),
    "mosaic": ("mosaic",),
    "harbor": ("harbor",),
    "vertex": ("vertex",),
}

_SKU_RE = re.compile(
    r"(?:sku|item\s*#|item\s*id|asin)[:\s#-]*([A-Za-z0-9][A-Za-z0-9-]{2,30})", re.I
)
_PRODUCT_NAME_RE = re.compile(r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+){0,4})\b")

_CATEGORY_TERMS = tuple(
    alias.lower() for aliases in _CATEGORY_ALIASES.values() for alias in aliases
)
_BRAND_TERMS = tuple(
    alias.lower() for aliases in _BRAND_ALIASES.values() for alias in aliases
)


def extract_product_entities(text: str) -> list[ProductEntity]:
    """Extract product entities from research text deterministically."""
    if not text or not text.strip():
        raise InputError("PARSE", "empty text for entity extraction")
    lowered = text.lower()
    entities: list[ProductEntity] = []

    for canonical, aliases in _CATEGORY_ALIASES.items():
        for alias in aliases:
            index = lowered.find(alias)
            if index >= 0:
                entities.append(
                    ProductEntity(
                        kind="category",
                        value=text[index : index + len(alias)],
                        normalized=canonical,
                        confidence=0.9,
                        span_start=index,
                        span_end=index + len(alias),
                    )
                )
                break

    for canonical, aliases in _BRAND_ALIASES.items():
        for alias in aliases:
            index = lowered.find(alias)
            if index >= 0:
                entities.append(
                    ProductEntity(
                        kind="brand",
                        value=text[index : index + len(alias)],
                        normalized=canonical,
                        confidence=0.8,
                        span_start=index,
                        span_end=index + len(alias),
                    )
                )
                break

    for match in _SKU_RE.finditer(text):
        sku = match.group(1)
        entities.append(
            ProductEntity(
                kind="sku",
                value=sku,
                normalized=sku.upper(),
                confidence=0.7,
                span_start=match.start(),
                span_end=match.end(),
            )
        )

    seen_products: set[str] = set()
    for match in _PRODUCT_NAME_RE.finditer(text):
        candidate = match.group(0)
        lowered_candidate = candidate.lower()
        # Skip pure category/brand mentions and generic filler.
        if lowered_candidate in _CATEGORY_TERMS or lowered_candidate in _BRAND_TERMS:
            continue
        if candidate in seen_products:
            continue
        seen_products.add(candidate)
        entities.append(
            ProductEntity(
                kind="product",
                value=candidate,
                normalized=candidate.lower(),
                confidence=0.5,
                span_start=match.start(),
                span_end=match.end(),
            )
        )

    entities.sort(key=lambda e: e.span_start)
    return entities


def product_entity_summary(entities: list[ProductEntity]) -> dict[str, Any]:
    """Compact deterministic summary used for evidence-entity linkage."""
    return {
        "categories": sorted({e.normalized for e in entities if e.kind == "category"}),
        "brands": sorted({e.normalized for e in entities if e.kind == "brand"}),
        "products": sorted({e.normalized for e in entities if e.kind == "product"}),
        "skus": sorted({e.normalized for e in entities if e.kind == "sku"}),
    }
