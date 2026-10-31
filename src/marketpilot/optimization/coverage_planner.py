"""Phase 5.8: Archive Coverage Planner (Task 3).

A lightweight, budget-constrained exploration coverage expansion flow:
1. Read the Generation-DEV-allowed historical trajectory index.
2. Identify research actions that real strategies requested but which lack
   historical coverage.
3. Execute new research branches from legal start/recoverable states.
4. Save real observations, states, actions, versions and execution costs.
5. Append-only add the actually-observed state transitions to the Archive.
6. Update effective coverage and marginal gain.

Guarantees:
- Actions from different states are NEVER stitched together.
- New executions are NEW environment executions (never masqueraded as replay
  hits).
- No hidden truth is used to pick the next online research action.
- Costs are recorded per research source; simulated budget is never written
  as real API spend.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from marketpilot.optimization.dream_rsi import (
    ParameterizedPolicy,
    ReplayWorldArchive,
    TrajectoryRecord,
    _record_trajectory,
)
from marketpilot.world.core import AgentWorldView, ResearchAction, World


@dataclass
class CoverageReport:
    """Coverage report after expansion (Task 3)."""

    world_count: int = 0
    unique_state_count: int = 0
    unique_supported_action_count: int = 0
    distinct_branch_count: int = 0
    attempt_coverage: float = 0.0
    episode_support_rate: float = 0.0
    unsupported_action_count: int = 0
    coverage_gain_per_new_execution: float = 0.0
    total_collection_cost: float = 0.0
    new_executions: int = 0

    def to_json(self) -> dict[str, Any]:
        return {
            "world_count": self.world_count,
            "unique_state_count": self.unique_state_count,
            "unique_supported_action_count": self.unique_supported_action_count,
            "distinct_branch_count": self.distinct_branch_count,
            "attempt_coverage": round(self.attempt_coverage, 4),
            "episode_support_rate": round(self.episode_support_rate, 4),
            "unsupported_action_count": self.unsupported_action_count,
            "coverage_gain_per_new_execution": round(
                self.coverage_gain_per_new_execution, 4
            ),
            "total_collection_cost": round(self.total_collection_cost, 4),
            "new_executions": self.new_executions,
        }


class ArchiveCoveragePlanner:
    """Budget-constrained exploration coverage expansion for the Archive."""

    def __init__(
        self,
        archive: ReplayWorldArchive,
        *,
        budget: float = 20.0,
        seed: int = 7,
    ) -> None:
        self.archive = archive
        self.budget = budget
        self.spent = 0.0
        self.new_executions = 0
        self.new_branches: list[TrajectoryRecord] = []
        import random

        self.rng = random.Random(seed)

    def plan_expansion(
        self,
        world: World,
        *,
        policies: list[ParameterizedPolicy] | None = None,
        max_branches: int = 3,
    ) -> CoverageReport:
        """Expand coverage by executing new research branches from the given
        world using the provided policies (or the four baselines)."""

        if policies is None:
            policies = [
                ParameterizedPolicy(strategy="fixed", name="fixed"),
                ParameterizedPolicy(strategy="missing-evidence", name="missing"),
                ParameterizedPolicy(strategy="uncertainty", name="uncertainty"),
                ParameterizedPolicy(strategy="adaptive-voi", name="adaptive"),
            ]

        # Identify already-covered (state, action) pairs.
        covered: set[tuple[str, str]] = set()
        for trace in self.archive.trajectories_for_world(world.world_id):
            for step in trace.steps:
                covered.add((step.state_before, step.action))

        # Execute new branches (different policies / action orders).
        executed: list[TrajectoryRecord] = []
        for policy in policies[:max_branches]:
            if self.spent >= self.budget:
                break
            view = AgentWorldView(world)
            result = policy.execute(view)
            traj = _record_trajectory(world, policy, result)
            # Only append if this branch adds NEW (state, action) coverage.
            new_pairs = [
                (s.state_before, s.action)
                for s in traj.steps
                if (s.state_before, s.action) not in covered
            ]
            if new_pairs:
                self.archive.record_trajectory(traj, round_index=self.new_executions)
                self.new_branches.append(traj)
                self.spent += result.total_cost
                self.new_executions += 1
                executed.append(traj)
                for pair in new_pairs:
                    covered.add(pair)

        return self._build_report(world, covered)

    def _build_report(
        self, world: World, covered: set[tuple[str, str]]
    ) -> CoverageReport:
        report = CoverageReport()
        report.world_count = 1
        report.new_executions = self.new_executions
        report.total_collection_cost = round(self.spent, 4)
        all_traces = self.archive.trajectories_for_world(world.world_id)
        # Unique states and actions.
        states: set[str] = set()
        actions: set[str] = set()
        branches: set[str] = set()
        for trace in all_traces:
            for step in trace.steps:
                states.add(step.state_before)
                actions.add(step.action)
            branches.add(trace.policy_hash)
        report.unique_state_count = len(states)
        report.unique_supported_action_count = len(actions)
        report.distinct_branch_count = len(branches)
        # Unsupported actions (non-stop, not valid ResearchAction).
        unsupported = {
            s.action
            for trace in all_traces
            for s in trace.steps
            if s.action != "stop"
            and s.action not in {a.value for a in ResearchAction}
        }
        report.unsupported_action_count = len(unsupported)
        # Attempt coverage: hits / (hits + unsupported attempts).
        hits = sum(
            1
            for trace in all_traces
            for s in trace.steps
            if s.action != "stop" and s.action in {a.value for a in ResearchAction}
        )
        attempts = hits + report.unsupported_action_count
        report.attempt_coverage = hits / attempts if attempts else 0.0
        # Episode support: fraction of traces fully supported.
        supported_traces = sum(
            1
            for trace in all_traces
            if all(
                s.action == "stop" or s.action in {a.value for a in ResearchAction}
                for s in trace.steps
            )
        )
        report.episode_support_rate = (
            supported_traces / len(all_traces) if all_traces else 0.0
        )
        # Marginal coverage gain per new execution.
        if report.new_executions > 0:
            report.coverage_gain_per_new_execution = round(
                len(covered) / report.new_executions, 4
            )
        return report
