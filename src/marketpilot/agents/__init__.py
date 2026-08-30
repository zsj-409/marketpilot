"""Agent contracts and deterministic implementations."""

from marketpilot.agents.base import Agent, AgentContext, AgentError, AgentResult
from marketpilot.agents.mock import build_default_agent_registry
from marketpilot.agents.registry import AgentRegistry

__all__ = [
    "Agent",
    "AgentContext",
    "AgentError",
    "AgentRegistry",
    "AgentResult",
    "build_default_agent_registry",
]
