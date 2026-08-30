"""Default Step 2 prompt templates."""

from marketpilot.prompts.base import PromptRegistry, PromptSpec

MARKET_RESEARCH = PromptSpec(
    name="market_research",
    version="v1",
    description="Analyze market demand and trend signals.",
    template=(
        "Research objective: $objective\n"
        "Market: $market\n"
        "Category: $category\n"
        "Task: $task\n\n"
        "State context:\n$state_context\n\n"
        "Use the available tools if they help. Return only JSON matching:\n"
        "$json_schema"
    ),
)


PRODUCT_RESEARCH = PromptSpec(
    name="product_research",
    version="v1",
    description="Discover or aggregate product candidates and unit economics.",
    template=(
        "Research objective: $objective\n"
        "Market: $market\n"
        "Category: $category\n"
        "Task: $task\n\n"
        "State context:\n$state_context\n\n"
        "Use the available tools if they help. Return only JSON matching:\n"
        "$json_schema"
    ),
)


REVIEW_RESEARCH = PromptSpec(
    name="review_research",
    version="v1",
    description="Identify recurring customer pain points.",
    template=(
        "Research objective: $objective\n"
        "Market: $market\n"
        "Category: $category\n"
        "Task: $task\n\n"
        "State context:\n$state_context\n\n"
        "Use the available tools if they help. Return only JSON matching:\n"
        "$json_schema"
    ),
)


COMPETITOR_RESEARCH = PromptSpec(
    name="competitor_research",
    version="v1",
    description="Assess competitive intensity.",
    template=(
        "Research objective: $objective\n"
        "Market: $market\n"
        "Category: $category\n"
        "Task: $task\n\n"
        "State context:\n$state_context\n\n"
        "Use the available tools if they help. Return only JSON matching:\n"
        "$json_schema"
    ),
)


RISK_ANALYSIS = PromptSpec(
    name="risk_analysis",
    version="v1",
    description="Identify execution, competition, and regulatory risks.",
    template=(
        "Research objective: $objective\n"
        "Market: $market\n"
        "Category: $category\n"
        "Task: $task\n\n"
        "State context:\n$state_context\n\n"
        "Use the available tools if they help. Return only JSON matching:\n"
        "$json_schema"
    ),
)


DECISION = PromptSpec(
    name="decision",
    version="v1",
    description="Produce an evidence-grounded recommendation.",
    template=(
        "Research objective: $objective\n"
        "Market: $market\n"
        "Category: $category\n"
        "Task: $task\n\n"
        "State context:\n$state_context\n\n"
        "Return only JSON matching:\n$json_schema"
    ),
)


def build_default_prompt_registry() -> PromptRegistry:
    """Build the default prompt registry."""

    registry = PromptRegistry()
    for prompt in (
        MARKET_RESEARCH,
        PRODUCT_RESEARCH,
        REVIEW_RESEARCH,
        COMPETITOR_RESEARCH,
        RISK_ANALYSIS,
        DECISION,
    ):
        registry.register(prompt)
    return registry
