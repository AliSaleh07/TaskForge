"""Pytest configuration and test fixtures for TaskForge."""

import os
import tempfile
import pytest
from starlette.testclient import TestClient

from taskforge.config import settings
from taskforge.database import init_db
from taskforge.main import app


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    temp_dir = tempfile.mkdtemp()
    test_db_path = os.path.join(temp_dir, "test_taskforge.db")
    settings.DATABASE_PATH = test_db_path
    settings.SECRET_KEY = "test-secret-key-for-unit-testing-32bytes"
    init_db(test_db_path)
    yield
    if os.path.exists(test_db_path):
        try:
            os.remove(test_db_path)
        except Exception:
            pass


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
