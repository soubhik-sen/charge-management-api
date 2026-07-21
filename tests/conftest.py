from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path

import pytest


TEST_DATABASE_PATH = Path(tempfile.gettempdir()) / f"charge_management_api_tests_{uuid.uuid4().hex}.sqlite"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE_PATH.as_posix()}"


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_database():
    yield
    from app.db.session import engine

    engine.dispose()
    TEST_DATABASE_PATH.unlink(missing_ok=True)
