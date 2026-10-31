"""Benchmark v3: data-freeze manifest (Task 6).

A BenchmarkManifest records everything needed to verify that a frozen
dataset was NOT modified and that a Locked Test is reproducible:
- benchmark_version, generator/evaluator versions+hashes
- dataset_split_hash, world_ids, world_config_hashes, seed_registry
- policy_hash, model_version, prompt_hash, research_budget
- metric_contract_version, execution_mode, creation_timestamp

Freeze invariants:
- Locked Test truths/trajectories/results never enter the optimizer.
- Any generation bug invalidates the old version explicitly (new version +
  impact record), never silent modification.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class BenchmarkManifest:
    benchmark_version: str
    generator_version: str
    evaluator_version: str
    metric_contract_version: str
    git_commit: str
    execution_mode: str  # pilot | dev | confirmation | locked_test
    world_ids: list[str] = field(default_factory=list)
    world_config_hashes: dict[str, str] = field(default_factory=dict)
    seed_registry: dict[str, int] = field(default_factory=dict)
    policy_hash: str = ""
    model_version: str = ""
    prompt_hash: str = ""
    research_budget: float = 12.0
    creation_timestamp: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    @property
    def dataset_split_hash(self) -> str:
        raw = json.dumps(
            {
                "world_ids": self.world_ids,
                "config_hashes": self.world_config_hashes,
                "seeds": self.seed_registry,
            },
            sort_keys=True,
        )
        return hashlib.sha256(raw.encode()).hexdigest()

    def to_json(self) -> dict[str, Any]:
        return {
            "benchmark_version": self.benchmark_version,
            "generator_version": self.generator_version,
            "evaluator_version": self.evaluator_version,
            "metric_contract_version": self.metric_contract_version,
            "git_commit": self.git_commit,
            "execution_mode": self.execution_mode,
            "world_ids": self.world_ids,
            "world_config_hashes": self.world_config_hashes,
            "seed_registry": self.seed_registry,
            "policy_hash": self.policy_hash,
            "model_version": self.model_version,
            "prompt_hash": self.prompt_hash,
            "research_budget": self.research_budget,
            "creation_timestamp": self.creation_timestamp,
            "dataset_split_hash": self.dataset_split_hash,
        }

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_json(), indent=2, ensure_ascii=False), encoding="utf-8"
        )

    @classmethod
    def load(cls, path: Path) -> BenchmarkManifest:
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            benchmark_version=data["benchmark_version"],
            generator_version=data["generator_version"],
            evaluator_version=data["evaluator_version"],
            metric_contract_version=data["metric_contract_version"],
            git_commit=data["git_commit"],
            execution_mode=data["execution_mode"],
            world_ids=data["world_ids"],
            world_config_hashes=data["world_config_hashes"],
            seed_registry=data["seed_registry"],
            policy_hash=data["policy_hash"],
            model_version=data["model_version"],
            prompt_hash=data["prompt_hash"],
            research_budget=data["research_budget"],
            creation_timestamp=data["creation_timestamp"],
        )

    def verify_world(self, world_id: str, config_hash: str) -> bool:
        """Verify a world's on-disk config hash matches the frozen one."""
        return (
            world_id in self.world_config_hashes
            and self.world_config_hashes[world_id] == config_hash
        )
