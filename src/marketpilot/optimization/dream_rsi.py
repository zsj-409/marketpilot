"""Phase 5: Dream-RSI core — recursive self-improvement through evolving worlds.

Components implemented in this phase (V2 spec §9):
- ExplorationTree: records observed actions and outcomes per world prefix.
- ReplayWorldArchive: append-only store of worlds + observed trajectories.
- Prefix-only Policy Interface: policies are parameter vectors; the optimizer
  only ever replays prefixes that were actually observed (no future branches).
- Historical Replay Simulator: replays recorded state transitions; unknown
  actions are REJECTED (rule 4); coverage is reported explicitly.
- Policy Proposal + Dream Evaluation + Policy Registry + Promotion/Rollback +
  Recursive Optimization Loop.

Rules honored:
- Historical replay only replays observed state transitions (rule 4).
- Replay coverage is explicit; unseen future branches are never used.
- No policy code reads hidden truth; oracle access stays evaluator-side.
- Candidate policies must pass offline tests, static checks, replay, and
  independent Confirmation DEV before promotion.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from marketpilot.optimization.proposer import MultiFamilyProposer

from marketpilot.evaluation.outcomes import (
    REQUIRED_FACETS,
    evidence_sufficient_for,
)
from marketpilot.policy.controller import ControllerResult, StopReason
from marketpilot.world.core import (
    AgentWorldView,
    EvidenceFacet,
    ResearchAction,
    World,
    WorldOracle,
)

# Policy parameter schema: weights over evidence facets + thresholds.
PARAM_KEYS = tuple(
    [f"weight_{facet.value}" for facet in EvidenceFacet]
    + ["voi_threshold", "refuse_threshold"]
)
DEFAULT_PARAMS: dict[str, float] = {
    "weight_market": 0.0,
    "weight_margin": 0.5,
    "weight_reliability": 0.1,
    "weight_competition": -0.15,
    "weight_risk": -0.2,
    "weight_demand": 0.3,
    "voi_threshold": 0.04,
    "refuse_threshold": 0.20,
}


class PolicyStatus(StrEnum):
    PROPOSED = "proposed"
    DREAM_EVALUATED = "dream_evaluated"
    REPLAY_VERIFIED = "replay_verified"
    CONFIRMATION_PASSED = "confirmation_passed"
    PROMOTED = "promoted"
    ROLLED_BACK = "rolled_back"
    # Outcome classification (Task C.7): a promoted/rolled-back policy is
    # labelled by how it compared to the previous active policy.
    IMPROVED = "improved"
    EFFICIENCY_GAIN = "efficiency_gain"
    TIED = "tied"
    REGRESSED = "regressed"
    INVALID = "invalid"


class PromotionKind(StrEnum):
    """Why a policy was promoted. Distinct from raw status: two policies can
    both be PROMOTED but one is an IMPROVEMENT (better decision quality) while
    the other is an EFFICIENCY_GAIN (same quality, lower cost) or a TIE."""

    IMPROVED = "improved"
    EFFICIENCY_GAIN = "efficiency_gain"
    TIED = "tied"
    REGRESSED = "regressed"
    INVALID = "invalid"


class ReplayOutcome(StrEnum):
    HIT = "hit"
    REJECTED_UNKNOWN_ACTION = "rejected_unknown_action"
    COVERAGE_GAP = "coverage_gap"


@dataclass(frozen=True)
class ObservedStep:
    """One observed (state-before, action, state-after) transition."""

    step_index: int
    action: str
    state_before: str
    state_after: str
    cost: float
    decision: str
    # Target product of the research action (None for stop / legacy records).
    product_id: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "step_index": self.step_index,
            "action": self.action,
            "state_before": self.state_before,
            "state_after": self.state_after,
            "cost": self.cost,
            "decision": self.decision,
            "product_id": self.product_id,
        }


@dataclass
class TrajectoryRecord:
    """A recorded trajectory of a policy over one world (observed transitions)."""

    world_id: str
    split: str
    policy_hash: str
    steps: list[ObservedStep] = field(default_factory=list)
    outcome: str = "UNKNOWN"
    total_cost: float = 0.0

    def to_json(self) -> dict[str, Any]:
        return {
            "world_id": self.world_id,
            "split": self.split,
            "policy_hash": self.policy_hash,
            "outcome": self.outcome,
            "total_cost": self.total_cost,
            "steps": [step.to_json() for step in self.steps],
        }


def policy_hash(params: dict[str, float]) -> str:
    """Deterministic hash of a policy parameter vector."""
    merged = dict(DEFAULT_PARAMS)
    merged.update(params)
    payload = json.dumps({key: round(merged[key], 6) for key in PARAM_KEYS}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]

def view_cost_config(view: AgentWorldView) -> dict[EvidenceFacet, float]:
    """Extract the world's action costs for controller configuration (W2)."""
    return dict(view._world.costs)


def _world_has_time_drift(view: AgentWorldView) -> bool:
    """Task E: True if any evidence in the world carries multiple observed_at
    versions (W3 time drift), which makes refresh re-queries meaningful."""
    world = view._world
    for by_facet in world.evidence.values():
        for entries in by_facet.values():
            stamps = {e.observed_at for e in entries if e.observed_at is not None}
            if len(stamps) > 1:
                return True
    return False


class ParameterizedPolicy:
    """Prefix-only policy interface: a parameter vector that consumes an
    AgentWorldView (never the oracle) and returns a ControllerResult.
    The execution budget and action costs are configurable per call so the
    SAME policy can be evaluated under different budgets (Task 4)."""

    def __init__(
        self,
        params: dict[str, float] | None = None,
        *,
        name: str = "param-policy",
        strategy: str = "adaptive-voi",
    ) -> None:
        merged = dict(DEFAULT_PARAMS)
        if params:
            merged.update(params)
        self.params = merged
        self.name = name
        self.strategy = strategy
        # Hash includes strategy so fixed/missing/uncertainty/adaptive with
        # identical weights are distinct policies.
        self.hash = hashlib.sha256(
            (policy_hash(merged) + f":{strategy}").encode()
        ).hexdigest()[:16]

    def execute(
        self,
        view: AgentWorldView,
        *,
        budget: float | None = None,
        max_steps: int | None = None,
        preference: float | None = None,
    ) -> ControllerResult:
        """Run the policy over a fresh view using its own scoring weights.

        `budget`/`max_steps` override the defaults (10.0 / 12); when omitted,
        the world's own action costs are used so W2 budget worlds behave
        correctly. `strategy` selects the controller class:
        fixed / missing-evidence / uncertainty / adaptive-voi (default).
        `preference` (rho, 0..1) is the EXPLORATION PREFERENCE, independent of
        the hard budget: rho high -> more willingness to explore (lower VOI
        stop threshold); rho low -> stop sooner. It never bypasses the hard
        budget or safety constraints.
        """
        from marketpilot.policy.controller import (
            AdaptiveVOIController,
            FixedController,
            MissingEvidenceController,
            UncertaintyController,
        )

        strategy_map = {
            "fixed": FixedController,
            "missing-evidence": MissingEvidenceController,
            "uncertainty": UncertaintyController,
            "adaptive-voi": AdaptiveVOIController,
        }
        # Contextual-hybrid delegates to ContextualHybridPolicy (Task 1.3).
        # Task 1.3 (Final Locked): when no explicit budget is given, use the
        # WORLD's own research_budget (Benchmark v3.1) so scarce worlds
        # (budget=2.0) are NOT overridden by the controller default 10.0.
        world_budget = getattr(view, "_world", None)
        world_budget = (
            getattr(world_budget, "research_budget", None) if world_budget else None
        )
        effective_budget = (
            budget if budget is not None else (world_budget if world_budget else 10.0)
        )
        if self.strategy == "contextual-hybrid":
            from marketpilot.optimization.proposer import ContextualHybridPolicy, PolicyConfig

            cfg = PolicyConfig(
                strategy="adaptive-voi",
                weights={
                    k: v for k, v in self.params.items() if k.startswith("weight_")
                },
                schedule={"conflict_weight": self.params.get("conflict_weight", 0.3)},
            )
            hybrid = ContextualHybridPolicy(cfg)
            return hybrid.execute(
                view,
                budget=effective_budget,
                max_steps=max_steps if max_steps is not None else 12,
            )
        controller_cls = strategy_map.get(self.strategy, AdaptiveVOIController)
        controller = controller_cls(  # type: ignore[abstract]
            budget=effective_budget,
            max_steps=max_steps if max_steps is not None else 12,
        )
        # W2: use the world's configured action costs.
        controller.configure_costs(view_cost_config(view))
        # Task E: enable W3 refresh when the world models time drift (any
        # evidence carries multiple observed_at versions).
        if hasattr(controller, "refresh_stale"):
            controller.refresh_stale = _world_has_time_drift(view)
        if hasattr(controller, "VOI_THRESHOLD"):
            # Task D: rho maps to exploration willingness. rho=0 -> strong
            # cost preference (higher stop threshold, stop sooner); rho=1 ->
            # strong exploration (lower threshold, keep researching).
            # Default preference (None -> 0.5) maps to scale=1.0, i.e. the
            # policy's base voi_threshold unchanged (backward compatible).
            rho = 0.5 if preference is None else max(0.0, min(1.0, preference))
            base_threshold = self.params["voi_threshold"]
            # rho=0 -> base*8 (eager to stop); rho=1 -> base*0.25 (eager to
            # explore); rho=0.5 -> base*1.0 (unchanged default).
            # Piecewise-linear through (0,8),(0.5,1),(1,0.25).
            if rho <= 0.5:
                scale = 8.0 + (1.0 - 8.0) * (rho / 0.5)  # 8 -> 1
            else:
                scale = 1.0 + (0.25 - 1.0) * ((rho - 0.5) / 0.5)  # 1 -> 0.25
            scaled = base_threshold * scale
            controller.VOI_THRESHOLD = max(0.001, min(1.0, scaled))
        if hasattr(controller, "REFUSE_THRESHOLD"):
            controller.REFUSE_THRESHOLD = self.params["refuse_threshold"]
        # Inject policy-specific scoring weights via a subclass hook.
        controller._scores = self._scored  # type: ignore[method-assign]
        return controller.run(view)

    def _scored(self, view: AgentWorldView) -> dict[str, float]:
        """Weighted scoring from revealed evidence using this policy's weights."""
        scores: dict[str, float] = {}
        weights = self.params
        for candidate in view.candidates():
            pid = candidate["product_id"]
            total = 0.0
            for facet in EvidenceFacet:
                entries = view.evidence_summary(pid).get(facet.value, [])
                value = 0.5
                if entries:
                    value = sum(float(e["value"]) for e in entries) / len(entries)
                total += weights[f"weight_{facet.value}"] * value
            scores[pid] = total
        return scores


class ExplorationTree:
    """Observed action-outcome tree per world (no future branches)."""

    def __init__(self) -> None:
        self._nodes: dict[tuple[str, str], dict[str, Any]] = {}

    def observe(self, world_id: str, step: ObservedStep) -> None:
        key = (world_id, step.state_before)
        node = self._nodes.setdefault(key, {"actions": {}})
        node["actions"].setdefault(step.action, []).append(
            {
                "state_after": step.state_after,
                "cost": step.cost,
                "decision": step.decision,
            }
        )

    def known_actions(self, world_id: str, state_before: str) -> list[str]:
        node = self._nodes.get((world_id, state_before))
        return list(node["actions"]) if node else []

    def coverage(self, world_id: str) -> dict[str, int]:
        """Number of observed states and total observed actions for a world."""
        states = 0
        actions = 0
        for (wid, _state), node in self._nodes.items():
            if wid == world_id:
                states += 1
                actions += sum(len(v) for v in node["actions"].values())
        return {"states": states, "actions": actions}

    def to_json(self) -> dict[str, Any]:
        return {
            f"{world_id}:{state}": node
            for (world_id, state), node in self._nodes.items()
        }


class ReplayWorldArchive:
    """Append-only store of worlds and observed trajectories (Task 3).

    Trajectories are indexed by (round, world_id, policy_hash) so multiple
    rounds of history accumulate and DIFFERENT branches in the same world can
    be stored side by side. Old trajectories are NEVER silently deleted.
    """

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._trajectories: dict[tuple[int, str, str], TrajectoryRecord] = {}
        self._worlds: dict[str, World] = {}
        self._load()

    def _load(self) -> None:
        traj_dir = self.base_dir / "trajectories"
        if traj_dir.exists():
            for path in traj_dir.glob("*.json"):
                data = json.loads(path.read_text(encoding="utf-8"))
                record = TrajectoryRecord(
                    world_id=data["world_id"],
                    split=data["split"],
                    policy_hash=data["policy_hash"],
                    steps=[
                        ObservedStep(
                            step_index=int(s["step_index"]),
                            action=s["action"],
                            state_before=s["state_before"],
                            state_after=s["state_after"],
                            cost=float(s["cost"]),
                            decision=s["decision"],
                        )
                        for s in data["steps"]
                    ],
                    outcome=data["outcome"],
                    total_cost=float(data["total_cost"]),
                )
                round_index = int(data.get("round", 0))
                self._trajectories[(round_index, record.world_id, record.policy_hash)] = record
        world_dir = self.base_dir / "worlds"
        if world_dir.exists():
            from marketpilot.world.core import load_worlds

            self._worlds = load_worlds(world_dir)

    def record_trajectory(
        self,
        trajectory: TrajectoryRecord,
        *,
        round_index: int = 0,
    ) -> None:
        key = (round_index, trajectory.world_id, trajectory.policy_hash)
        self._trajectories[key] = trajectory
        traj_dir = self.base_dir / "trajectories"
        traj_dir.mkdir(parents=True, exist_ok=True)
        payload = trajectory.to_json()
        payload["round"] = round_index
        (traj_dir / f"r{round_index}_{trajectory.policy_hash}.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )

    def trajectories(self, *, round_index: int | None = None) -> list[TrajectoryRecord]:
        """All trajectories, optionally filtered to one round."""
        if round_index is None:
            return list(self._trajectories.values())
        return [
            t for (r, _wid, _h), t in self._trajectories.items() if r == round_index
        ]

    def trajectories_for_world(self, world_id: str) -> list[TrajectoryRecord]:
        """Every recorded trajectory for a world (all rounds, all branches)."""
        return [
            t for (_r, wid, _h), t in self._trajectories.items() if wid == world_id
        ]

    def worlds(self) -> dict[str, World]:
        return self._worlds

    def register_world(self, world: World) -> None:
        self._worlds[world.world_id] = world
        world_dir = self.base_dir / "worlds"
        world_dir.mkdir(parents=True, exist_ok=True)
        world.save(world_dir)


class HistoricalReplaySimulator:
    """Replays ONLY observed state transitions; unknown actions are rejected.

    Rule 4: Historical Replay returns only real recorded results; unknown
    actions are explicitly rejected. Coverage is reported explicitly.
    """

    def __init__(self, archive: ReplayWorldArchive) -> None:
        self.archive = archive
        self.rejected_actions: list[str] = []
        self.replay_hits = 0

    def replay_policy(
        self,
        policy: ParameterizedPolicy,
        world: World,
        observed_trajectory: TrajectoryRecord | None = None,
    ) -> tuple[ControllerResult, dict[str, Any]]:
        """Replay a policy over a world using ONLY recorded transitions.

        Returns (result, report) where report includes coverage and rejected
        actions. If an action is unknown, the simulator REJECTS it (does not
        invent a result) and stops that branch.

        ``observed_trajectory``: when set (dream evaluation of a variant that
        has no recorded trajectory of its own), replay the transitions of this
        recorded trajectory but score the replayed evidence with the variant's
        weights. Only the archive's already-observed history is used.
        """
        recorded = observed_trajectory or next(
            (
                t
                for t in self.archive.trajectories()
                if t.world_id == world.world_id and t.policy_hash == policy.hash
            ),
            None,
        )
        if recorded is None:
            return (
                ControllerResult(
                    selected_id=None,
                    stop_reason=StopReason.REFUSED,
                ),
                {
                    "coverage": 0.0,
                    "attempt_coverage": 0.0,
                    "episode_supported": 0.0,
                    "support_status": "UNSUPPORTED",
                    "unsupported_actions": ["no recorded trajectory for policy"],
                    "state_mismatches": [],
                    "rejected_actions": ["no recorded trajectory for policy"],
                    "replay_hits": 0,
                    "replayed_steps": 0,
                    "replayable_steps": 0,
                    "cost": 0.0,
                },
            )
        # Replay the recorded steps step-by-step against a fresh view. Unknown
        # actions are rejected (should not happen for a recorded trajectory).
        # Replay cost uses the OBSERVED per-step cost recorded in the archive
        # (what was actually spent when that transition happened online), so
        # replay cost is a faithful reproduction, not an estimate.
        view = AgentWorldView(world)
        replayed = 0
        replay_cost = 0.0
        unsupported: list[str] = []
        state_mismatches: list[str] = []
        for step in recorded.steps:
            action = step.action
            if action == "stop":
                continue
            try:
                research_action = ResearchAction(action)
            except ValueError:
                self.rejected_actions.append(action)
                unsupported.append(action)
                continue
            # W3 / W5: state-compatibility check. The recorded step carries a
            # state_before signature; if the CURRENT view's signature does not
            # match the recorded one, the transition is not replayable
            # (CROSS-WORLD / STATE MISMATCH) and must NOT be invented.
            # `_record_trajectory` uses s{index} placeholders for legacy
            # records; those are skipped. Real state signatures (from
            # view.state_signature()) ARE checked.
            if step.state_before and not step.state_before.startswith("s"):
                current_sig = view.state_signature()
                if current_sig != step.state_before:
                    state_mismatches.append(f"{step.state_before} != {current_sig}")
                    continue
            # Task 2.1 Replay Fidelity: the replayed action must target the
            # SAME product the online controller researched. Older records
            # without a product_id fall back to the previous behaviour
            # (None = first candidate), which is only valid for single-
            # candidate worlds.
            view.take_action(research_action, step.product_id)
            replayed += 1
            replay_cost += float(step.cost)
        self.replay_hits += replayed
        # Coverage denominator: only REPLAYABLE actions (non-stop, known
        # research actions). Stop is a terminal bookkeeping step, not an
        # attempt to execute research, so counting it in the denominator
        # would dilute coverage below what the policy actually explored.
        replayable = sum(1 for s in recorded.steps if s.action != "stop")
        # Attempt Coverage (Task 1.5): hits / (hits + unsupported attempts).
        attempts = replayed + len(unsupported)
        attempt_coverage = replayed / attempts if attempts else 0.0
        # Episode Support Rate (Task 1.5): fraction of episodes whose FULL
        # path was supported (no unsupported action, no state mismatch).
        episode_supported = (
            1.0
            if len(unsupported) == 0 and len(state_mismatches) == 0 and replayable > 0
            else 0.0
        )
        support_status = (
            "SUPPORTED"
            if len(unsupported) == 0 and len(state_mismatches) == 0
            else "UNSUPPORTED"
        )
        coverage = replayed / replayable if replayable else 0.0
        # Evaluate the replayed evidence with the policy's scoring.
        scores = policy._scored(view)
        selected = max(scores, key=lambda pid: scores[pid]) if scores else None
        # Task 2.1 Replay Fidelity: the replayed decision MUST follow the
        # SAME evidence-sufficiency rule as the live controller of the SAME
        # family. Replaying the recorded actions must not turn an
        # INSUFFICIENT outcome into a blind GO just because some score
        # exists — and must not turn a valid GO into INSUFFICIENT by
        # applying a stricter rule than the family actually used.
        revealed = {
            pid: [f.value for f in view.revealed_facets(pid)] for pid in scores
        }
        # adaptive-voi abstains based on the SELECTED candidate's missing
        # ratio; systematic families require every candidate's required
        # facets (mirrors _missing_ratio vs _sufficient semantics).
        if policy.strategy == "adaptive-voi":
            if selected is not None:
                sel_facets = set(revealed.get(selected, []))
                sufficient = REQUIRED_FACETS.issubset(sel_facets)
            else:
                sufficient = False
        else:
            sufficient = evidence_sufficient_for(
                ControllerResult(
                    selected_id=selected,
                    stop_reason=StopReason.SUFFICIENT_EVIDENCE,
                    revealed_facets=revealed,
                )
            )
        if selected is None:
            decision = "INSUFFICIENT"
            stop = StopReason.REFUSED
        elif sufficient:
            decision = "GO"
            stop = StopReason.SUFFICIENT_EVIDENCE
        else:
            # Evidence insufficient for a valid decision: the replayed
            # trajectory did not gather the required facets. This mirrors
            # the live controller's abstention semantics.
            decision = "INSUFFICIENT"
            stop = StopReason.BUDGET_EXHAUSTED
        result = ControllerResult(
            selected_id=selected,
            stop_reason=stop,
            revealed_facets=revealed,
            decision=decision,
        )
        return (
            result,
            {
                "coverage": round(coverage, 4),
                "attempt_coverage": round(attempt_coverage, 4),
                "episode_supported": episode_supported,
                "support_status": support_status,
                "unsupported_actions": unsupported,
                "state_mismatches": state_mismatches,
                "rejected_actions": list(self.rejected_actions),
                "replay_hits": self.replay_hits,
                "replayed_steps": replayed,
                "replayable_steps": replayable,
                "cost": round(replay_cost, 4),
            },
        )


class MultiWorldDreamEvaluator:
    """Task B: evaluate ONE policy against the FULL history pool.

    For each allowed historical world/trace in the pool:
    1. Replay the policy over that trace's recorded transitions (state
       compatible only; unknown actions rejected).
    2. Record per-trace outcome (decision, regret evaluator-side, cost,
       coverage, support).
    3. Aggregate ACROSS WORLDS (by world_id) so a world with more traces does
       not get more statistical weight.

    Aggregation rules:
    - Each world contributes its mean regret / success / cost.
    - A world with NO supported trace is NOT silently dropped; it is counted
      with its failure reason (NOT_EVALUABLE) and reported.
    - Never use max(all_scores); never average only the successful worlds.
    - Regret is only computed on SUPPORTED traces; unsupported traces get
      `support_status` and are excluded from the REAL regret statistics (a
      proxy penalty may be tracked separately).
    """

    def __init__(self, replay: HistoricalReplaySimulator | None = None) -> None:
        # replay is injected by the loop; a standalone evaluator builds its
        # own simulator lazily (no archive needed for trace replay since
        # evaluate_policy_on_pool passes observed_trajectory explicitly).
        self.replay = replay

    def _sim(self) -> HistoricalReplaySimulator:
        if self.replay is None:
            self.replay = HistoricalReplaySimulator(
                ReplayWorldArchive(Path(".") / "multiworld-tmp-archive-do-not-use")
            )
        return self.replay

    def evaluate_policy_on_pool(
        self,
        policy: ParameterizedPolicy,
        pool: list[TrajectoryRecord],
        worlds: dict[str, World],
        *,
        preference: float = 0.5,
        budget: float = 10.0,
    ) -> dict[str, Any]:
        """Evaluate a policy over the whole pool (per-trace + per-world agg).

        Returns a dict with:
        - per_trace: list of per-trace evaluation records
        - per_world: dict world_id -> aggregated metrics
        - aggregate: mean/median/worst over worlds, support stats
        """
        per_trace: list[dict[str, Any]] = []
        # Group traces by world_id (a world with many traces counts once).
        by_world: dict[str, list[TrajectoryRecord]] = {}
        for trace in pool:
            by_world.setdefault(trace.world_id, []).append(trace)

        for world_id, traces in by_world.items():
            world = worlds.get(world_id)
            if world is None:
                per_trace.append(
                    {"world_id": world_id, "trace_id": "?", "status": "WORLD_MISSING"}
                )
                continue
            oracle = WorldOracle(world)
            for trace in traces:
                # Replay this trace independently (only this trace's recorded
                # transitions; no cross-world evidence merge).
                result, report = self._sim().replay_policy(
                    policy, world, observed_trajectory=trace
                )
                status = report.get("support_status", "SUPPORTED")
                regret = None
                if status == "SUPPORTED" and result.selected_id is not None:
                    regret = oracle.regret(result.selected_id)
                per_trace.append(
                    {
                        "world_id": world_id,
                        "world_version": world.world_version,
                        "trace_id": trace.policy_hash,
                        "round_id": getattr(trace, "round_id", None),
                        "preference": preference,
                        "budget": budget,
                        "status": status,
                        "decision": result.decision,
                        "selected": result.selected_id,
                        "regret": regret,
                        "cost": report.get("cost", 0.0),
                        "attempt_coverage": report.get("attempt_coverage", 0.0),
                        "episode_supported": report.get("episode_supported", 0.0),
                        "unsupported_actions": report.get("unsupported_actions", []),
                        "state_mismatches": report.get("state_mismatches", []),
                    }
                )

        # Per-world aggregation: world with more traces does not weigh more.
        per_world: dict[str, dict[str, Any]] = {}
        supported_worlds: list[float] = []
        for world_id in by_world:
            world_traces = [t for t in per_trace if t["world_id"] == world_id]
            supported = [t for t in world_traces if t["status"] == "SUPPORTED"]
            regrets = [t["regret"] for t in supported if t["regret"] is not None]
            per_world[world_id] = {
                "n_traces": len(world_traces),
                "n_supported": len(supported),
                "mean_regret": sum(regrets) / len(regrets) if regrets else None,
                "support_rate": len(supported) / len(world_traces) if world_traces else 0.0,
                "statuses": [t["status"] for t in world_traces],
            }
            if regrets:
                supported_worlds.append(sum(regrets) / len(regrets))

        # Aggregate across worlds (not across traces).
        aggregate: dict[str, Any] = {
            "n_worlds": len(by_world),
            "n_supported_worlds": len(supported_worlds),
            "n_not_evaluable_worlds": sum(
                1 for w in per_world.values() if w["n_supported"] == 0
            ),
            "mean_world_regret": (
                sum(supported_worlds) / len(supported_worlds) if supported_worlds else None
            ),
            "median_world_regret": (
                sorted(supported_worlds)[len(supported_worlds) // 2]
                if supported_worlds
                else None
            ),
            "worst_world_regret": max(supported_worlds) if supported_worlds else None,
            "overall_support_rate": (
                sum(w["n_supported"] for w in per_world.values())
                / sum(w["n_traces"] for w in per_world.values())
                if per_world
                else 0.0
            ),
        }
        return {
            "policy_hash": policy.hash,
            "pool_size": len(pool),
            "per_trace": per_trace,
            "per_world": per_world,
            "aggregate": aggregate,
        }


class DreamEvaluator:
    """Dream evaluation: offline replay score of a proposed policy.

    Distinguishes three cases (Task 1.3):
    A. The proposed policy forms a different but VALID decision (business
       quality judged by the independent evaluator, NOT by agreement with
       history). A different decision is NOT auto-penalized.
    B. The proposed policy needs state/evidence NOT covered by the archive ->
       UNSUPPORTED / NOT_EVALUABLE; the score is 0.0 (never guessed).
    C. Deterministic replay of recorded history yields an inconsistent
       result -> a REPLAY CORRECTNESS ERROR, also scored 0.0 (flagged).

    The disagreement term is kept ONLY as a research heuristic, with a 0/0.1/0.3
    sensitivity ablation available. It never substitutes for independent
    decision quality.
    """

    def evaluate(
        self,
        policy: ParameterizedPolicy,
        replay_report: dict[str, Any],
        result: ControllerResult,
        recorded_outcome: str | None = None,
        disagreement_penalty: float = 0.1,
    ) -> float:
        coverage = float(replay_report.get("coverage", 0.0))
        support_status = replay_report.get("support_status", "SUPPORTED")
        # Case B / C: unsupported actions or state mismatches -> the policy's
        # path is NOT fully covered by history. We do NOT guess; we return
        # NOT_EVALUABLE (score 0.0). A policy whose replay is incomplete
        # cannot be claimed to be better than the incumbent.
        if support_status != "SUPPORTED":
            return 0.0
        if coverage <= 0.0:
            return 0.0
        success = 1.0 if result.decision == "GO" else 0.0
        # Case A: disagreement with the recorded outcome is a heuristic signal
        # only. A DIFFERENT decision is not automatically bad; it must be
        # judged by the independent evaluator (regret), not by agreement with
        # history. The penalty is configurable (0 / 0.1 / 0.3 ablation).
        disagreement = 0.0
        if recorded_outcome is not None:
            disagreement = 0.0 if result.decision == recorded_outcome else 1.0
        penalty = disagreement_penalty * disagreement
        return round(max(0.0, coverage * (0.5 + 0.5 * success) - penalty), 4)


class PolicyRegistry:
    """Registry with promotion/rollback and independent confirmation gate."""

    def __init__(self) -> None:
        self._policies: dict[str, ParameterizedPolicy] = {}
        self._status: dict[str, PolicyStatus] = {}
        self._history: list[dict[str, Any]] = []

    def propose(self, policy: ParameterizedPolicy) -> None:
        self._policies[policy.hash] = policy
        self._status[policy.hash] = PolicyStatus.PROPOSED

    def mark_dream_evaluated(self, policy_hash: str) -> None:
        self._status[policy_hash] = PolicyStatus.DREAM_EVALUATED

    def promote(self, policy_hash: str, kind: PromotionKind = PromotionKind.TIED) -> None:
        self._status[policy_hash] = PolicyStatus.PROMOTED
        self._history.append(
            {"event": "promote", "policy_hash": policy_hash, "kind": kind.value}
        )

    def rollback(self, policy_hash: str, reason: str = "confirmation_failed") -> None:
        self._status[policy_hash] = PolicyStatus.ROLLED_BACK
        self._history.append(
            {"event": "rollback", "policy_hash": policy_hash, "reason": reason}
        )

    def classify_outcome(
        self,
        policy_hash: str,
        *,
        quality_delta: float,
        cost_delta: float,
        threshold: float = 1e-6,
        quality_tolerance: float = 0.0,
    ) -> PromotionKind:
        """Classify how a promoted policy compares to its predecessor by PAIRED
        confirmation runs (same world, same budget).

        Decision rules (pre-defined, not tuned after seeing results):
        - quality_delta >  quality_tolerance -> IMPROVED  (better decision quality)
        - quality_delta < -quality_tolerance -> REGRESSED (worse decision quality)
        - quality_delta within tolerance AND cost_delta < -threshold
                                             -> EFFICIENCY_GAIN (same quality, cheaper)
        - otherwise                           -> TIED (no sufficient evidence of
                                                  quality or efficiency gain)
        """
        if quality_delta > quality_tolerance:
            kind = PromotionKind.IMPROVED
        elif quality_delta < -quality_tolerance:
            kind = PromotionKind.REGRESSED
        elif cost_delta < -threshold:
            kind = PromotionKind.EFFICIENCY_GAIN
        else:
            kind = PromotionKind.TIED
        self._history.append(
            {
                "event": "classify",
                "policy_hash": policy_hash,
                "kind": kind.value,
                "quality_delta": round(quality_delta, 6),
                "cost_delta": round(cost_delta, 6),
            }
        )
        return kind

    def status(self, policy_hash: str) -> PolicyStatus:
        return self._status.get(policy_hash, PolicyStatus.PROPOSED)

    def active(self) -> ParameterizedPolicy | None:
        """The single promoted policy (default params if none promoted)."""
        promoted = [
            h for h, s in self._status.items() if s is PolicyStatus.PROMOTED
        ]
        if not promoted:
            return ParameterizedPolicy(name="default")
        return self._policies[promoted[-1]]

    def history(self) -> list[dict[str, Any]]:
        return list(self._history)

    def confirmation_passed(self, policy_hash: str) -> bool:
        """Independent Confirmation DEV gate: policy must be verified on the
        confirmation world and have no rejected actions."""
        return self._status.get(policy_hash) is PolicyStatus.REPLAY_VERIFIED


class ExecutionLedger:
    """Strict cost accounting for RSI loops (Task 1.4).

    Distinguishes SIX cost types, never mixed:
    - archive_collection : cost of collecting historical exploration data
                           (real, spent when the trajectory was recorded).
    - online_execution   : current policy's NEW real execution in the env.
    - policy_proposal    : cost of generating a candidate policy.
    - confirmation       : independent confirmation run cost (real).
    - incremental_replay : incremental cost of reading history + running the
                           replay policy (offline compute, NOT real budget).
    - simulated_action   : replay-path representation of historical action
                           budget consumption (VIRTUAL; never counts as new
                           real online spend).

    `ObservedStep.cost` records the ORIGINAL tool-call cost at collection
    time; when a replay re-runs that step, its cost is `simulated_action`
    (virtual), NOT a new real online expense. The same historical collection
    event is never charged twice in one comparison.
    """

    def __init__(self) -> None:
        self._entries: list[dict[str, Any]] = []

    def record(
        self,
        *,
        round_index: int,
        phase: str,
        cost_type: str,
        policy_hash: str,
        cost: float,
        note: str = "",
    ) -> None:
        self._entries.append(
            {
                "round": round_index,
                "phase": phase,
                "cost_type": cost_type,
                "policy_hash": policy_hash,
                "cost": round(float(cost), 4),
                "note": note,
            }
        )

    def record_online(
        self, *, round_index: int, phase: str, policy_hash: str, cost: float
    ) -> None:
        self.record(
            round_index=round_index, phase=phase, cost_type="online_execution",
            policy_hash=policy_hash, cost=cost,
        )

    def record_replay(
        self,
        *,
        round_index: int,
        phase: str,
        policy_hash: str,
        actions_replayed: int,
        cost: float,
    ) -> None:
        # Replay cost = simulated_action (virtual historical budget), plus a
        # small incremental_replay overhead (offline compute). Both are
        # recorded separately so they never mix with real online spend.
        self.record(
            round_index=round_index, phase=phase, cost_type="simulated_action",
            policy_hash=policy_hash, cost=cost,
            note=f"replayed {actions_replayed} actions",
        )
        self.record(
            round_index=round_index, phase=phase, cost_type="incremental_replay",
            policy_hash=policy_hash, cost=0.0,
            note="offline replay compute (no real budget)",
        )

    @property
    def online_total(self) -> float:
        return self._total_of_types(
            {"online_execution", "confirmation", "archive_collection", "policy_proposal"}
        )

    @property
    def replay_total(self) -> float:
        """Total replay-related cost. NOTE: simulated_action is VIRTUAL
        historical budget, NOT real spend; real replay cost is only the
        incremental_replay compute. Use `replay_compute_total` for real cost."""
        return self._total_of_types({"simulated_action", "incremental_replay"})

    @property
    def replay_compute_total(self) -> float:
        """REAL replay compute cost (incremental_replay only)."""
        return self._total_of_types({"incremental_replay"})

    @property
    def simulated_action_total(self) -> float:
        """VIRTUAL historical budget consumed by replays (never real spend)."""
        return self._total_of_types({"simulated_action"})

    def _total_of_types(self, types: set[str]) -> float:
        return sum(float(e["cost"]) for e in self._entries if e["cost_type"] in types)

    def by_type(self) -> dict[str, float]:
        totals: dict[str, float] = {}
        for entry in self._entries:
            totals[entry["cost_type"]] = (
                totals.get(entry["cost_type"], 0.0) + float(entry["cost"])
            )
        return {k: round(v, 4) for k, v in totals.items()}

    def to_json(self) -> dict[str, Any]:
        return {
            "online_total": round(self.online_total, 4),
            "replay_total": round(self.replay_total, 4),
            "replay_compute_total": round(self.replay_compute_total, 4),
            "simulated_action_total": round(self.simulated_action_total, 4),
            "by_type": self.by_type(),
            "entries": self._entries,
        }


class RecursiveOptimizationLoop:
    """The recursive loop: propose -> dream evaluate -> replay verify ->
    confirmation DEV -> promote or rollback. Parameterized policy search first
    (LLM code modification is a later extension)."""

    def __init__(
        self,
        archive: ReplayWorldArchive,
        registry: PolicyRegistry,
        *,
        rounds: int = 3,
        exploration: float = 0.1,
        dream_threshold: float = 0.5,
        pool_mode: str = "full",
        confirmation_shards: list[World] | None = None,
    ) -> None:
        self.archive = archive
        self.registry = registry
        self.rounds = rounds
        self.exploration = exploration
        self.dream_threshold = dream_threshold
        # Task 3: "full" = dream over ALL accumulated history (up to current
        # round); "current" = dream over ONLY the most recent round's history.
        self.pool_mode = pool_mode
        # Task 5: pre-allocated confirmation shards (world-level isolation).
        # Each round consumes ONE shard; a shard is never reused across
        # rounds. If shards run out, the loop reports confirmation budget
        # exhaustion instead of reusing.
        self.confirmation_shards = confirmation_shards or []
        self.shard_usage: dict[int, str] = {}  # round -> shard world_id
        self.replay = HistoricalReplaySimulator(archive)
        self.dream = DreamEvaluator()
        self.round_log: list[dict[str, Any]] = []
        self.ledger = ExecutionLedger()
        self._dream_scores: dict[str, float] = {}
        # Task 1.4: multi-family proposer (cross-family candidate search).
        # When enabled, proposals can come from any strategy family, not just
        # AdaptiveVOI perturbations.
        self.proposer: MultiFamilyProposer | None = None

    def run(self, dev_world: World, confirmation_world: World) -> dict[str, Any]:
        """Run the recursive optimization loop.

        The active (default) policy records a trajectory on the dev world;
        proposals are variants, dream-evaluated on replay, verified on the
        confirmation world, then promoted or rolled back. The TEST world is
        never used here.
        """
        active = self.registry.active()
        if active is None:
            active = ParameterizedPolicy(name="default")
            self.registry.propose(active)
        # 1. Record observed trajectory of the active policy on dev (round 0).
        view = AgentWorldView(dev_world)
        result = active.execute(view)
        self.ledger.record_online(
            round_index=0, phase="init", policy_hash=active.hash, cost=result.total_cost
        )
        trajectory = _record_trajectory(dev_world, active, result)
        self.archive.record_trajectory(trajectory, round_index=0)
        self._seed_tree(dev_world, trajectory)

        for round_index in range(1, self.rounds + 1):
            # 2. Propose a parameterized variant (exploration noise around active).
            proposed = self._propose_variant(active, round_index - 1)
            self.registry.propose(proposed)
            # 3. Dream evaluation: replay the variant against the archive's
            #    OBSERVED history for the dev world. With pool_mode="full",
            #    dream over ALL accumulated rounds' trajectories for the dev
            #    world (Task 3 cumulative pool). With pool_mode="current",
            #    dream over ONLY the most recent round's trajectory.
            if self.pool_mode == "current":
                observed_pool = [
                    t for t in self.archive.trajectories(round_index=round_index - 1)
                    if t.world_id == dev_world.world_id
                ]
            else:  # full
                observed_pool = self.archive.trajectories_for_world(dev_world.world_id)
            # Score against the most recent trajectory of the active policy
            # (the one that produced the current dev history).
            observed = next(
                (
                    t
                    for t in observed_pool
                    if t.policy_hash == active.hash
                ),
                observed_pool[-1] if observed_pool else None,
            )
            replay_result, replay_report = self.replay.replay_policy(
                proposed, dev_world, observed_trajectory=observed
            )
            # Offline dream replay: simulated actions, no real budget spent.
            self.ledger.record_replay(
                round_index=round_index,
                phase="dream",
                policy_hash=proposed.hash,
                actions_replayed=int(replay_report.get("replayed_steps", 0)),
                cost=float(replay_report.get("cost", 0.0)),
            )
            dream_score = self.dream.evaluate(
                proposed,
                replay_report,
                replay_result,
                recorded_outcome=observed.outcome if observed else None,
            )
            self._dream_scores[proposed.hash] = dream_score
            self.registry.mark_dream_evaluated(proposed.hash)
            # 4. Independent Confirmation DEV (Task 5): each round consumes a
            #    pre-allocated confirmation shard. Shards are never reused
            #    across rounds. If shards are exhausted, the round cannot
            #    confirm and the challenger is NOT promoted (reports
            #    confirmation budget exhaustion).
            round_used_shard = round_index - 1
            # Task F (fail-closed): when no fresh confirmation shard is
            # available, the round does NOT confirm and the challenger is NOT
            # promoted. There is NO fallback to Generation DEV / Locked Test /
            # a previously-used world. If the loop was given no shards at all,
            # we still allow the legacy single-confirmation-world behavior
            # ONLY when explicitly requested (confirmation_shards=None means
            # the caller accepts reusing the confirmation_world).
            if self.confirmation_shards:
                if round_used_shard < len(self.confirmation_shards):
                    conf_world = self.confirmation_shards[round_used_shard]
                    self.shard_usage[round_index] = conf_world.world_id
                else:
                    # FAIL-CLOSED: no fresh shard -> this round cannot confirm.
                    self.shard_usage[round_index] = "EXHAUSTED"
                    self.round_log.append(
                        {
                            "round": round_index,
                            "proposed_hash": proposed.hash,
                            "dream_score": dream_score,
                            "confirmation_ok": False,
                            "action": "confirmation_exhausted",
                            "kind": None,
                        }
                    )
                    self.registry.rollback(proposed.hash, reason="confirmation_exhausted")
                    continue
            else:
                conf_world = confirmation_world
            conf_view = AgentWorldView(conf_world)
            conf_result = proposed.execute(conf_view)
            self.ledger.record_online(
                round_index=round_index,
                phase="confirmation",
                policy_hash=proposed.hash,
                cost=conf_result.total_cost,
            )
            conf_trajectory = _record_trajectory(conf_world, proposed, conf_result)
            self.archive.record_trajectory(conf_trajectory, round_index=round_index)
            _conf_replay, conf_report = self.replay.replay_policy(proposed, conf_world)
            self.ledger.record_replay(
                round_index=round_index,
                phase="confirmation_replay",
                policy_hash=proposed.hash,
                actions_replayed=int(conf_report.get("replayed_steps", 0)),
                cost=float(conf_report.get("cost", 0.0)),
            )
            # Confirmation gate: the challenger must make a DECISION with
            # sufficient evidence (not refuse, not demand human review), its
            # replay must be fully supported, and its dream score must clear
            # the threshold. On worlds whose key facet is expensive/hidden,
            # an adaptive policy may legitimately stop with a selected product
            # (decision != GO because evidence is partial) — but if it REFUSES
            # or requests HUMAN_REVIEW it did not reach a decision and cannot
            # be promoted. If confirmation shards are exhausted, the round
            # cannot confirm (Task 5).
            conf_ok = (
                self.shard_usage.get(round_index) != "EXHAUSTED"
                and not conf_result.refused
                and not conf_result.human_review
                and len(conf_report.get("rejected_actions", [])) == 0
                and dream_score >= self.dream_threshold
            )
            kind: PromotionKind | None = None
            prev_active: ParameterizedPolicy | None = None
            inc_result: ControllerResult | None = None
            inc_regret: float | None = None
            chal_regret: float | None = None
            quality_delta: float | None = None
            cost_delta: float | None = None
            if conf_ok:
                # Classify the promotion by PAIRED comparison: the incumbent
                # (previous active) and the challenger (proposed) are BOTH
                # executed on the same confirmation world with the same budget,
                # so quality/cost deltas are real paired measurements, not
                # proxies.
                prev_active = active
                # Paired incumbent run on the SAME confirmation world (shard).
                inc_view = AgentWorldView(conf_world)
                inc_result = prev_active.execute(inc_view)
                self.ledger.record_online(
                    round_index=round_index,
                    phase="incumbent_confirmation",
                    policy_hash=prev_active.hash,
                    cost=inc_result.total_cost,
                )
                # Task A1: quality delta is computed by the EVALUATOR from the
                # REAL decision utility/regret of each policy's selected
                # product on the confirmation world — NOT by whether the two
                # policies selected different products. Same utility but
                # different product = TIED; different product with higher
                # regret = REGRESSED. The oracle is used here because this is
                # the evaluator-side promotion gate, never inside the policy.
                oracle = WorldOracle(conf_world)
                # Task 1.1/1.2: a REFUSED / HUMAN_REVIEW / INSUFFICIENT
                # decision does NOT get the (possibly lucky) selected_id's
                # regret; it is charged the FULL regret (best_utility) because
                # no valid recommendation was produced. This prevents "cheap
                # abstention" from looking like a low-regret outcome.
                if (
                    inc_result.refused
                    or inc_result.human_review
                    or inc_result.decision == "INSUFFICIENT"
                ):
                    inc_regret = oracle.best_utility()
                else:
                    inc_regret = oracle.regret(inc_result.selected_id)
                if (
                    conf_result.refused
                    or conf_result.human_review
                    or conf_result.decision == "INSUFFICIENT"
                ):
                    chal_regret = oracle.best_utility()
                else:
                    chal_regret = oracle.regret(conf_result.selected_id)
                # Regret is lower-is-better; quality delta is positive when the
                # challenger's regret is strictly lower (and it made a valid
                # decision). A refused challenger cannot be promoted (conf_ok
                # already excludes that); a refused INCUMBENT being replaced
                # by a valid GO challenger is a real improvement.
                quality_delta = inc_regret - chal_regret
                # Real paired cost delta: challenger cost - incumbent cost
                # (negative = challenger cheaper).
                cost_delta = conf_result.total_cost - inc_result.total_cost
                kind = self.registry.classify_outcome(
                    proposed.hash,
                    quality_delta=quality_delta,
                    cost_delta=cost_delta,
                    quality_tolerance=1e-6,
                )
                # Task 1.3 Promotion Gate: a REGRESSED challenger is NOT
                # promoted even though confirmation "succeeded" (conf_ok).
                # TIED also does not switch the active policy by default;
                # only IMPROVED / EFFICIENCY_GAIN switch.
                if kind is PromotionKind.REGRESSED or kind is PromotionKind.TIED:
                    self.registry.rollback(proposed.hash, reason=f"kind={kind.value}")
                    conf_ok = False
                else:
                    self.registry.promote(proposed.hash, kind=kind)
                    active = proposed
                    # Record the promoted policy's dev trajectory so future
                    # variants dream-evaluate over it.
                    dev_view = AgentWorldView(dev_world)
                    dev_result = active.execute(dev_view)
                    self.ledger.record_online(
                        round_index=round_index,
                        phase="promote_dev",
                        policy_hash=active.hash,
                        cost=dev_result.total_cost,
                    )
                    dev_trajectory = _record_trajectory(dev_world, active, dev_result)
                    self.archive.record_trajectory(
                        dev_trajectory, round_index=round_index
                    )
            else:
                self.registry.rollback(proposed.hash)
            # Task 1.1: full per-round promotion audit trail.
            self.round_log.append(
                {
                    "round": round_index,
                    "incumbent_policy_hash": (
                        prev_active.hash if prev_active is not None else active.hash
                    ),
                    "challenger_policy_hash": proposed.hash,
                    "incumbent_family": (
                        prev_active.strategy if prev_active is not None else active.strategy
                    ),
                    "challenger_family": proposed.strategy,
                    "dream_score": dream_score,
                    "replay_support": replay_report.get("support_status", "UNSUPPORTED"),
                    "confirmation_world_id": (
                        self.shard_usage.get(round_index, conf_world.world_id)
                    ),
                    "confirmation_ok": conf_ok,
                    "action": "promote" if conf_ok else "rollback",
                    "kind": kind.value if kind is not None else None,
                    "incumbent_outcome": (
                        inc_result.decision if inc_result is not None else None
                    ),
                    "challenger_outcome": conf_result.decision,
                    "incumbent_regret": (
                        round(inc_regret, 4) if inc_regret is not None else None
                    ),
                    "challenger_regret": (
                        round(chal_regret, 4) if chal_regret is not None else None
                    ),
                    "quality_delta": (
                        round(quality_delta, 4) if quality_delta is not None else None
                    ),
                    "cost_delta": (
                        round(cost_delta, 4) if cost_delta is not None else None
                    ),
                }
            )
        active_policy = self.registry.active()
        return {
            "rounds": self.rounds,
            "pool_mode": self.pool_mode,
            "pool_size": len(self.archive.trajectories()),
            "promoted": active_policy.hash if active_policy else "none",
            "round_log": self.round_log,
            "replay_hits": self.replay.replay_hits,
            "rejected_actions": list(self.replay.rejected_actions),
        }

    def _propose_variant(self, base: ParameterizedPolicy, round_index: int) -> ParameterizedPolicy:
        """Deterministic parameter perturbation seeded by the round index.

        When a MultiFamilyProposer is attached, proposals come from the
        multi-family search space (cross-family + perturbation + contextual)
        instead of AdaptiveVOI-only perturbation (Task 1).
        """
        if self.proposer is not None:
            batch = self.proposer.propose(base, round_index, n_candidates=4)
            # Pick a non-incumbent candidate (the batch[0] is the incumbent).
            candidates = [c for c in batch if c.hash != base.hash]
            if candidates:
                return candidates[round_index % len(candidates)]
            return base
        import random

        rng = random.Random(1000 + round_index)
        params = dict(base.params)
        keys = list(PARAM_KEYS)
        for key in keys[:6]:  # perturb facet weights only
            params[key] = max(-1.0, min(1.0, params[key] + rng.uniform(-0.1, 0.1)))
        return ParameterizedPolicy(params, name=f"variant-r{round_index}")

    def _seed_tree(self, world: World, trajectory: TrajectoryRecord) -> None:
        """Seed the exploration tree from an observed trajectory."""
        self._tree = ExplorationTree()
        for step in trajectory.steps:
            self._tree.observe(world.world_id, step)


def _record_trajectory(
    world: World,
    policy: ParameterizedPolicy,
    result: ControllerResult,
) -> TrajectoryRecord:
    """Convert a controller result into an observed trajectory record.

    Each step stores the research-action name (e.g. "search_margin") and the
    target product id, so HistoricalReplaySimulator can re-execute the exact
    observed transition.
    """
    from marketpilot.policy.controller import _FACET_ACTION

    steps: list[ObservedStep] = []
    for index, step in enumerate(result.steps):
        action_name = "stop"
        if step.facet is not None:
            research_action = _FACET_ACTION.get(step.facet)
            if research_action is not None:
                action_name = research_action.value
        steps.append(
            ObservedStep(
                step_index=index,
                action=action_name,
                state_before=f"s{index}",
                state_after=f"s{index + 1}",
                cost=step.cost,
                decision=result.decision,
                product_id=step.target_id,
            )
        )
    return TrajectoryRecord(
        world_id=world.world_id,
        split=world.split.value,
        policy_hash=policy.hash,
        steps=steps,
        outcome=result.decision,
        total_cost=result.total_cost,
    )
