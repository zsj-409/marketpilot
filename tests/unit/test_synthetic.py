"""Synthetic generator tests."""

from pathlib import Path

from marketpilot.synthetic.generator import SyntheticMarketGenerator
from marketpilot.synthetic.validation import validate_dataset


def test_generator_is_reproducible() -> None:
    left = SyntheticMarketGenerator(seed=42).generate()
    right = SyntheticMarketGenerator(seed=42).generate()
    assert [p.model_dump() for p in left[0]] == [p.model_dump() for p in right[0]]


def test_dataset_passes_business_invariants() -> None:
    products, _, reviews, _ = SyntheticMarketGenerator(seed=7).generate()
    issues = validate_dataset(products, review_count=len(reviews))
    assert issues == []


def test_ground_truth_is_not_in_observable_products(tmp_path: Path) -> None:
    generator = SyntheticMarketGenerator(seed=3, products_per_category=4)
    generator.write(tmp_path)
    from marketpilot.synthetic.environment import SyntheticEnvironment

    environment = SyntheticEnvironment(tmp_path)
    product = environment.observable_products("Pet Supplies")[0]
    assert "latent_opportunity_score" not in product
    assert "latent_risk_score" not in product
