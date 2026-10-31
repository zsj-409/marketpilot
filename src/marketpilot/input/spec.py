"""Unified ResearchTaskSpec: the single typed entry point for a research request.

Phase 1 requirement: unify user constraints, budget, world split, and raw
inputs into one strongly typed schema that every downstream layer consumes.
"""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from marketpilot.input.constraints import ConstraintSpec
from marketpilot.input.normalization import (
    NormalizedInventory,
    NormalizedMoney,
    NormalizedQuantity,
    NormalizedTimestamp,
)


class WorldSplit(StrEnum):
    """World-level data partition used by a task (Phase 2 / Phase 7 requirement)."""

    DEV = "dev"
    CONFIRMATION = "confirmation"
    TEST = "test"
    UNSPLIT = "unsplit"


class UnifiedResearchBudget(BaseModel):
    """One typed budget for research execution.

    Consolidates the two overlapping budget types that v1 had
    (domain.goals.ResearchBudget and research.models.ResearchBudget).
    All limits are optional; None means unlimited.
    """

    model_config = ConfigDict(frozen=True)

    max_tool_calls: int | None = Field(default=None, gt=0)
    max_search_queries: int | None = Field(default=None, gt=0)
    max_page_fetches: int | None = Field(default=None, gt=0)
    max_sources: int | None = Field(default=None, gt=0)
    max_llm_tokens: int | None = Field(default=None, gt=0)
    max_estimated_cost: float | None = Field(default=None, gt=0)
    max_research_duration_seconds: int | None = Field(default=None, gt=0)


class ProductRequest(BaseModel):
    """Minimal structured product request inside a task spec."""

    model_config = ConfigDict(frozen=True)

    category: str = Field(min_length=2, max_length=100)
    market: str = Field(min_length=2, max_length=100)
    objective: str = Field(min_length=3, max_length=1000)
    constraints: ConstraintSpec = ConstraintSpec()
    budget: UnifiedResearchBudget = UnifiedResearchBudget()
    world_split: WorldSplit = WorldSplit.UNSPLIT
    world_id: str | None = Field(default=None, max_length=200)


class ResearchTaskSpec(BaseModel):
    """The unified, strongly typed specification for one research task.

    This is the single normalized entry point: a downstream pipeline consumes
    one ResearchTaskSpec instead of ad-hoc dicts. Raw text is retained only for
    provenance; every structured field is normalized and validated.
    """

    model_config = ConfigDict(validate_assignment=True)

    spec_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    market: str
    category: str
    objective: str = Field(min_length=3, max_length=1000)
    product: ProductRequest | None = None

    constraints: ConstraintSpec = ConstraintSpec()
    budget: UnifiedResearchBudget = UnifiedResearchBudget()
    world_split: WorldSplit = WorldSplit.UNSPLIT
    world_id: str | None = Field(default=None, max_length=200)

    # Normalized structured observations (Phase 1 stable-input outputs).
    normalized_price: NormalizedMoney | None = None
    normalized_quantity: NormalizedQuantity | None = None
    normalized_inventory: NormalizedInventory | None = None
    normalized_timestamp: NormalizedTimestamp | None = None

    raw_objective_text: str = Field(default="", max_length=2000)
    source_language: str = Field(default="en", max_length=20)

    @model_validator(mode="after")
    def normalize_labels(self) -> "ResearchTaskSpec":
        """Deterministically normalize market/category without touching objective text."""
        self.__dict__["market"] = self.market.strip().upper()
        self.__dict__["category"] = self.category.strip().lower()
        if self.product is not None:
            self.__dict__["product"] = self.product.model_copy(
                update={
                    "market": self.product.market.strip().upper(),
                    "category": self.product.category.strip().lower(),
                }
            )
        return self


def task_spec_from_goal(
    *,
    market: str,
    category: str,
    objective: str,
    constraints: ConstraintSpec | None = None,
    budget: UnifiedResearchBudget | None = None,
    world_split: WorldSplit = WorldSplit.UNSPLIT,
    world_id: str | None = None,
) -> ResearchTaskSpec:
    """Build a ResearchTaskSpec from the fields the v1 CLI already parses.

    Keeps the migration path from ResearchGoal (domain/goals.py) cheap: the v1
    CLI can construct a spec from the same market/category/objective fields.
    """
    return ResearchTaskSpec(
        market=market,
        category=category,
        objective=objective,
        constraints=constraints or ConstraintSpec(),
        budget=budget or UnifiedResearchBudget(),
        world_split=world_split,
        world_id=world_id,
        product=ProductRequest(
            category=category,
            market=market,
            objective=objective,
            constraints=constraints or ConstraintSpec(),
            budget=budget or UnifiedResearchBudget(),
            world_split=world_split,
            world_id=world_id,
        ),
        raw_objective_text=objective,
    )
