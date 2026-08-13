import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent_core import create_agent
from app.auth import require_token
from app.config import get_settings
from app.db import add_message, create_session, get_session, touch_session
from app.routes.docs import rebuilding
from app.streaming import encode_sse, stream_answer

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    question: str


@router.post("/api/chat")
async def chat(body: ChatRequest, _=Depends(require_token)) -> StreamingResponse:
    settings = get_settings()
    question = body.question.strip()
    if not question:
        raise HTTPException(400, detail="问题不能为空")
    if len(question) > settings.max_input_chars:
        raise HTTPException(400, detail=f"问题过长,最多 {settings.max_input_chars} 字符")
    if not settings.resolved_api_key:
        raise HTTPException(503, detail="服务端未配置 API Key,请在 .env 中设置后重启")
    if rebuilding:
        raise HTTPException(503, detail="知识库正在重建,请稍后重试")
    if body.session_id and not get_session(settings.sqlite_path, body.session_id):
        raise HTTPException(404, detail="会话不存在")

    agent = create_agent()

    async def event_stream():
        session_id = body.session_id or create_session(settings.sqlite_path, title=question[:30])
        add_message(settings.sqlite_path, session_id, "user", question, None, settings.resolved_model)
        parts, sources = [], []
        async for event in stream_answer(agent, question):
            if event["type"] == "delta":
                parts.append(event["text"])
            elif event["type"] == "sources":
                sources = event["names"]
            yield encode_sse(event["type"], event)
        if parts:
            add_message(
                settings.sqlite_path,
                session_id,
                "assistant",
                "".join(parts),
                json.dumps(sources, ensure_ascii=False),
                settings.resolved_model,
            )
        touch_session(settings.sqlite_path, session_id)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
