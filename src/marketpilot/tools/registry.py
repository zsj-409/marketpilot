"""Tool registration and lookup."""

from marketpilot.domain.enums import ToolResultStatus
from marketpilot.tools.base import Tool, ToolInput
from marketpilot.tools.errors import ToolError


class ToolRegistry:
    """A typed in-process registry of available tools."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        name = tool.metadata.name
        if name in self._tools:
            raise ValueError(f"tool already registered: {name}")
        self._tools[name] = tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolError(
                ToolResultStatus.INVALID_INPUT,
                f"unknown tool: {name}",
            ) from exc

    def has(self, name: str) -> bool:
        return name in self._tools

    def names(self) -> list[str]:
        return sorted(self._tools)

    def validate_input(self, tool_input: ToolInput) -> None:
        tool = self.get(tool_input.tool_name)
        required = tool.metadata.input_schema.get("required", [])
        if not isinstance(required, list):
            raise ToolError(
                ToolResultStatus.PERMANENT_ERROR,
                f"invalid required-field metadata for tool: {tool.metadata.name}",
            )
        provided = set(tool_input.arguments.model_dump(exclude_none=True))
        missing = [field for field in required if field not in provided]
        if missing:
            raise ToolError(
                ToolResultStatus.INVALID_INPUT,
                f"missing required arguments for {tool.metadata.name}: {missing}",
            )
