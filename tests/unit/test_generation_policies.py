"""Candidate-generation policy tests."""

from pathlib import Path

from marketpilot.benchmark.generation_policies import (
    ConstraintFirstPolicy,
    EvidenceGapFirstPolicy,
    RiskFirstPolicy,
    StaticRankingPolicy,
)
from marketpilot.synthetic.environment import SyntheticEnvironment
from marketpilot.synthetic.generator import SyntheticMarketGenerator


def test_policies_return_stable_ids_and_do_not_read_hidden_truth(tmp_path: Path) -> None:
    SyntheticMarketGenerator(seed=13, products_per_category=4).write(tmp_path)
    environment = SyntheticEnvironment(tmp_path)
    products = environment.observable_products("Pet Supplies", "easy")
    for policy in (
        StaticRankingPolicy(),
        ConstraintFirstPolicy(),
        EvidenceGapFirstPolicy(),
        RiskFirstPolicy(),
    ):
        ranking = policy.rank(products, {"minimum_margin": 0.2, "maximum_risk": 0.7})
        assert ranking
        assert len(ranking) == len(set(ranking))
        assert all("latent_opportunity_score" not in product for product in products)
