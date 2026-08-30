"""Persistence repository tests."""

from pathlib import Path

from marketpilot.persistence.database import create_sqlite_engine, session_factory
from marketpilot.persistence.unit_of_work import UnitOfWork


def test_sqlite_roundtrip(tmp_path: Path) -> None:
    engine = create_sqlite_engine(tmp_path / "test.db")
    session = session_factory(engine)()
    with UnitOfWork(session) as uow:
        suite_id = uow.benchmarks.save_suite("suite-a", "v1", {})
        task_id = uow.benchmarks.save_task(
            suite_id,
            {
                "task_key": "task-1",
                "goal": "goal",
                "market": "US",
                "category": "Pet Supplies",
                "constraints": {},
                "environment_id": "synthetic-market-v1",
                "allowed_budget": {},
                "rubric": {},
                "hidden_ground_truth_ref": {},
            },
        )
        run_id = uow.benchmarks.save_run(
            suite_id,
            task_id,
            "baseline",
            "mock",
            "mock",
            42,
            "COMPLETED",
            {},
        )
    assert run_id
    assert uow.benchmarks.get_suite("suite-a") is not None
