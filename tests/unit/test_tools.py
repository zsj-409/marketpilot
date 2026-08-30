"""Tool registry and mock tool tests."""

from uuid import uuid4

import pytest

from marketpilot.domain.enums import ToolResultStatus
from marketpilot.tools.base import ToolArguments, ToolContext, ToolInput
from marketpilot.tools.errors import ToolError
from marketpilot.tools.mock import MockSearchProductsTool, build_default_tool_registry
from marketpilot.tools.registry import ToolRegistry


def test_default_tools_are_registered() -> None:
    registry = build_default_tool_registry()
    assert "web_search" in registry.names()
    assert "fetch_page" in registry.names()
    assert "search_products" in registry.names()


def test_unknown_tool_returns_structured_error() -> None:
    registry = build_default_tool_registry()
    with pytest.raises(ToolError) as excinfo:
        registry.get("does_not_exist")
    assert excinfo.value.status is ToolResultStatus.INVALID_INPUT


async def test_invalid_tool_input_is_structured() -> None:
    run_id = uuid4()
    context = ToolContext(run_id=run_id, task_id=uuid4())
    with pytest.raises(ToolError) as excinfo:
        await MockSearchProductsTool().execute(ToolArguments(), context)
    assert excinfo.value.status is ToolResultStatus.INVALID_INPUT
    assert "category" in excinfo.value.message


async def test_registry_validates_required_arguments() -> None:
    registry = build_default_tool_registry()
    input_value = ToolInput(tool_name="search_products", arguments=ToolArguments())
    with pytest.raises(ToolError) as excinfo:
        registry.validate_input(input_value)
    assert excinfo.value.status is ToolResultStatus.INVALID_INPUT
    assert "category" in excinfo.value.message


def test_registry_rejects_duplicate_tools() -> None:
    registry = ToolRegistry()
    tool = MockSearchProductsTool()
    registry.register(tool)
    with pytest.raises(ValueError, match="already registered"):
        registry.register(tool)
