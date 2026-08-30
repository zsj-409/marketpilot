"""Prompt rendering tests."""

from marketpilot.prompts.templates import build_default_prompt_registry


def test_prompt_rendering_is_deterministic() -> None:
    registry = build_default_prompt_registry()
    variables = {
        "objective": "Find products",
        "market": "US",
        "category": "pet supplies",
        "task": "Research",
        "state_context": "{}",
        "json_schema": "{}",
    }
    first = registry.render("market_research", variables)
    second = registry.render("market_research", variables)
    assert first.text == second.text
    assert first.prompt_hash == second.prompt_hash
    assert first.prompt_hash == second.prompt_hash
    assert first.name == "market_research"
    assert first.version == "v1"


def test_all_prompts_are_registered() -> None:
    registry = build_default_prompt_registry()
    assert {
        "market_research",
        "product_research",
        "review_research",
        "competitor_research",
        "risk_analysis",
        "decision",
    }.issubset(set(registry.names()))
