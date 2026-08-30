"""Unit-of-work session lifecycle."""

from types import TracebackType

from sqlalchemy.orm import Session

from marketpilot.persistence.repositories import (
    BenchmarkRepository,
    ExperimentRepository,
    RunRepository,
    SourceRepository,
)


class UnitOfWork:
    """Own a session and expose persistence-agnostic repositories."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.runs = RunRepository(session)
        self.sources = SourceRepository(session)
        self.benchmarks = BenchmarkRepository(session)
        self.experiments = ExperimentRepository(session)

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "UnitOfWork":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            if exc_type is None:
                self.commit()
            else:
                self.rollback()
        finally:
            self.close()
