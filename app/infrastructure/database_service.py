from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.domain.service import ChargeManagementService
from app.infrastructure.sqlalchemy_repository import SqlAlchemyChargeRepository


class DatabaseBackedChargeManagementService:
    """Runs each domain operation against an isolated database transaction."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def __getattr__(self, name: str) -> Callable[..., Any]:
        domain_method = getattr(ChargeManagementService, name, None)
        if not callable(domain_method):
            raise AttributeError(name)

        @wraps(domain_method)
        def invoke(*args: Any, **kwargs: Any) -> Any:
            with self._session_factory() as db:
                if self._is_mutation(name) and db.get_bind().dialect.name == "postgresql":
                    # The compatibility domain service mutates aggregate models.
                    # Serialize writes until each aggregate has a native row-level repository.
                    db.execute(
                        text("SELECT pg_advisory_xact_lock(:lock_key)"),
                        {"lock_key": 168449836269119},
                    )
                repository = SqlAlchemyChargeRepository(db)
                service = ChargeManagementService(repository)
                try:
                    result = getattr(service, name)(*args, **kwargs)
                    repository.flush()
                    db.commit()
                    return result
                except Exception:
                    db.rollback()
                    raise

        return invoke

    @staticmethod
    def _is_mutation(name: str) -> bool:
        return name != "initialization_data" and not name.startswith(("get_", "list_"))
