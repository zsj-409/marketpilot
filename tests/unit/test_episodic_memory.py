"""Episodic and skill memory tests."""

from marketpilot.memory.episodic import Episode, EpisodicMemory
from marketpilot.memory.skills import SkillMemory


def test_episodic_memory_structured_retrieval() -> None:
    memory = EpisodicMemory()
    memory.store(
        Episode(
            episode_id="e1",
            category="Pet Supplies",
            task_type="Risk Analysis",
            constraints=frozenset({"battery"}),
        )
    )
    memory.store(
        Episode(
            episode_id="e2",
            category="Beauty Tools",
            task_type="Product Analysis",
        )
    )
    results = memory.retrieve(category="Pet Supplies", task_type="Risk Analysis")
    assert [episode.episode_id for episode in results] == ["e1"]


def test_skill_extraction() -> None:
    memory = SkillMemory()
    episode = Episode(
        episode_id="e1",
        category="Pet Supplies",
        task_type="Risk Analysis",
        evidence_patterns=("battery", "shipping"),
        failure_reason=None,
        decision_outcome="WATCH",
    )
    skills = memory.extract(episode)
    assert any(skill.name == "battery product shipping-risk check" for skill in skills)
