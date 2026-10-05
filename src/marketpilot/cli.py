"""Command-line entry points for MarketPilot."""

import argparse
import asyncio
import json
import platform
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast
from uuid import uuid4

from marketpilot.agents.llm import build_llm_agent_registry
from marketpilot.agents.mock import build_default_agent_registry
from marketpilot.agents.registry import AgentRegistry
from marketpilot.benchmark.export import export_trajectories
from marketpilot.benchmark.runner import BenchmarkRunner
from marketpilot.config import MarketPilotSettings
from marketpilot.domain.goals import ResearchGoal
from marketpilot.domain.state import ResearchState
from marketpilot.evaluation.evaluator import SystemEvaluator
from marketpilot.llm.budget import LLMBudgetGuard
from marketpilot.llm.errors import LLMAuthenticationError
from marketpilot.llm.models import LLMModelConfig
from marketpilot.llm.providers.mock import (
    MockLLMClient,
    build_demo_llm_responses,
    build_research_demo_llm_responses,
)
from marketpilot.llm.registry import build_default_llm_client_registry
from marketpilot.llm.retry import RetryableLLMClient, RetryPolicy
from marketpilot.memory.in_memory import InMemoryMemoryStore
from marketpilot.observability.logging import configure_logging
from marketpilot.observability.trajectory import TrajectoryRecorder
from marketpilot.orchestration.planner import ResearchPlanner
from marketpilot.orchestration.runner import DAGRunner
from marketpilot.persistence.database import create_sqlite_engine, session_factory
from marketpilot.persistence.unit_of_work import UnitOfWork
from marketpilot.product_selection.controller import TerminationController
from marketpilot.product_selection.critic import DecisionCritic
from marketpilot.product_selection.decision import DecisionModule
from marketpilot.product_selection.live_environment import build_live_research_environment
from marketpilot.product_selection.loop import ClosedLoopRunner
from marketpilot.product_selection.mock_environment import make_environment
from marketpilot.product_selection.report import write_product_report
from marketpilot.product_selection.workers import ResearchEnvironment, WorkerRegistry
from marketpilot.prompts.templates import build_default_prompt_registry
from marketpilot.reporting.report import build_run_report, render_report_html
from marketpilot.research.budget import BudgetTracker
from marketpilot.research.dedup import SourceDeduplicator
from marketpilot.research.models import ResearchBudget
from marketpilot.research.providers.mock import build_mock_research_providers
from marketpilot.research.providers.retrieval import HTTPPageRetriever, PageRetriever
from marketpilot.research.providers.search import SearchProvider, TavilySearchProvider
from marketpilot.research.replay import ReplayStore
from marketpilot.research.store import ResearchStore
from marketpilot.synthetic.generator import SyntheticMarketGenerator
from marketpilot.synthetic.validation import validate_dataset
from marketpilot.tools.mock import build_default_tool_registry
from marketpilot.tools.registry import ToolRegistry
from marketpilot.tools.research import FetchPageTool, WebSearchTool

if TYPE_CHECKING:
    from marketpilot.llm.base import LLMClient

DEFAULT_GOAL = "Find promising pet products in the US market"


def _parse_goal(goal: str) -> ResearchGoal:
    """Parse the demo goal into a typed research goal."""

    market_match = re.search(r"in the ([A-Za-z ]+?) market", goal, flags=re.IGNORECASE)
    category_match = re.search(
        r"(?:promising|best|top)\s+([A-Za-z ]+?)\s+(?:products|items)",
        goal,
        flags=re.IGNORECASE,
    )
    market = (market_match.group(1) if market_match else "US").strip().upper()
    category = category_match.group(1).strip().lower() if category_match else "general products"
    return ResearchGoal(
        market=market,
        category=f"{category} supplies" if category != "general products" else category,
        objective=goal.strip(),
    )


async def _run_demo(
    goal_text: str,
    runs_dir: Path,
    agent_registry: AgentRegistry | None = None,
    *,
    mode: str = "mock",
    provider: str = "mock",
    model: str = "mock-research-model",
    tool_registry: ToolRegistry | None = None,
    research_store: ResearchStore | None = None,
    budget: BudgetTracker | None = None,
    replay_store: ReplayStore | None = None,
    research_mode: str = "mock",
    deduplicator: SourceDeduplicator | None = None,
) -> Path:
    goal = _parse_goal(goal_text)
    run_id = uuid4()
    state = ResearchState(run_id=run_id, goal=goal, budget=goal.budget)
    planner = ResearchPlanner()
    dag = planner.plan(run_id, goal)
    for task in dag.tasks:
        state.add_task(task)

    recorder = TrajectoryRecorder(run_id=run_id)
    runner = DAGRunner(
        agent_registry=agent_registry or build_default_agent_registry(),
        tool_registry=tool_registry or build_default_tool_registry(),
        recorder=recorder,
        memory_store=InMemoryMemoryStore(),
        evaluator=SystemEvaluator(),
        research_store=research_store,
        budget=budget,
        replay_store=replay_store,
        research_mode=research_mode,
        deduplicator=deduplicator,
    )
    final_state, evaluation = await runner.run(state)

    run_dir = runs_dir / str(run_id)
    recorder.write_trajectory(run_dir / "trajectory.jsonl")
    recorder.write_final_state(run_dir / "final_state.json", final_state)
    recommendation = next(iter(final_state.recommendations.values()), None)
    summary: dict[str, str | int | float | bool] = {
        "run_id": str(run_id),
        "status": final_state.status.value,
        "market": final_state.goal.market,
        "category": final_state.goal.category,
        "evaluation_passed": evaluation.passed,
        "task_success_rate": evaluation.metrics.task_success_rate,
        "evidence_coverage": evaluation.metrics.evidence_coverage,
        "tool_success_rate": evaluation.metrics.tool_success_rate,
        "recommendation": (
            recommendation.rationale
            if recommendation is not None
            else "No recommendation produced."
        ),
        "decision": recommendation.decision.value if recommendation is not None else "NONE",
        "mode": mode,
        "research_mode": research_mode,
        "llm_provider": provider,
        "llm_model": model,
        "llm_calls": final_state.metrics.llm_calls,
        "llm_input_tokens": final_state.metrics.llm_input_tokens,
        "llm_output_tokens": final_state.metrics.llm_output_tokens,
        "llm_total_tokens": final_state.metrics.llm_total_tokens,
        "llm_failed_calls": final_state.metrics.llm_failed_calls,
        "llm_retry_count": final_state.metrics.llm_retry_count,
        "llm_estimated_cost": final_state.metrics.llm_estimated_cost or 0.0,
        "tool_calls": final_state.metrics.tool_calls,
    }
    recorder.write_summary(run_dir / "summary.json", summary)
    _write_sources(run_dir, research_store)
    if replay_store is not None and research_mode in {"mock", "live"}:
        replay_store.write(run_dir / "replay.jsonl")
    report = build_run_report(run_dir)
    render_report_html(report, run_dir / "report.html")
    return run_dir


def _write_sources(run_dir: Path, research_store: ResearchStore | None) -> None:
    if research_store is None:
        return
    path = run_dir / "sources.jsonl"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for source in research_store.sources:
            payload = source.model_dump(mode="json", exclude_none=True)
            payload["kind"] = "source"
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        for retrieval in research_store.retrievals:
            payload = retrieval.model_dump(mode="json", exclude_none=True)
            payload["kind"] = "retrieval"
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        for snapshot in research_store.snapshots:
            payload = snapshot.model_dump(mode="json", exclude_none=True)
            payload["kind"] = "snapshot"
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _build_llm_runtime(
    settings: MarketPilotSettings,
    *,
    research_mode: str | None = None,
    tool_registry: ToolRegistry | None = None,
) -> AgentRegistry:
    config = LLMModelConfig(
        provider="openai",
        model=settings.llm_model or "gpt-4o-mini",
        api_key=settings.llm_api_key,
        timeout_seconds=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
        temperature=settings.llm_temperature,
        max_output_tokens=settings.llm_max_output_tokens,
    )
    if settings.llm_provider == "mock":
        research = research_mode in {"mock", "live", "replay"}
        responses = build_research_demo_llm_responses() if research else build_demo_llm_responses()
        client: LLMClient = MockLLMClient(responses_by_prompt=responses)
    else:
        client = build_default_llm_client_registry().create(config)
    client = RetryableLLMClient(
        client,
        policy=RetryPolicy(max_attempts=settings.llm_max_retries + 1),
    )
    tools = tool_registry or build_default_tool_registry()
    prompt_registry = build_default_prompt_registry()
    allowed_tools: tuple[str, ...] | None = None
    if research_mode in {"mock", "live", "replay"}:
        allowed_tools = ("web_search", "fetch_page")
    agent_registry = build_llm_agent_registry(
        client=client,
        tool_registry=tools,
        prompt_registry=prompt_registry,
        provider_name=settings.llm_provider,
        model_name=settings.llm_model,
        allowed_tools=allowed_tools,
        max_model_turns=settings.llm_max_model_turns,
        max_tool_calls=settings.llm_max_tool_calls,
    )
    return agent_registry


def _build_research_context(
    settings: MarketPilotSettings,
    research_mode: str,
) -> tuple[ToolRegistry, ResearchStore, BudgetTracker, ReplayStore | None, SourceDeduplicator]:
    store = ResearchStore()
    budget = BudgetTracker(
        ResearchBudget(
            max_search_queries=settings.research_max_search_queries,
            max_page_fetches=settings.research_max_page_fetches,
            max_sources=settings.research_max_sources,
        )
    )
    deduplicator = SourceDeduplicator()
    replay_store: ReplayStore | None = None
    search_provider: SearchProvider
    retriever: PageRetriever

    if research_mode == "replay":
        if settings.replay_run is None:
            print("replay mode requires --replay-run <RUN_ID>", file=sys.stderr)
            raise SystemExit(2)
        replay_store = ReplayStore()
        replay_path = settings.runs_dir / settings.replay_run / "replay.jsonl"
        if not replay_path.exists():
            print(f"replay file not found: {replay_path}", file=sys.stderr)
            raise SystemExit(2)
        replay_store.load(replay_path)
        search_provider, retriever = build_mock_research_providers()
    elif research_mode == "live":
        key = settings.search_api_key.get_secret_value() if settings.search_api_key else None
        if settings.search_provider == "tavily" and key is None:
            print(
                "live research requires MARKETPILOT_SEARCH_API_KEY",
                file=sys.stderr,
            )
            raise SystemExit(2)
        search_provider = TavilySearchProvider(
            api_key=key or "",
            timeout_seconds=settings.retrieval_timeout_seconds,
        )
        retriever = HTTPPageRetriever(
            timeout_seconds=settings.retrieval_timeout_seconds,
            max_bytes=settings.max_page_bytes,
        )
        replay_store = ReplayStore()
    else:
        search_provider, retriever = build_mock_research_providers()
        replay_store = ReplayStore()

    registry = ToolRegistry()
    registry.register(WebSearchTool(search_provider, max_results=settings.max_search_results))
    registry.register(FetchPageTool(retriever))
    return registry, store, budget, replay_store, deduplicator


def _cmd_dataset_generate(settings: MarketPilotSettings, dataset: str, seed: int) -> None:
    if dataset != "synthetic-market-v1":
        print(f"unknown dataset: {dataset}", file=sys.stderr)
        raise SystemExit(2)
    generator = SyntheticMarketGenerator(seed=seed)
    directory = settings.datasets_dir / "synthetic-market-v1"
    manifest = generator.write(directory)
    products, _, reviews, _ = generator.generate()
    issues = validate_dataset(products, review_count=len(reviews))
    if issues:
        for issue in issues[:5]:
            print(f"validation issue: {issue.message}", file=sys.stderr)
        raise SystemExit(1)
    print(f"Dataset: {directory.resolve()}")
    print(f"Products: {manifest.product_count}")
    print(f"Reviews: {manifest.review_count}")
    print(f"Sources: {manifest.source_count}")


def _cmd_benchmark(
    settings: MarketPilotSettings,
    suite: str,
    strategy: str,
    provider: str,
    model: str,
    n: int,
    seed: int,
) -> None:
    runner = BenchmarkRunner(
        datasets_dir=settings.datasets_dir,
        output_dir=settings.benchmark_runs_dir,
        suite_name=suite,
        strategy_name=strategy,
        n=n,
        seed=seed,
        provider=provider,
        model=model,
    )
    manifest, results, metrics = runner.run()
    print(f"Experiment: {manifest.experiment_id}")
    print(f"Artifacts: {(settings.benchmark_runs_dir / manifest.experiment_id).resolve()}")
    print(f"Tasks: {metrics['task_count']}")
    print(f"Success rate: {metrics['success_rate']:.3f}")
    print(f"Mean regret: {metrics['mean_regret']:.4f}")
    print(f"Mean top-k recall: {metrics['mean_top_k_recall']:.3f}")

    if settings.database_url.startswith("sqlite"):
        engine = create_sqlite_engine(settings.database_url.removeprefix("sqlite:///"))
        session = session_factory(engine)()
        with UnitOfWork(session) as uow:
            suite_id = uow.benchmarks.save_suite(suite, "v1", {})
            for result in results:
                task = {
                    "task_key": result.task_key,
                    "goal": result.family,
                    "market": "US",
                    "category": result.category,
                    "constraints": {},
                    "environment_id": "synthetic-market-v1",
                    "allowed_budget": {},
                    "rubric": {},
                    "hidden_ground_truth_ref": {"category": result.category},
                }
                task_id = uow.benchmarks.save_task(suite_id, task)
                uow.benchmarks.save_run(
                    suite_id,
                    task_id,
                    strategy,
                    model,
                    provider,
                    seed,
                    result.status,
                    result.model_dump(mode="json"),
                )
            uow.experiments.save(manifest.model_dump(mode="json"))


def _cmd_benchmark_compare(
    settings: MarketPilotSettings, experiment_a: str, experiment_b: str
) -> None:
    def load_metrics(experiment_id: str) -> dict[str, object]:
        path = settings.benchmark_runs_dir / experiment_id / "metrics.json"
        if not path.exists():
            print(f"missing experiment metrics: {path}", file=sys.stderr)
            raise SystemExit(2)
        return dict(json.loads(path.read_text(encoding="utf-8")))

    left = load_metrics(experiment_a)
    right = load_metrics(experiment_b)
    print(f"{'metric':<28} {'A':>12} {'B':>12}")
    for key in (
        "task_count",
        "success_rate",
        "mean_regret",
        "mean_top_k_recall",
        "mean_verifier_score",
    ):
        print(f"{key:<28} {left.get(key, 'N/A')!s:>12} {right.get(key, 'N/A')!s:>12}")


def _cmd_showcase(settings: MarketPilotSettings) -> None:
    dataset_dir = settings.datasets_dir / "synthetic-market-v1"
    if not (dataset_dir / "manifest.json").exists():
        _cmd_dataset_generate(settings, "synthetic-market-v1", 42)
    engine = create_sqlite_engine(settings.database_url.removeprefix("sqlite:///"))
    session = session_factory(engine)()
    with UnitOfWork(session) as uow:
        run_dir = asyncio.run(
            _run_demo(
                DEFAULT_GOAL,
                settings.runs_dir,
                mode="llm",
                provider="mock",
                model="synthetic-showcase",
            )
        )
        uow.experiments.save(
            {
                "name": "showcase",
                "dataset": "synthetic-market-v1",
                "dataset_version": "v1",
                "generator_version": "1.0.0",
                "seed": 42,
                "benchmark_suite": "synthetic",
                "strategy": "showcase",
                "model": "synthetic-showcase",
                "provider": "mock",
            }
        )
        showcase_dir = settings.benchmark_runs_dir / "showcase"
        showcase_dir.mkdir(parents=True, exist_ok=True)
        (showcase_dir / "run_dir.txt").write_text(str(run_dir), encoding="utf-8")
        print(f"Showcase run: {run_dir.resolve()}")
        print(f"Report: {(run_dir / 'report.html').resolve()}")
        print(f"Database: {settings.database_url}")


def _cmd_trajectories_export(settings: MarketPilotSettings, run_dir: str, output: str) -> None:
    count = export_trajectories(Path(run_dir), Path(output))
    print(f"Exported {count} trajectory examples to {Path(output).resolve()}")


def _cmd_llm_smoke(settings: MarketPilotSettings) -> None:
    from marketpilot.llm.models import LLMMessage, LLMMessageRole, LLMRequest
    from marketpilot.llm.providers.openai import OpenAIChatClient

    config = LLMModelConfig(
        provider="openai",
        model=settings.llm_model or "gpt-4o-mini",
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        timeout_seconds=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
        temperature=settings.llm_temperature,
        max_output_tokens=settings.llm_max_output_tokens,
    )
    try:
        client: LLMClient = OpenAIChatClient(config)
    except LLMAuthenticationError as exc:
        print(f"LIVE LLM NOT EXECUTED: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    client = LLMBudgetGuard(
        client,
        max_calls=1,
        max_output_tokens=settings.llm_max_output_tokens,
    )
    request = LLMRequest(
        provider=settings.llm_provider,
        model=settings.llm_model,
        messages=[LLMMessage(role=LLMMessageRole.USER, content="Reply with the single word: ok")],
        temperature=0.0,
        max_output_tokens=settings.llm_max_output_tokens,
    )
    response = asyncio.run(client.generate(request))
    print(f"provider={response.provider}")
    print(f"model={response.model}")
    print(f"response_id={response.response_id}")
    print(f"input_tokens={response.usage.input_tokens}")
    print(f"output_tokens={response.usage.output_tokens}")
    print(f"latency_ms={response.usage.latency_ms}")


def _cmd_doctor(settings: MarketPilotSettings) -> None:
    print("MarketPilot version: 1.1.0")
    print(f"Python: {platform.python_version()}")
    print("Offline capability: available")
    print(f"LLM provider: {settings.llm_provider or 'not configured'}")
    print(f"LLM model: {settings.llm_model or 'not configured'}")
    print("LLM API key: " + ("configured" if settings.llm_api_key else "missing"))
    print("LLM base URL: " + (settings.llm_base_url or "not configured"))
    print("Search API key: " + ("configured" if settings.search_api_key else "missing"))
    print(f"Database URL: {settings.database_url}")
    print("Execution modes: mock, llm")
    print("Research modes: mock, live, replay")
    print("Web workbench: marketpilot workbench (--host 127.0.0.1 --port 8600)")


def _cmd_workbench(host: str, port: int) -> None:
    import uvicorn

    from marketpilot.webui.server import create_app

    app = create_app()
    print("MarketPilot Workbench")
    print(f"  URL: http://{host}:{port}")
    print("  Stop with Ctrl+C. Artifacts are read from runs/, benchmark_runs/, datasets/.")
    uvicorn.run(app, host=host, port=port, log_level="warning")


def _cmd_select_product(settings: MarketPilotSettings, args: argparse.Namespace) -> None:
    environment: ResearchEnvironment
    if args.mode == "live":
        try:
            environment = build_live_research_environment(settings)
        except LLMAuthenticationError as exc:
            print(f"LIVE VALIDATION NOT EXECUTED: {exc}", file=sys.stderr)
            raise SystemExit(2) from exc
        asyncio.run(environment.seed(args.goal, limit=8))
    else:
        environment = make_environment()
    runner = ClosedLoopRunner(
        DecisionCritic(),
        TerminationController(max_rounds=args.max_rounds, max_dynamic_tasks=6),
        DecisionModule(),
        WorkerRegistry(),
    )
    result = runner.run(environment, {"max_price": 80, "no_battery": False})
    run_dir = settings.runs_dir / f"select-{result.termination.value.lower()}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "recommendation.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
    (run_dir / "candidates.json").write_text(
        json.dumps(environment.candidates(), indent=2), encoding="utf-8"
    )
    write_product_report(run_dir / "report.html", args.goal, result, environment.candidates())
    print(f"Goal: {args.goal}")
    print(f"Termination: {result.termination.value}")
    print(f"Research rounds: {result.research_rounds}")
    print(f"Follow-up investigations: {result.followup_investigations}")
    print(f"Sources used: {result.followup_investigations}")
    print(f"Artifacts: {run_dir.resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="marketpilot")
    subparsers = parser.add_subparsers(dest="command", required=True)
    demo = subparsers.add_parser("demo", help="Run a MarketPilot research demo")
    demo.add_argument("--goal", default=DEFAULT_GOAL, help="Research goal text")
    demo.add_argument(
        "--mode",
        choices=["mock", "llm"],
        default=None,
        help="Execution mode: mock agents (default) or LLM agents",
    )
    demo.add_argument("--provider", default=None, help="LLM provider in llm mode")
    demo.add_argument("--model", default=None, help="LLM model in llm mode")
    demo.add_argument(
        "--research-mode",
        choices=["mock", "live", "replay"],
        default=None,
        help="Research environment mode",
    )
    demo.add_argument("--replay-run", default=None, help="Run ID to replay from")

    report = subparsers.add_parser("report", help="Generate a static run report")
    report.add_argument("--run-dir", required=True, help="Path to a run directory")

    dataset = subparsers.add_parser("dataset", help="Manage synthetic datasets")
    dataset_sub = dataset.add_subparsers(dest="dataset_command", required=True)
    dataset_generate = dataset_sub.add_parser("generate", help="Generate a synthetic dataset")
    dataset_generate.add_argument("--dataset", default="synthetic-market-v1")
    dataset_generate.add_argument("--seed", type=int, default=42)

    benchmark = subparsers.add_parser("benchmark", help="Run a synthetic benchmark")
    benchmark_sub = benchmark.add_subparsers(dest="benchmark_command")
    benchmark_run = benchmark_sub.add_parser("run", help="Run one benchmark experiment")
    benchmark_run.add_argument("--suite", default="marketpilot-synthetic-v1")
    benchmark_run.add_argument("--strategy", default="baseline")
    benchmark_run.add_argument("--provider", default="mock")
    benchmark_run.add_argument("--model", default="synthetic-baseline")
    benchmark_run.add_argument("--n", type=int, default=1)
    benchmark_run.add_argument("--seed", type=int, default=42)
    benchmark_compare = benchmark_sub.add_parser("compare", help="Compare two experiments")
    benchmark_compare.add_argument("experiment_a")
    benchmark_compare.add_argument("experiment_b")

    subparsers.add_parser("showcase", help="Run the zero-credential showcase")

    trajectories = subparsers.add_parser("trajectories", help="Export trajectory examples")
    trajectories_sub = trajectories.add_subparsers(dest="trajectories_command", required=True)
    trajectories_export = trajectories_sub.add_parser("export", help="Export trajectory JSONL")
    trajectories_export.add_argument("--run-dir", required=True)
    trajectories_export.add_argument("--output", required=True)

    llm = subparsers.add_parser("llm", help="Live LLM provider validation")
    llm_sub = llm.add_subparsers(dest="llm_command", required=True)
    llm_sub.add_parser("smoke", help="Run one minimal real model call")

    subparsers.add_parser("doctor", help="Show environment diagnostics")

    workbench = subparsers.add_parser(
        "workbench", help="Launch the interactive web workbench"
    )
    workbench.add_argument("--host", default="127.0.0.1", help="Bind address (default 127.0.0.1)")
    workbench.add_argument("--port", type=int, default=8600, help="Port (default 8600)")

    select_product = subparsers.add_parser(
        "select-product", help="Run closed-loop product selection"
    )
    select_product.add_argument("--goal", default="Find a promising pet product")
    select_product.add_argument("--mode", choices=["mock", "live"], default="mock")
    select_product.add_argument("--max-rounds", type=int, default=3)
    select_product.add_argument("--max-sources", type=int, default=30)

    args = parser.parse_args()
    settings = MarketPilotSettings()
    if args.command == "report":
        run_dir = Path(args.run_dir)
        report_path = run_dir / "report.html"
        render_report_html(build_run_report(run_dir), report_path)
        print(f"Report: {report_path.resolve()}")
        return
    if args.command == "dataset":
        _cmd_dataset_generate(settings, args.dataset, args.seed)
        return
    if args.command == "benchmark":
        if args.benchmark_command == "compare":
            _cmd_benchmark_compare(settings, args.experiment_a, args.experiment_b)
        else:
            _cmd_benchmark(
                settings, args.suite, args.strategy, args.provider, args.model, args.n, args.seed
            )
        return
    if args.command == "showcase":
        _cmd_showcase(settings)
        return
    if args.command == "trajectories":
        _cmd_trajectories_export(settings, args.run_dir, args.output)
        return
    if args.command == "llm":
        _cmd_llm_smoke(settings)
        return
    if args.command == "doctor":
        _cmd_doctor(settings)
        return
    if args.command == "workbench":
        _cmd_workbench(args.host, args.port)
        return
    if args.command == "select-product":
        _cmd_select_product(settings, args)
        return

    if args.mode is not None:
        settings = settings.model_copy(update={"mode": cast("Literal['mock', 'llm']", args.mode)})
    if args.provider is not None:
        settings = settings.model_copy(update={"llm_provider": args.provider})
    if args.model is not None:
        settings = settings.model_copy(update={"llm_model": args.model})
    if args.research_mode is not None:
        settings = settings.model_copy(
            update={
                "research_mode": cast(
                    "Literal['mock', 'live', 'replay']",
                    args.research_mode,
                )
            }
        )
    if args.replay_run is not None:
        settings = settings.model_copy(update={"replay_run": args.replay_run})
    configure_logging(settings.log_level)

    research_mode = settings.research_mode if args.research_mode is not None else None
    if research_mode is not None:
        tool_registry, research_store, budget, replay_store, deduplicator = _build_research_context(
            settings, research_mode
        )
        if settings.mode == "llm":
            try:
                agent_registry = _build_llm_runtime(
                    settings,
                    research_mode=research_mode,
                    tool_registry=tool_registry,
                )
            except LLMAuthenticationError as exc:
                print(f"LLM configuration error: {exc}", file=sys.stderr)
                raise SystemExit(2) from exc
        else:
            agent_registry = build_default_agent_registry()
        run_dir = asyncio.run(
            _run_demo(
                args.goal,
                settings.runs_dir,
                agent_registry,
                mode=settings.mode,
                provider=settings.llm_provider,
                model=settings.llm_model,
                tool_registry=tool_registry,
                research_store=research_store,
                budget=budget,
                replay_store=replay_store,
                research_mode=research_mode,
                deduplicator=deduplicator,
            )
        )
    else:
        if settings.mode == "llm":
            try:
                agent_registry = _build_llm_runtime(settings)
            except LLMAuthenticationError as exc:
                print(f"LLM configuration error: {exc}", file=sys.stderr)
                raise SystemExit(2) from exc
        else:
            agent_registry = build_default_agent_registry()
        run_dir = asyncio.run(
            _run_demo(
                args.goal,
                settings.runs_dir,
                agent_registry,
                mode=settings.mode,
                provider=settings.llm_provider,
                model=settings.llm_model,
            )
        )
    print(f"Run directory: {run_dir.resolve()}")
    print(f"Report: {(run_dir / 'report.html').resolve()}")


if __name__ == "__main__":
    main()
