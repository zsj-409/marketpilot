"""Benchmark strategy tests."""

from pathlib import Path

from marketpilot.benchmark.strategies import (
    BaselineStrategy,
    BestOfNStrategy,
    VerifierGuidedStrategy,
)
from marketpilot.synthetic.environment import SyntheticEnvironment
from marketpilot.synthetic.generator import SyntheticMarketGenerator


def _environment(tmp_path: Path) -> SyntheticEnvironment:
    SyntheticMarketGenerator(seed=11, products_per_category=5).write(tmp_path)
    return SyntheticEnvironment(tmp_path)


def test_strategies_return_ranked_candidates(tmp_path: Path) -> None:
    environment = _environment(tmp_path)
    for strategy in (
        BaselineStrategy(),
        BestOfNStrategy(n=3),
        VerifierGuidedStrategy(n=3),
    ):
        selected = strategy.select(
            "Pet Supplies", {"minimum_margin": 0.2, "maximum_risk": 0.7}, environment
        )
        assert selected
        assert len(selected) == len(set(selected))
