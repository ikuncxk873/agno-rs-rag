from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import db
from app.auth import require_token
from app.config import get_settings

router = APIRouter()


class CreateSessionRequest(BaseModel):
    title: Optional[str] = "新会话"


@router.get("/api/sessions")
async def list_sessions(_=Depends(require_token)):
    return db.list_sessions(get_settings().sqlite_path)


@router.post("/api/sessions")
async def create_session(body: CreateSessionRequest, _=Depends(require_token)):
    title = body.title or "新会话"
    return {"id": db.create_session(get_settings().sqlite_path, title=title), "title": title}


@router.get("/api/sessions/{session_id}/messages")
async def get_messages(session_id: str, _=Depends(require_token)):
    if not db.get_session(get_settings().sqlite_path, session_id):
        raise HTTPException(404, detail="会话不存在")
    return db.list_messages(get_settings().sqlite_path, session_id)


@router.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str, _=Depends(require_token)):
    if not db.delete_session(get_settings().sqlite_path, session_id):
        raise HTTPException(404, detail="会话不存在")
    return {"deleted": True}
