"""Release Gate Task 1: Safety Gate full-path coverage tests.

Every final-output path (CLI demo, Workbench /api/run, agent runtime
decision) must go through the SAME gate; pre-gate vs post-gate outcomes
are recorded; an intercepted Unsupported GO counts as a SAFETY
INTERCEPTION, never a successful recommendation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from marketpilot.domain.enums import Decision
from marketpilot.domain.evidence import EvidenceItem
from marketpilot.domain.recommendations import (
    ProductCandidate,
    ProductScore,
    Recommendation,
    RiskFlag,
)
from marketpilot.safety.gateway import gate_recommendation, gate_workbench_run


def _candidate(cid: str = "c1") -> ProductCandidate:
    return ProductCandidate(
        candidate_id=uuid4(), run_id=uuid4(), name="Test Product",
        category="electronics", market="US", provider_product_id=cid,
    )


def _score() -> ProductScore:
    return ProductScore(demand=0.8, trend=0.6, estimated_margin=0.5,
                        competition=0.3, customer_pain_opportunity=0.7,
                        operational_complexity=0.4, regulatory_risk=0.2,
                        overall_score=0.7)


def _risk() -> RiskFlag:
    return RiskFlag(risk_id=uuid4(), run_id=uuid4(), label="market risk",
                    severity=0.4, rationale="medium risk")


def _evidence(facets: list[str] | None = None) -> list[EvidenceItem]:
    from marketpilot.domain.enums import EvidenceSourceType

    facets = facets or ["margin", "demand", "risk"]
    now = datetime.now(UTC)
    return [
        EvidenceItem(
            evidence_id=uuid4(), run_id=uuid4(), task_id=uuid4(),
            source_type=EvidenceSourceType.SEARCH_RESULT, source_uri=f"https://src/{f}",
            retrieved_at=now, content_hash="a" * 8, excerpt=f"{f} evidence",
            confidence=0.9, related_entity=f,
        )
        for f in facets
    ]


def _rec(decision: Decision = Decision.GO) -> Recommendation:
    return Recommendation(
        recommendation_id=uuid4(), run_id=uuid4(), candidate=_candidate(),
        scores=_score(), findings=frozenset({uuid4()}),
        supporting_evidence=frozenset({uuid4()}), risk_flags=frozenset({uuid4()}),
        decision=decision, confidence=0.8, rationale="evidence-supported GO",
    )


def test_cli_path_go_through_gate() -> None:
    """CLI demo path: a supported GO passes; the emission records both layers."""
    gated = gate_recommendation("cli.demo", _rec(), _evidence())
    assert gated.gate_decision == "PASS"
    assert gated.post_gate_outcome == "GO"
    assert gated.pre_gate_outcome == "GO"
    assert gated.gate_reason_codes == []


def test_unsupported_go_is_intercepted_not_success() -> None:
    """Task 1: an unsupported GO must be a SAFETY INTERCEPTION, not a success."""
    gated = gate_recommendation("cli.demo", _rec(), [])
    assert gated.gate_decision == "REFUSED"
    assert gated.gate_reason_codes == ["evidence_insufficient"]
    assert gated.post_gate_outcome == "REFUSED"
    # The pre-gate outcome is still GO — the two layers differ.
    assert gated.pre_gate_outcome == "GO"
    assert gated.post_gate_outcome != gated.pre_gate_outcome


def test_no_recommendation_refused() -> None:
    gated = gate_recommendation("cli.demo", None, _evidence())
    assert gated.gate_decision == "REFUSED"
    assert gated.post_gate_outcome == "REFUSED"


def test_non_go_decision_refused() -> None:
    gated = gate_recommendation("cli.demo", _rec(Decision.NO_GO), _evidence())
    assert gated.gate_decision == "REFUSED"
    assert gated.post_gate_outcome == "REFUSED"


def test_workbench_path_gated() -> None:
    """Workbench /api/run path: GO with full evidence chain passes."""
    chain = {"p1": ["margin", "demand", "risk"]}
    gated = gate_workbench_run("GO", "p1", chain, spent=8.0, world_budget=12.0)
    assert gated.gate_decision == "PASS"
    assert gated.post_gate_outcome == "GO"
    assert gated.path == "workbench.run"


def test_workbench_unsupported_intercepted() -> None:
    """Workbench path: adaptive-voi style GO with no evidence is REFUSED."""
    gated = gate_workbench_run("GO", "p1", {}, spent=9.4, world_budget=12.0)
    assert gated.gate_decision == "REFUSED"
    assert gated.gate_reason_codes == ["evidence_insufficient"]
    assert gated.post_gate_outcome == "REFUSED"


def test_workbench_no_go_refused() -> None:
    gated = gate_workbench_run("INSUFFICIENT", None, {}, spent=2.0,
                               world_budget=12.0)
    assert gated.gate_decision == "REFUSED"
    assert gated.post_gate_outcome == "REFUSED"


def test_emission_record_complete() -> None:
    """The emission record carries path, pre/post outcomes, reasons, time."""
    gated = gate_recommendation("cli.demo", _rec(), [])
    d = gated.to_dict()
    assert d["path"] == "cli.demo"
    assert d["pre_gate_outcome"] == "GO"
    assert d["post_gate_outcome"] == "REFUSED"
    assert d["gate_reason_codes"] == ["evidence_insufficient"]
    assert d["emitted_at"]


def test_gate_is_deterministic_and_strategy_free() -> None:
    """Same inputs -> same verdict, regardless of which strategy produced it."""
    from marketpilot.optimization.dream_rsi import ParameterizedPolicy
    from marketpilot.world.core import AgentWorldView, build_diagnostic_world

    world = build_diagnostic_world(kind="W1", seed=7, world_id="w1")
    results = {}
    for strategy in ["fixed", "missing-evidence", "uncertainty",
                     "adaptive-voi", "contextual-hybrid"]:
        pol = ParameterizedPolicy(strategy=strategy, name=strategy)
        results[strategy] = pol.execute(AgentWorldView(world))
    # Feed the SAME complete evidence + a GO decision to the gate for every
    # strategy: the verdict must be identical (gate is strategy-independent).
    chain = {"p1": ["margin", "demand", "risk"]}
    verdicts = set()
    for result in results.values():
        g = gate_workbench_run(
            result.decision if result.decision == "GO" else "GO",
            "p1", chain, spent=result.total_cost, world_budget=12.0,
        )
        verdicts.add(g.gate_decision)
    # Same evidence + GO -> PASS for every strategy (the gate ignores the
    # strategy name entirely).
    assert verdicts == {"PASS"}
    # And the gate still honors the real decisions: a strategy that actually
    # refused (adaptive-voi on W1) yields REFUSED when its own decision is
    # fed in with no evidence — the gate is authoritative, not the strategy.
    refused = gate_workbench_run(
        results["adaptive-voi"].decision, results["adaptive-voi"].selected_id,
        {}, spent=results["adaptive-voi"].total_cost, world_budget=12.0,
    )
    assert refused.gate_decision == "REFUSED"
