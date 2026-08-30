"""Runtime configuration for MarketPilot."""

from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class MarketPilotSettings(BaseSettings):
    """Typed application settings.

    Step 1 intentionally requires no credentials. Every value can be supplied
    through environment variables or a local `.env` file.
    """

    model_config = SettingsConfigDict(
        env_prefix="MARKETPILOT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    runs_dir: Path = Path("runs")
    log_level: str = "INFO"
    mode: Literal["mock", "llm"] = "mock"
    llm_provider: str = "mock"
    llm_model: str = "mock-research-model"
    llm_api_key: SecretStr | None = None
    llm_base_url: str | None = None
    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 2
    llm_temperature: float = 0.0
    llm_max_output_tokens: int = 1024
    llm_max_model_turns: int = 4
    llm_max_tool_calls: int = 8
    llm_max_calls_per_task: int = 12
    llm_max_rollout_count: int = 4
    llm_total_call_limit: int | None = None
    research_mode: Literal["mock", "live", "replay"] = "mock"
    search_provider: str = "tavily"
    search_api_key: SecretStr | None = None
    retrieval_timeout_seconds: float = 10.0
    max_page_bytes: int = 1_000_000
    max_search_results: int = 5
    replay_run: str | None = None
    research_max_search_queries: int | None = None
    research_max_page_fetches: int | None = None
    research_max_sources: int | None = None
    datasets_dir: Path = Path("datasets")
    benchmark_runs_dir: Path = Path("benchmark_runs")
    database_url: str = "sqlite:///marketpilot.db"
