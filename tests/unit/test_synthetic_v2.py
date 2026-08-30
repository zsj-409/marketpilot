"""Synthetic environment v2 retrieval tests."""

from pathlib import Path

from marketpilot.synthetic.generator import SyntheticMarketGenerator
from marketpilot.synthetic.providers import SyntheticSearchProviderV2, load_synthetic_providers_v2


async def test_v2_different_queries_retrieve_different_facets(tmp_path: Path) -> None:
    SyntheticMarketGenerator(seed=21, products_per_category=4).write(tmp_path)
    search, _ = load_synthetic_providers_v2(tmp_path)
    general = await search.search("best opportunity overview", 3)
    downside = await search.search("downside failure risk", 3)
    constraint = await search.search("constraints eligible required", 3)
    general_facets = {str(item.metadata["evidence_facets"][0]) for item in general}
    downside_facets = {str(item.metadata["evidence_facets"][0]) for item in downside}
    constraint_facets = {str(item.metadata["evidence_facets"][0]) for item in constraint}
    assert general_facets != downside_facets
    assert downside_facets != constraint_facets


async def test_v2_search_has_no_policy_parameter(tmp_path: Path) -> None:
    SyntheticMarketGenerator(seed=21, products_per_category=4).write(tmp_path)
    search = SyntheticSearchProviderV2([])
    results = await search.search("price cost", 2)
    assert results == []
