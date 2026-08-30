"""Agent role registration and lookup."""

from marketpilot.agents.base import Agent
from marketpilot.domain.enums import AgentRole


class AgentRegistry:
    """A typed in-process registry of agents by role."""

    def __init__(self) -> None:
        self._agents: dict[AgentRole, Agent] = {}

    def register(self, agent: Agent) -> None:
        if agent.role in self._agents:
            raise ValueError(f"agent already registered: {agent.role}")
        self._agents[agent.role] = agent

    def get(self, role: AgentRole) -> Agent:
        try:
            return self._agents[role]
        except KeyError as exc:
            raise ValueError(f"unknown agent role: {role}") from exc

    def roles(self) -> list[AgentRole]:
        return sorted(self._agents, key=lambda role: role.value)
