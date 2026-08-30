"""Real LLM rollout over a frozen synthetic environment."""

from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from marketpilot.agents.llm import build_llm_agent_registry
from marketpilot.agents.registry import AgentRegistry
from marketpilot.config import MarketPilotSettings
from marketpilot.domain.goals import ResearchGoal
from marketpilot.domain.state import ResearchState
from marketpilot.evaluation.evaluator import SystemEvaluator
from marketpilot.evaluation.schemas import EvaluationResult
from marketpilot.llm.models import LLMModelConfig
from marketpilot.llm.providers.openai import OpenAIChatClient
from marketpilot.llm.retry import RetryableLLMClient, RetryPolicy
from marketpilot.observability.trajectory import TrajectoryRecorder
from marketpilot.orchestration.planner import ResearchPlanner
from marketpilot.orchestration.runner import DAGRunner
from marketpilot.prompts.templates import build_default_prompt_registry
from marketpilot.research.budget import BudgetTracker
from marketpilot.research.dedup import SourceDeduplicator
from marketpilot.research.models import ResearchBudget
from marketpilot.research.store import ResearchStore
from marketpilot.synthetic.providers import load_synthetic_providers
from marketpilot.tools.registry import ToolRegistry
from marketpilot.tools.research import FetchPageTool, WebSearchTool

if TYPE_CHECKING:
    from marketpilot.llm.base import LLMClient


def build_synthetic_llm_agent_registry(
    settings: MarketPilotSettings,
    dataset_dir: Path,
) -> tuple[AgentRegistry, ToolRegistry]:
    config = LLMModelConfig(
        provider="openai",
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        timeout_seconds=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
        temperature=settings.llm_temperature,
        max_output_tokens=settings.llm_max_output_tokens,
    )
    client: LLMClient = OpenAIChatClient(config)
    client = RetryableLLMClient(
        client,
        policy=RetryPolicy(max_attempts=settings.llm_max_retries + 1),
    )
    search_provider, retriever = load_synthetic_providers(dataset_dir)
    registry = ToolRegistry()
    registry.register(WebSearchTool(search_provider, max_results=settings.max_search_results))
    registry.register(FetchPageTool(retriever))
    agents = build_llm_agent_registry(
        client=client,
        tool_registry=registry,
        prompt_registry=build_default_prompt_registry(),
        provider_name="openai",
        model_name=settings.llm_model,
        allowed_tools=("web_search", "fetch_page"),
        max_model_turns=4,
        max_tool_calls=6,
    )
    return agents, registry


async def run_llm_task(
    settings: MarketPilotSettings,
    dataset_dir: Path,
    *,
    category: str,
    market: str = "US",
) -> tuple[ResearchState, EvaluationResult]:
    agent_registry, tool_registry = build_synthetic_llm_agent_registry(settings, dataset_dir)
    goal = ResearchGoal(
        market=market,
        category=category,
        objective=f"Find promising products in {category} in the {market} market",
    )
    state = ResearchState(run_id=uuid4(), goal=goal, budget=goal.budget)
    planner = ResearchPlanner()
    for task in planner.plan(state.run_id, goal).tasks:
        state.add_task(task)
    recorder = TrajectoryRecorder(run_id=state.run_id)
    runner = DAGRunner(
        agent_registry=agent_registry,
        tool_registry=tool_registry,
        recorder=recorder,
        research_store=ResearchStore(),
        budget=BudgetTracker(ResearchBudget()),
        research_mode="mock",
        deduplicator=SourceDeduplicator(),
        evaluator=SystemEvaluator(),
    )
    return await runner.run(state)
