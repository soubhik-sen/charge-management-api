from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import engine


class DatabaseReadinessError(RuntimeError):
    """Raised when the runtime database cannot satisfy a readiness probe."""


def check_database_readiness(target_engine: Engine = engine) -> None:
    try:
        with target_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise DatabaseReadinessError("Database connectivity check failed.") from exc
