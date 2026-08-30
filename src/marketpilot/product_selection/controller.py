"""Deterministic termination controller."""

from marketpilot.product_selection.models import DecisionCriticVerdict, TerminationDecision


class TerminationController:
    def __init__(self, max_rounds: int = 3, max_dynamic_tasks: int = 6) -> None:
        self.max_rounds = max_rounds
        self.max_dynamic_tasks = max_dynamic_tasks

    def decide(
        self,
        *,
        verdict: DecisionCriticVerdict,
        round_number: int,
        dynamic_tasks_created: int,
        budget_remaining: int,
    ) -> TerminationDecision:
        if verdict is DecisionCriticVerdict.ACCEPT:
            return TerminationDecision.FINISH
        if budget_remaining <= 0 or dynamic_tasks_created >= self.max_dynamic_tasks:
            return TerminationDecision.STOP_BUDGET_EXHAUSTED
        if round_number >= self.max_rounds:
            return TerminationDecision.STOP_BUDGET_EXHAUSTED
        if verdict is DecisionCriticVerdict.CONSTRAINT_FAILURE:
            return TerminationDecision.REPLAN_CANDIDATES
        if verdict is DecisionCriticVerdict.EVIDENCE_CONFLICT:
            return TerminationDecision.INVESTIGATE_CONFLICT
        if verdict is DecisionCriticVerdict.MISSING_EVIDENCE:
            return TerminationDecision.CONTINUE_TARGETED_RESEARCH
        return TerminationDecision.STOP_NO_VIABLE_PATH
