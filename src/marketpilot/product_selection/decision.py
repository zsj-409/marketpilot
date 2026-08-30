"""DecisionModule: rank candidates only from current structured state."""

from typing import Any
from uuid import UUID

from marketpilot.product_selection.workers import ResearchEnvironment


class DecisionModule:
    """Deterministic candidate comparison from evidence, not web access."""

    def rank(
        self,
        environment: ResearchEnvironment,
        constraints: dict[str, object],
    ) -> list[UUID]:
        candidates = environment.candidates()

        def score(candidate: dict[str, Any]) -> float:
            evidence = environment.evidence(UUID(str(candidate["candidate_id"])))
            demand = _signal(evidence.get("demand", []), positive=True)
            competition = _signal(evidence.get("competition", []), positive=False)
            risk = _signal(evidence.get("risk", []), positive=False)
            raw_price = candidate.get("price")
            price_penalty = float(str(raw_price)) / 100.0 if raw_price is not None else 0.0
            return demand - competition - risk - price_penalty

        ranked = sorted(candidates, key=score, reverse=True)
        return [UUID(str(candidate["candidate_id"])) for candidate in ranked]


def _signal(observations: list[str], positive: bool) -> float:
    negative = sum(1 for item in observations if item.startswith("negative"))
    conflict = sum(1 for item in observations if item == "conflict")
    if positive:
        score = 1.0 if observations else 0.0
        return max(0.2, score - 0.8 * negative - 0.4 * conflict)
    if not observations:
        return 0.0
    score = 1.0
    if negative:
        score += 0.8 * negative
    if conflict:
        score += 0.4 * conflict
    return score
