import os
import sys
from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

os.environ.setdefault("NO_PROXY", "api.deepseek.com")


@pytest.fixture
def settings(tmp_path, monkeypatch):
    from app import config

    test_settings = config.Settings(
        sqlite_path=tmp_path / "app.db",
        knowledge_dir=tmp_path / "knowledge",
        lancedb_dir=tmp_path / "lancedb",
        access_token="test-token",
        deepseek_api_key="sk-fake",
    )
    monkeypatch.setattr(config, "_settings", test_settings)
    return test_settings


@pytest.fixture
def client(settings):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
