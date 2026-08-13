import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RAG_LIVE_TEST") != "1",
    reason="设置 RAG_LIVE_TEST=1 并配置 API key 后运行真实调用",
)


@pytest.fixture
def live_client(tmp_path, monkeypatch):
    from app import config

    real = config.Settings()
    test_settings = config.Settings(
        sqlite_path=tmp_path / "app.db",
        knowledge_dir=real.knowledge_dir,
        lancedb_dir=real.lancedb_dir,
        access_token="",
        deepseek_api_key=real.deepseek_api_key,
        anthropic_auth_token=real.anthropic_auth_token,
        gptgod_api_key=real.gptgod_api_key,
        gptgod_model=real.gptgod_model,
        gptgod_base_url=real.gptgod_base_url,
    )
    monkeypatch.setattr(config, "_settings", test_settings)

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


def test_live_chat_stream(live_client):
    with live_client.stream(
        "POST", "/api/chat", json={"question": "NDVI 的计算公式是什么?"}
    ) as response:
        body = "".join(response.iter_text())
    assert response.status_code == 200
    assert "event: done" in body
    assert "event: delta" in body or "event: error" in body
