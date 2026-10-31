"""Phase 2: Synthetic Market v3 minimal-world tests.

The core proof: in the minimal world, acquiring the KEY evidence (margin)
flips a wrong decision to the right one; not acquiring it keeps the wrong
decision. Also verifies oracle/agent isolation and world-level split integrity.
"""

import json
from pathlib import Path

import pytest

from marketpilot.input.spec import WorldSplit
from marketpilot.world.core import (
    AgentWorldView,
    DeterministicPolicy,
    EvidenceFacet,
    ResearchAction,
    WorldOracle,
    build_dev_conf_test_worlds,
    build_minimal_world,
    load_worlds,
    write_world_manifest,
)


def _pid(world, label: str) -> str:
    """Resolve the stable product id of the good (viable) or bad product."""
    for product in world.products:
        if label == "good" and product.true_utility > 0.6:
            return product.product_id
        if label == "bad" and product.true_utility <= 0.6:
            return product.product_id
    raise AssertionError(f"no {label} product in world")


def test_minimal_world_key_facet_is_margin() -> None:
    world = build_minimal_world(seed=7)
    assert world.key_facet is EvidenceFacet.MARGIN
    assert world.split is WorldSplit.DEV


def test_minimal_world_observable_bias_makes_naive_choice_wrong() -> None:
    world = build_minimal_world(seed=7)
    oracle = WorldOracle(world)
    good = _pid(world, "good")
    bad = _pid(world, "bad")
    assert oracle.best_product_id() == good
    # The bad product has the biased-high observed margin; a naive choice by
    # observable margin alone would pick the bad product (wrong).
    assert world.observables[bad].observed_margin > world.observables[good].observed_margin


def test_evidence_acquisition_flips_decision() -> None:
    """PROOF: acquiring margin evidence flips the decision to correct."""
    world = build_minimal_world(seed=7)
    oracle = WorldOracle(world)
    good = _pid(world, "good")
    bad = _pid(world, "bad")
    view = AgentWorldView(world)

    # Naive decision from observables only: pick the bad product (wrong).
    naive_scores = {
        pid: obs["observed_margin"]
        for pid, obs in ((pid, view.observable(pid)) for pid in (good, bad))
    }
    naive_best = max(naive_scores, key=lambda pid: naive_scores[pid])
    assert naive_best == bad
    assert oracle.regret(naive_best) > 0.0

    # Acquire margin evidence: the good product's true margin is revealed.
    for pid in (good, bad):
        evidence = view.take_action(ResearchAction.SEARCH_MARGIN, pid)
        assert evidence, "margin action must reveal evidence"
    margin_scores = {}
    for pid in (good, bad):
        entries = view.evidence_summary(pid)["margin"]
        margin_scores[pid] = entries[0]["value"]
    best_after = max(margin_scores, key=lambda pid: margin_scores[pid])
    assert best_after == good
    assert oracle.regret(best_after) == 0.0


def test_wrong_action_keeps_wrong_decision() -> None:
    """Acquiring only DEMAND evidence (not the key facet) keeps the wrong pick."""
    world = build_minimal_world(seed=7)
    oracle = WorldOracle(world)
    good = _pid(world, "good")
    bad = _pid(world, "bad")
    view = AgentWorldView(world)
    for pid in (good, bad):
        view.take_action(ResearchAction.SEARCH_DEMAND, pid)
    scores = {}
    for pid in (good, bad):
        entries = view.evidence_summary(pid).get("demand", [])
        scores[pid] = entries[0]["value"] if entries else 0.0
    best = max(scores, key=lambda pid: scores[pid])
    assert oracle.regret(best) > 0.0


def test_oracle_is_isolated_from_agent_view() -> None:
    """The agent world view exposes no oracle truth."""
    world = build_minimal_world(seed=7)
    good = _pid(world, "good")
    view = AgentWorldView(world)
    observable = view.observable(good)
    assert "true_margin" not in observable
    assert "true_utility" not in observable
    assert "latent" not in json.dumps(view.candidates())
    assert not hasattr(view, "ground_truth_for")


def test_oracle_only_reads_hidden_truth() -> None:
    world = build_minimal_world(seed=7)
    oracle = WorldOracle(world)
    good = _pid(world, "good")
    bad = _pid(world, "bad")
    assert oracle.true_viable(good)
    assert not oracle.true_viable(bad)
    assert oracle.regret(bad) > 0.0
    assert oracle.regret(good) == 0.0


def test_deterministic_policy_with_key_evidence_wins() -> None:
    world = build_minimal_world(seed=7)
    oracle = WorldOracle(world)
    good = _pid(world, "good")
    policy = DeterministicPolicy((ResearchAction.SEARCH_MARGIN, ResearchAction.SEARCH_DEMAND))
    result = policy.run(AgentWorldView(world))
    assert result["selected_id"] == good
    assert oracle.regret(result["selected_id"]) == 0.0


def test_deterministic_policy_without_key_evidence_loses() -> None:
    world = build_minimal_world(seed=7)
    oracle = WorldOracle(world)
    bad = _pid(world, "bad")
    poor = DeterministicPolicy((ResearchAction.SEARCH_DEMAND, ResearchAction.SEARCH_RISK))
    result = poor.run(AgentWorldView(world))
    assert result["selected_id"] == bad
    assert oracle.regret(result["selected_id"]) > 0.0


def test_random_policy_self_check_runs() -> None:
    world = build_minimal_world(seed=7)
    from marketpilot.world.core import RandomPolicy

    result = RandomPolicy().run(AgentWorldView(world))
    assert result["selected_id"] in {p.product_id for p in world.products}


def test_dev_conf_test_worlds_are_distinct_and_frozen(tmp_path: Path) -> None:
    worlds = build_dev_conf_test_worlds(seed=7, base_dir=tmp_path)
    assert set(worlds) == {"minimal-dev", "minimal-confirmation", "minimal-test"}
    assert worlds["minimal-dev"].split is WorldSplit.DEV
    assert worlds["minimal-confirmation"].split is WorldSplit.CONFIRMATION
    assert worlds["minimal-test"].split is WorldSplit.TEST
    for path in tmp_path.glob("world_*.json"):
        assert path.exists()
    write_world_manifest(worlds, tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "v3-minimal"
    assert manifest["worlds"]["minimal-dev"]["split"] == "dev"
    assert manifest["worlds"]["minimal-test"]["split"] == "test"
    hashes = {item["hash"] for item in manifest["worlds"].values()}
    assert len(hashes) == 3


def test_worlds_roundtrip_after_save(tmp_path: Path) -> None:
    build_dev_conf_test_worlds(seed=7, base_dir=tmp_path)
    loaded = load_worlds(tmp_path)
    assert set(loaded) == {"minimal-dev", "minimal-confirmation", "minimal-test"}
    oracle = WorldOracle(loaded["minimal-dev"])
    good = _pid(loaded["minimal-dev"], "good")
    assert oracle.best_product_id() == good
    assert oracle.true_utility(good) == pytest.approx(0.74)
