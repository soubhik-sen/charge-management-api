from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker


def database_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:///./charge_management.db")


def _engine_kwargs(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {}


engine = create_engine(database_url(), pool_pre_ping=True, **_engine_kwargs(database_url()))


if engine.dialect.name == "sqlite":
    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
