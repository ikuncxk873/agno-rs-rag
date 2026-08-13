from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from app.config import PROJECT_DIR, get_settings
from app.db import init_db
from app.routes import chat, docs, sessions
from kb_build import LANCEDB_DIR, rebuild


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    init_db(settings.sqlite_path)
    if not (LANCEDB_DIR / "rs_knowledge.lance").exists():
        await run_in_threadpool(rebuild)
    yield


app = FastAPI(title=get_settings().app_name, lifespan=lifespan)
app.include_router(chat.router)
app.include_router(sessions.router)
app.include_router(docs.router)


@app.get("/api/health")
async def health():
    settings = get_settings()
    knowledge_dir = settings.knowledge_dir
    docs = [p.name for p in knowledge_dir.rglob("*") if p.is_file()] if knowledge_dir.exists() else []
    return {
        "status": "ok",
        "model": settings.deepseek_model,
        "docs_count": len(docs),
        "vector_db_exists": (settings.lancedb_dir / "rs_knowledge.lance").exists(),
    }
app.mount("/", StaticFiles(directory=str(PROJECT_DIR / "static"), html=True), name="static")
