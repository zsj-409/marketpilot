"""Research goal and constraint contracts."""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ResearchConstraints(BaseModel):
    """User-defined business constraints."""

    model_config = ConfigDict(frozen=True)

    minimum_margin: float = Field(default=0.3, ge=0, le=1)
    maximum_risk: float = Field(default=0.5, ge=0, le=1)
    minimum_evidence_count: int = Field(default=1, ge=1)


class ResearchBudget(BaseModel):
    """Execution budget for a research run."""

    model_config = ConfigDict(frozen=True)

    max_tool_calls: int = Field(default=100, ge=1)
    max_wall_clock_seconds: int = Field(default=600, ge=1)
    max_token_cost: float = Field(default=0.0, ge=0)


class ResearchGoal(BaseModel):
    """A provider-neutral product research objective."""

    model_config = ConfigDict(frozen=True)

    market: str = Field(min_length=2, max_length=100)
    category: str = Field(min_length=2, max_length=100)
    objective: str = Field(min_length=3, max_length=500)
    constraints: ResearchConstraints = ResearchConstraints()
    budget: ResearchBudget = ResearchBudget()

    @model_validator(mode="after")
    def normalize_labels(self) -> "ResearchGoal":
        """Normalize labels without changing the user's objective text."""

        self.__dict__["market"] = self.market.strip().upper()
        self.__dict__["category"] = self.category.strip().lower()
        return self
