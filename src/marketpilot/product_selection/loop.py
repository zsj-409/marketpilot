"""Bounded closed-loop product-selection runner with selective worker dispatch."""

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from marketpilot.product_selection.controller import TerminationController
from marketpilot.product_selection.critic import DecisionCritic
from marketpilot.product_selection.decision import DecisionModule
from marketpilot.product_selection.models import (
    DecisionCriticVerdict,
    ResearchRound,
    TerminationDecision,
)
from marketpilot.product_selection.workers import FollowUpTask, ResearchEnvironment, WorkerRegistry


class FollowUpEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    task_id: UUID
    worker_role: str
    candidate_id: UUID
    facet: str
    round_number: int


class ProductSelectionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    final_candidate_id: UUID | None = None
    final_verdict: DecisionCriticVerdict | None = None
    termination: TerminationDecision
    rounds: list[ResearchRound] = Field(default_factory=list)
    followup_events: list[FollowUpEvent] = Field(default_factory=list)
    research_rounds: int = 0
    initial_candidates: int = 0
    followup_investigations: int = 0
    unresolved_gaps: int = 0


class ClosedLoopRunner:
    def __init__(
        self,
        critic: DecisionCritic,
        controller: TerminationController,
        decision: DecisionModule,
        workers: WorkerRegistry,
    ) -> None:
        self.critic = critic
        self.controller = controller
        self.decision = decision
        self.workers = workers

    def run(
        self,
        environment: ResearchEnvironment,
        constraints: dict[str, object],
    ) -> ProductSelectionResult:
        initial_candidates = len(environment.candidates())
        dynamic_tasks = 0
        budget = 6
        rounds: list[ResearchRound] = []
        followup_events: list[FollowUpEvent] = []
        final_verdict: DecisionCriticVerdict | None = None
        termination = TerminationDecision.STOP_NO_VIABLE_PATH
        final_candidate: UUID | None = None

        for round_number in range(1, self.controller.max_rounds + 1):
            ranking = self.decision.rank(environment, constraints)
            if not ranking:
                final_verdict = DecisionCriticVerdict.NO_VIABLE_CANDIDATE
                termination = TerminationDecision.STOP_NO_VIABLE_PATH
                break
            selected = ranking[0]
            evidence = environment.evidence(selected)
            candidate_facts = next(
                candidate
                for candidate in environment.candidates()
                if UUID(str(candidate["candidate_id"])) == selected
            )
            output = self.critic.critique(
                selected_candidate_id=selected,
                evidence=evidence,
                constraints=constraints,
                candidate_facts=candidate_facts,
            )
            final_verdict = output.verdict
            termination = self.controller.decide(
                verdict=output.verdict,
                round_number=round_number,
                dynamic_tasks_created=dynamic_tasks,
                budget_remaining=budget,
            )
            completed: list[str] = []
            if termination is TerminationDecision.CONTINUE_TARGETED_RESEARCH:
                for gap in output.gaps:
                    task = FollowUpTask(
                        task_id=uuid4(),
                        candidate_id=selected,
                        facet=gap.facet,
                        worker_role=_worker_for_facet(gap.facet),
                        objective=gap.required_evidence,
                        priority=gap.priority,
                        originating_round=round_number,
                    )
                    role = self.workers.dispatch(task, environment)
                    followup_events.append(
                        FollowUpEvent(
                            task_id=task.task_id,
                            worker_role=role,
                            candidate_id=selected,
                            facet=gap.facet,
                            round_number=round_number,
                        )
                    )
                    dynamic_tasks += 1
                    budget -= 1
                    completed.append(f"{role}:{gap.facet}:{selected}")
            elif termination is TerminationDecision.INVESTIGATE_CONFLICT:
                for conflict in output.conflicts:
                    task = FollowUpTask(
                        task_id=uuid4(),
                        candidate_id=selected,
                        facet=conflict.facet,
                        worker_role=_worker_for_facet(conflict.facet),
                        objective=f"resolve {conflict.facet} conflict",
                        originating_round=round_number,
                    )
                    role = self.workers.dispatch(task, environment)
                    followup_events.append(
                        FollowUpEvent(
                            task_id=task.task_id,
                            worker_role=role,
                            candidate_id=selected,
                            facet=conflict.facet,
                            round_number=round_number,
                        )
                    )
                    dynamic_tasks += 1
                    budget -= 1
                    completed.append(f"{role}:conflict:{conflict.facet}:{selected}")
            elif termination is TerminationDecision.REPLAN_CANDIDATES:
                for candidate in environment.candidates():
                    if _satisfies(candidate, constraints) is False:
                        _mark_ineligible(environment, UUID(str(candidate["candidate_id"])))
                completed.append("replan")

            rounds.append(
                ResearchRound(
                    round_number=round_number,
                    unresolved_gaps=output.gaps,
                    conflicts=output.conflicts,
                    completed_followup_tasks=completed,
                    remaining_budget=budget,
                    termination_reason=termination,
                )
            )
            final_candidate = self.decision.rank(environment, constraints)[0]
            if termination in {
                TerminationDecision.FINISH,
                TerminationDecision.STOP_BUDGET_EXHAUSTED,
                TerminationDecision.STOP_NO_VIABLE_PATH,
            }:
                break

        return ProductSelectionResult(
            final_candidate_id=final_candidate,
            final_verdict=final_verdict,
            termination=termination,
            rounds=rounds,
            followup_events=followup_events,
            research_rounds=len(rounds),
            initial_candidates=initial_candidates,
            followup_investigations=dynamic_tasks,
            unresolved_gaps=sum(len(round.unresolved_gaps) for round in rounds),
        )


def _worker_for_facet(facet: str) -> str:
    if facet in {"risk", "reliability", "returns"}:
        return "review-risk"
    if facet in {"competition", "market"}:
        return "market-competitor"
    return "product"


def _satisfies(candidate: dict[str, object], constraints: dict[str, object]) -> bool:
    if "max_price" in constraints and float(str(candidate.get("price", 0.0))) > float(
        str(constraints["max_price"])
    ):
        return False
    return not (constraints.get("no_battery") and candidate.get("battery"))


def _mark_ineligible(environment: ResearchEnvironment, candidate_id: UUID) -> None:
    environment.add_evidence(candidate_id, "eligibility", "ineligible constraint violation")
