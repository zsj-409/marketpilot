"""Closed-loop product selection acceptance scenarios."""

from uuid import UUID, uuid4

from marketpilot.product_selection.controller import TerminationController
from marketpilot.product_selection.critic import DecisionCritic
from marketpilot.product_selection.decision import DecisionModule
from marketpilot.product_selection.loop import ClosedLoopRunner
from marketpilot.product_selection.mock_environment import MockResearchEnvironment
from marketpilot.product_selection.models import DecisionCriticVerdict, TerminationDecision
from marketpilot.product_selection.workers import WorkerRegistry


def _runner(max_rounds: int = 3) -> ClosedLoopRunner:
    return ClosedLoopRunner(
        DecisionCritic(),
        TerminationController(max_rounds=max_rounds, max_dynamic_tasks=6),
        DecisionModule(),
        WorkerRegistry(),
    )


def test_scenario_d_accepts_without_research() -> None:
    env = MockResearchEnvironment(
        [
            {
                "candidate_id": str(uuid4()),
                "title": "Candidate A",
                "price": 40.0,
                "battery": False,
            }
        ]
    )
    result = _runner().run(env, {"max_price": 80, "no_battery": False})
    assert result.termination is TerminationDecision.FINISH
    assert result.followup_events == []
    assert result.research_rounds == 1


def test_scenario_a_gap_changes_decision() -> None:
    first = str(uuid4())
    second = str(uuid4())
    env = MockResearchEnvironment(
        [
            {"candidate_id": first, "title": "Candidate A", "price": 40.0, "battery": False},
            {"candidate_id": second, "title": "Candidate B", "price": 55.0, "battery": False},
        ]
    )
    env._evidence[UUID(first)].pop("risk", None)
    before = _runner().decision.rank(env, {"max_price": 80, "no_battery": False})[0]
    result = _runner(max_rounds=3).run(env, {"max_price": 80, "no_battery": False})
    after = _runner().decision.rank(env, {"max_price": 80, "no_battery": False})[0]
    assert before == UUID(first)
    assert result.followup_events
    assert "risk" in env.evidence(UUID(first))
    assert after != before
    assert result.research_rounds >= 2


def test_scenario_b_constraint_rejection() -> None:
    candidate = str(uuid4())
    env = MockResearchEnvironment(
        [{"candidate_id": candidate, "title": "Candidate A", "price": 40.0, "battery": True}]
    )
    result = _runner(max_rounds=3).run(env, {"max_price": 80, "no_battery": True})
    assert result.final_verdict is not DecisionCriticVerdict.ACCEPT
    assert "eligibility" in env.evidence(UUID(candidate))


def test_scenario_c_conflict_research() -> None:
    candidate = str(uuid4())
    env = MockResearchEnvironment(
        [{"candidate_id": candidate, "title": "Candidate A", "price": 40.0, "battery": False}]
    )
    env._evidence[UUID(candidate)]["risk"] = ["conflict"]
    result = _runner(max_rounds=3).run(env, {"max_price": 80, "no_battery": False})
    assert any(event.facet == "risk" for event in result.followup_events)


def test_scenario_e_budget_exhaustion() -> None:
    candidate = str(uuid4())
    env = MockResearchEnvironment(
        [{"candidate_id": candidate, "title": "Candidate A", "price": 40.0, "battery": False}]
    )
    env._evidence[UUID(candidate)].pop("risk", None)
    result = _runner(max_rounds=1).run(env, {"max_price": 80, "no_battery": False})
    assert result.termination is TerminationDecision.STOP_BUDGET_EXHAUSTED
    assert result.unresolved_gaps >= 0
