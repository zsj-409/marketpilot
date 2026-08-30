"""Deterministic offline tools for architecture validation."""

from hashlib import sha256
from typing import final

from marketpilot.domain.enums import ToolResultStatus
from marketpilot.tools.base import (
    ToolArguments,
    ToolContext,
    ToolMetadata,
    ToolOutput,
)
from marketpilot.tools.errors import ToolError
from marketpilot.tools.registry import ToolRegistry


def _require(arguments: ToolArguments, field: str) -> str:
    values: dict[str, str | None] = {
        "query": arguments.query,
        "category": arguments.category,
        "market": arguments.market,
        "product_name": arguments.product_name,
        "product_id": arguments.product_id,
        "memory_key": arguments.memory_key,
        "memory_value": arguments.memory_value,
        "url": arguments.url,
    }
    value = values[field]
    if value is None:
        raise ToolError(ToolResultStatus.INVALID_INPUT, f"missing required argument: {field}")
    return value


def _observation(summary: str, uri: str, observation: str, confidence: float) -> ToolOutput:
    return ToolOutput(
        summary=summary,
        source_uri=uri,
        observation=f"{observation}\nsha256:{sha256(observation.encode()).hexdigest()}",
        confidence=confidence,
    )


@final
class MockWebSearchTool:
    """Deterministic web-search stand-in."""

    def __init__(self) -> None:
        self._metadata = ToolMetadata(
            name="web_search",
            description="Search a mock web index for market and product queries.",
            version="1.0.0",
            input_schema={"required": ["query"]},
            risk_level="medium",
            timeout_seconds=10,
            retry_policy="exponential",
        )

    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata

    async def execute(self, arguments: ToolArguments, context: ToolContext) -> ToolOutput:
        query = _require(arguments, "query")
        return _observation(
            f"Mock search results for {query}",
            f"mock://search/{context.run_id}",
            f"Deterministic search result set for '{query}'.",
            0.72,
        )


@final
class MockFetchPageTool:
    """Deterministic page-fetch stand-in."""

    def __init__(self) -> None:
        self._metadata = ToolMetadata(
            name="fetch_page",
            description="Fetch a normalized mock page from a URI.",
            version="1.0.0",
            input_schema={"required": ["url"]},
            risk_level="medium",
            timeout_seconds=15,
            retry_policy="exponential",
        )

    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata

    async def execute(self, arguments: ToolArguments, context: ToolContext) -> ToolOutput:
        url = _require(arguments, "url")
        return _observation(
            "Mock page fetched",
            url,
            f"Deterministic normalized page content for run {context.run_id}.",
            0.68,
        )


@final
class MockSearchProductsTool:
    """Provider-neutral product catalog stand-in."""

    def __init__(self) -> None:
        self._metadata = ToolMetadata(
            name="search_products",
            description="Search a mock product catalog.",
            version="1.0.0",
            input_schema={"required": ["category", "market"]},
            risk_level="low",
        )

    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata

    async def execute(self, arguments: ToolArguments, context: ToolContext) -> ToolOutput:
        category = _require(arguments, "category")
        market = _require(arguments, "market")
        return _observation(
            f"Mock product candidates in {category}",
            f"mock://catalog/{market}/{category}/{context.run_id}",
            "Automatic pet feeder; slow feeder bowl; pet hair remover.",
            0.83,
        )


@final
class MockGetProductDetailsTool:
    """Provider-neutral product details stand-in."""

    def __init__(self) -> None:
        self._metadata = ToolMetadata(
            name="get_product_details",
            description="Return mock details for one product.",
            version="1.0.0",
            input_schema={"required": ["product_id"]},
        )

    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata

    async def execute(self, arguments: ToolArguments, context: ToolContext) -> ToolOutput:
        product_id = _require(arguments, "product_id")
        return _observation(
            f"Mock details for {product_id}",
            f"mock://products/{product_id}/{context.run_id}",
            "Price band: $28-$46; primary material: plastic; battery powered.",
            0.81,
        )


@final
class MockSearchReviewsTool:
    """Provider-neutral review search stand-in."""

    def __init__(self) -> None:
        self._metadata = ToolMetadata(
            name="search_reviews",
            description="Search mock product review themes.",
            version="1.0.0",
            input_schema={"required": ["product_name"]},
        )

    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata

    async def execute(self, arguments: ToolArguments, context: ToolContext) -> ToolOutput:
        product_name = _require(arguments, "product_name")
        return _observation(
            f"Mock review themes for {product_name}",
            f"mock://reviews/{product_name}/{context.run_id}",
            "Recurring complaints: battery reliability, app connectivity, cleaning difficulty.",
            0.79,
        )


@final
class MockGetMarketSignalTool:
    """Provider-neutral market signal stand-in."""

    def __init__(self) -> None:
        self._metadata = ToolMetadata(
            name="get_market_signal",
            description="Return a deterministic market signal.",
            version="1.0.0",
            input_schema={"required": ["category", "market"]},
        )

    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata

    async def execute(self, arguments: ToolArguments, context: ToolContext) -> ToolOutput:
        category = _require(arguments, "category")
        market = _require(arguments, "market")
        return _observation(
            f"Mock market signal for {category} in {market}",
            f"mock://market-signals/{market}/{category}/{context.run_id}",
            "Search demand is moderately rising; seasonality is low; competition is medium-high.",
            0.76,
        )


@final
class MockEstimateCostTool:
    """Deterministic landed-cost estimator."""

    def __init__(self) -> None:
        self._metadata = ToolMetadata(
            name="estimate_cost",
            description="Estimate deterministic unit cost.",
            version="1.0.0",
            input_schema={"required": ["product_name"]},
        )

    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata

    async def execute(self, arguments: ToolArguments, context: ToolContext) -> ToolOutput:
        product_name = _require(arguments, "product_name")
        return _observation(
            f"Mock cost estimate for {product_name}",
            f"mock://cost/{product_name}/{context.run_id}",
            "Estimated landed unit cost: $18.50; shipping weight: 1.2kg.",
            0.65,
        )


@final
class MockEstimateMarginTool:
    """Deterministic margin estimator."""

    def __init__(self) -> None:
        self._metadata = ToolMetadata(
            name="estimate_margin",
            description="Estimate deterministic gross margin.",
            version="1.0.0",
            input_schema={"required": ["product_name"]},
        )

    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata

    async def execute(self, arguments: ToolArguments, context: ToolContext) -> ToolOutput:
        product_name = _require(arguments, "product_name")
        return _observation(
            f"Mock margin estimate for {product_name}",
            f"mock://margin/{product_name}/{context.run_id}",
            "Estimated gross margin: 0.38; break-even units per month: 145.",
            0.63,
        )


@final
class MockRetrieveMemoryTool:
    """Deterministic memory retrieval stand-in."""

    def __init__(self) -> None:
        self._metadata = ToolMetadata(
            name="retrieve_memory",
            description="Retrieve a deterministic memory record.",
            version="1.0.0",
            input_schema={"required": ["memory_key"]},
        )

    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata

    async def execute(self, arguments: ToolArguments, context: ToolContext) -> ToolOutput:
        key = _require(arguments, "memory_key")
        return _observation(
            f"Mock memory for {key}",
            f"mock://memory/{key}/{context.run_id}",
            "Prior observation: automatic pet feeder demand is stable but competition is high.",
            0.70,
        )


@final
class MockStoreMemoryTool:
    """Deterministic memory write stand-in."""

    def __init__(self) -> None:
        self._metadata = ToolMetadata(
            name="store_memory",
            description="Store a deterministic memory record.",
            version="1.0.0",
            input_schema={"required": ["memory_key", "memory_value"]},
        )

    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata

    async def execute(self, arguments: ToolArguments, context: ToolContext) -> ToolOutput:
        key = _require(arguments, "memory_key")
        value = _require(arguments, "memory_value")
        return _observation(
            f"Stored mock memory {key}",
            f"mock://memory-write/{key}/{context.run_id}",
            value,
            1.0,
        )


def build_default_tool_registry() -> ToolRegistry:
    """Build the deterministic offline tool set."""

    registry = ToolRegistry()
    for tool in (
        MockWebSearchTool(),
        MockFetchPageTool(),
        MockSearchProductsTool(),
        MockGetProductDetailsTool(),
        MockSearchReviewsTool(),
        MockGetMarketSignalTool(),
        MockEstimateCostTool(),
        MockEstimateMarginTool(),
        MockRetrieveMemoryTool(),
        MockStoreMemoryTool(),
    ):
        registry.register(tool)
    return registry
