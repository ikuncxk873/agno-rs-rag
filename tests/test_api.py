import json
from types import SimpleNamespace

AUTH = {"Authorization": "Bearer test-token"}


class RunContentEvent:
    def __init__(self, content):
        self.content = content


class FakeAgent:
    async def arun(self, question, stream=True, stream_events=True, yield_run_output=True):
        yield RunContentEvent("这是模拟回答")
        yield SimpleNamespace(
            messages=[
                SimpleNamespace(
                    role="tool",
                    tool_name="search_knowledge_base",
                    content='[{"name": "测试文档.txt"}]',
                )
            ]
        )


def test_health(client, settings):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["model"] == settings.deepseek_model


def test_chat_requires_token(client):
    assert client.post("/api/chat", json={"question": "你好"}).status_code == 401
    response = client.post("/api/chat", json={"question": "你好"}, headers={"Authorization": "Bearer wrong"})
    assert response.status_code == 401


def test_chat_empty_question(client):
    response = client.post("/api/chat", json={"question": "   "}, headers=AUTH)
    assert response.status_code == 400


def test_chat_too_long(client, settings):
    response = client.post(
        "/api/chat",
        json={"question": "长" * (settings.max_input_chars + 1)},
        headers=AUTH,
    )
    assert response.status_code == 400


def test_chat_missing_session(client):
    response = client.post(
        "/api/chat",
        json={"session_id": "no-such-session", "question": "你好"},
        headers=AUTH,
    )
    assert response.status_code == 404


def test_chat_stream_and_persist(client, monkeypatch):
    monkeypatch.setattr("app.routes.chat.create_agent", lambda: FakeAgent())
    with client.stream(
        "POST", "/api/chat", json={"question": "测试问题"}, headers=AUTH
    ) as response:
        body = "".join(response.iter_text())
    assert response.status_code == 200
    assert "event: delta" in body
    assert "这是模拟回答" in body
    assert "event: sources" in body
    assert "event: done" in body

    sessions = client.get("/api/sessions", headers=AUTH).json()
    assert len(sessions) == 1
    messages = client.get(f"/api/sessions/{sessions[0]['id']}/messages", headers=AUTH).json()
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[0]["content"] == "测试问题"
    assert messages[1]["content"] == "这是模拟回答"
    assert json.loads(messages[1]["sources"]) == ["测试文档.txt"]


def test_sessions_crud(client):
    created = client.post("/api/sessions", json={"title": "我的会话"}, headers=AUTH).json()
    session_id = created["id"]
    assert created["title"] == "我的会话"

    listed = client.get("/api/sessions", headers=AUTH).json()
    assert any(s["id"] == session_id for s in listed)

    assert client.get(f"/api/sessions/{session_id}/messages", headers=AUTH).status_code == 200
    assert client.delete(f"/api/sessions/{session_id}", headers=AUTH).status_code == 200
    assert client.get(f"/api/sessions/{session_id}/messages", headers=AUTH).status_code == 404
    assert client.delete(f"/api/sessions/{session_id}", headers=AUTH).status_code == 404


def test_documents_list_and_upload_rejected(client):
    listed = client.get("/api/documents", headers=AUTH)
    assert listed.status_code == 200
    assert listed.json() == {"files": []}

    bad = client.post(
        "/api/documents",
        files={"file": ("evil.exe", b"x", "application/octet-stream")},
        headers=AUTH,
    )
    assert bad.status_code == 400
