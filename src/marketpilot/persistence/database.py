"""Database engine and session configuration."""

from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from marketpilot.persistence.models import Base


def create_sqlite_engine(path: str | Path = "marketpilot.db") -> Engine:
    """Create a zero-setup SQLite engine."""

    engine = create_engine(f"sqlite:///{path}", future=True)
    Base.metadata.create_all(engine)
    return engine


def create_engine_from_url(url: str) -> Engine:
    """Create an engine for SQLite or PostgreSQL URLs."""

    engine = create_engine(url, future=True)
    Base.metadata.create_all(engine)
    return engine


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
