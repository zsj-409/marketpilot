"""Phase 2: Synthetic Market v3 — controlled research worlds (public facade).

See `marketpilot.world.core` for the implementation. This facade exposes the
world-building API without leaking oracle access into agent code paths: agents
only ever receive an `AgentWorldView`; evaluators receive a `WorldOracle`.
"""

from marketpilot.world.core import (
    AgentWorldView,
    Decision,
    DeterministicPolicy,
    Difficulty,
    Evidence,
    EvidenceFacet,
    RandomPolicy,
    ResearchAction,
    TrueProduct,
    World,
    WorldOracle,
    build_dev_conf_test_worlds,
    build_minimal_world,
    load_worlds,
    write_world_manifest,
)
from marketpilot.world.generator import (
    WorldGenerationSpec,
    generate_world,
    world_config_hash,
)
from marketpilot.world.manifest import BenchmarkManifest

__all__ = [
    "AgentWorldView",
    "BenchmarkManifest",
    "Decision",
    "DeterministicPolicy",
    "Difficulty",
    "Evidence",
    "EvidenceFacet",
    "RandomPolicy",
    "ResearchAction",
    "TrueProduct",
    "World",
    "WorldGenerationSpec",
    "WorldOracle",
    "build_dev_conf_test_worlds",
    "build_minimal_world",
    "generate_world",
    "load_worlds",
    "world_config_hash",
    "write_world_manifest",
]
