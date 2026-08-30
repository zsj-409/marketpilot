"""Benchmark suite construction."""

from uuid import NAMESPACE_URL, uuid5

from marketpilot.benchmark.models import BenchmarkSuite, BenchmarkTask
from marketpilot.synthetic.rules import CATEGORY_PROFILES

FAMILIES = [
    "Opportunity Discovery",
    "Product Analysis",
    "Competitive Analysis",
    "Customer Pain Point Discovery",
    "Risk Analysis",
    "Constraint-based Product Selection",
]


def build_synthetic_suite(
    suite_id: str = "marketpilot-synthetic-v1",
    version: str = "v1",
) -> BenchmarkSuite:
    """Build 30+ meaningful tasks across categories and families."""

    tasks: list[BenchmarkTask] = []
    categories = list(CATEGORY_PROFILES)
    index = 0
    difficulties = ["easy", "medium", "hard"]
    for family in FAMILIES:
        for category in categories:
            difficulty = difficulties[index % len(difficulties)]
            constraints = {"minimum_margin": 0.25, "maximum_risk": 0.6}
            if family == "Constraint-based Product Selection":
                constraints = {"minimum_margin": 0.4, "maximum_risk": 0.4}
            tasks.append(
                BenchmarkTask(
                    task_id=uuid5(
                        NAMESPACE_URL,
                        f"marketpilot:benchmark:{suite_id}:{family}:{category}",
                    ),
                    task_key=(
                        f"{family.replace(' ', '-').lower()}-{category.replace(' ', '-').lower()}"
                    ),
                    family=family,
                    difficulty=difficulty,
                    goal=f"{family} for {category} in the US market",
                    market="US",
                    category=category,
                    constraints=constraints,
                    environment_id="synthetic-market-v1",
                    allowed_budget={"search_queries": 4, "page_fetches": 6},
                    rubric={"evaluate": ["opportunity", "risk", "constraints"]},
                    hidden_ground_truth_ref={"category": category},
                )
            )
            index += 1
    return BenchmarkSuite(suite_id=suite_id, name=suite_id, version=version, tasks=tasks)
