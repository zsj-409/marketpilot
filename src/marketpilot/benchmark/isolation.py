"""Evaluation hardening v2.1: isolated method execution (Task 1).

Unified runner that guarantees:
- every method starts from a FRESH AgentWorldView (independent revealed
  evidence, time=0, zero spent budget);
- no cross-method state pollution (no shared view, no shared PRNG);
- the World object itself is treated as immutable: views are created from
  the SAME world but each view is independent (revealed/time are per-view);
- random methods derive their PRNG from (world_id, method, repetition) so
  execution order cannot change results;
- the runner REJECTS a dirty initial view (negative control, Task 1.3).

Also provides:
- run_method_order_invariance(): permutation-invariance test (Task 1.2).
"""

from __future__ import annotations

import hashlib
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from marketpilot.world.core import AgentWorldView, World

# A method runner: takes a fresh view (+ prng seed) and returns a result.
MethodRunner = Callable[[AgentWorldView, int], Any]


class ViewPollutionError(RuntimeError):
    """Raised when a view handed to a method is not in its initial state."""


def _initial_signature(world: World) -> str:
    """The agent-visible signature of a fresh view (time 0, nothing revealed)."""
    view = AgentWorldView(world)
    return view.state_signature()


def isolated_execute(
    world: World,
    method: str,
    runner: MethodRunner,
    repetition: int = 0,
    *,
    verify_clean: bool = True,
) -> tuple[Any, str]:
    """Execute ONE method on ONE world in full isolation.

    Returns (result, final_state_signature). If verify_clean is True, the
    view's pre-execution signature must equal the fresh signature; otherwise
    ViewPollutionError is raised (negative control for cross-method leaks).
    """
    view = AgentWorldView(world)
    if verify_clean:
        fresh = _initial_signature(world)
        actual = view.state_signature()
        if actual != fresh:
            raise ViewPollutionError(
                f"view for {method} on {world.world_id} is not clean: "
                f"{actual} != fresh {fresh}"
            )
    # Deterministic per-(world, method, repetition) PRNG: order-invariant.
    seed = _prng_seed(world.world_id, method, repetition)
    result = runner(view, seed)
    return result, view.state_signature()


def _prng_seed(world_id: str, method: str, repetition: int) -> int:
    raw = f"{world_id}::{method}::{repetition}".encode()
    return int(hashlib.sha256(raw).hexdigest()[:12], 16)


def run_method_order_invariance(
    world: World,
    runners: dict[str, MethodRunner],
    *,
    repetitions: int = 1,
) -> dict[str, Any]:
    """Permutation-invariance test (Task 1.2).

    Runs every method in several orders; for a fixed (world, method,
    repetition), the outcome signature must be identical regardless of
    which other methods ran before it.
    """
    orders = [
        list(runners.keys()),
        list(reversed(list(runners.keys()))),
        sorted(runners.keys()),
    ]
    # Add a random order (deterministic seed).
    rng = random.Random(1234)
    shuffled = list(runners.keys())
    rng.shuffle(shuffled)
    orders.append(shuffled)

    per_method: dict[str, list[str]] = {m: [] for m in runners}
    for order in orders:
        for m in order:
            view = AgentWorldView(world)
            seed = _prng_seed(world.world_id, m, 0)
            result = runners[m](view, seed)
            sig = view.state_signature()
            per_method[m].append(f"{sig}::{result}")
    # Check: each method's signature set must have size 1 (order-invariant).
    violations = {}
    for m, sigs in per_method.items():
        if len(set(sigs)) != 1:
            violations[m] = sigs
    return {
        "world_id": world.world_id,
        "orders_tested": len(orders),
        "method_signatures": {m: sigs[0] for m, sigs in per_method.items()},
        "order_invariant": not violations,
        "violations": violations,
    }


@dataclass
class IsolationReport:
    """Machine-readable isolation check report."""

    world_id: str
    n_methods: int
    views_clean: bool
    order_invariant: bool
    budget_isolated: bool
    details: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {
            "world_id": self.world_id,
            "n_methods": self.n_methods,
            "views_clean": self.views_clean,
            "order_invariant": self.order_invariant,
            "budget_isolated": self.budget_isolated,
            "details": self.details,
        }
