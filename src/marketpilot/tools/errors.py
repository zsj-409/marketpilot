"""Structured tool failures."""

from marketpilot.domain.enums import ToolResultStatus


class ToolError(Exception):
    """A typed tool failure with a machine-readable status."""

    def __init__(self, status: ToolResultStatus, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
