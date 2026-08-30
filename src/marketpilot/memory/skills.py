"""Deterministic skill extraction and retrieval."""

from dataclasses import dataclass
from uuid import uuid4

from marketpilot.memory.episodic import Episode


@dataclass(frozen=True)
class Skill:
    skill_id: str
    name: str
    trigger: str
    action_template: str
    evidence: tuple[str, ...]
    outcome: str


_SKILL_TEMPLATES = {
    "high-review-depth saturation check": (
        "Saturation risk detected by review depth and seller count."
    ),
    "battery product shipping-risk check": (
        "Battery products require shipping and regulatory risk review."
    ),
    "seasonality validation": (
        "Validate that demand signals match the category seasonality profile."
    ),
    "complaint cluster verification": (
        "Verify complaint clusters before accepting a pain-point claim."
    ),
    "low-source-diversity recovery": ("Add an independent source before finalizing evidence."),
}


class SkillMemory:
    """Store reusable bounded, inspectable skills."""

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def extract(self, episode: Episode) -> list[Skill]:
        skills: list[Skill] = []
        for name, action in _SKILL_TEMPLATES.items():
            if name.split(" ")[0] in " ".join(
                episode.evidence_patterns + episode.verifier_feedback
            ):
                skill = Skill(
                    skill_id=str(uuid4()),
                    name=name,
                    trigger=f"category={episode.category}",
                    action_template=action,
                    evidence=episode.evidence_patterns,
                    outcome=episode.decision_outcome,
                )
                self._skills[skill.name] = skill
                skills.append(skill)
        if not skills and episode.failure_reason:
            skill = Skill(
                skill_id=str(uuid4()),
                name="recover-from-failure",
                trigger=f"failure={episode.failure_reason}",
                action_template="Apply the previously successful evidence pattern before retrying.",
                evidence=episode.evidence_patterns,
                outcome=episode.decision_outcome,
            )
            self._skills[skill.name] = skill
            skills.append(skill)
        return skills

    def retrieve(self, trigger_terms: set[str]) -> list[Skill]:
        return [
            skill
            for skill in self._skills.values()
            if any(term in skill.trigger for term in trigger_terms)
        ]

    def all(self) -> list[Skill]:
        return list(self._skills.values())

    def __len__(self) -> int:
        return len(self._skills)
