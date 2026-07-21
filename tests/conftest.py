from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path

import pytest


TEST_DATABASE_PATH = Path(tempfile.gettempdir()) / f"charge_management_api_tests_{uuid.uuid4().hex}.sqlite"
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE_PATH.as_posix()}"
os.environ.setdefault("AUTH_MODE", "development")


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_database():
    from app.db.models import Base
    from app.db.session import engine

    Base.metadata.create_all(engine)
    yield
    engine.dispose()
    if os.environ["DATABASE_URL"].startswith("sqlite"):
        TEST_DATABASE_PATH.unlink(missing_ok=True)
