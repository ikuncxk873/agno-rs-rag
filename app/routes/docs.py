from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.auth import require_token
from app.config import get_settings
from kb_build import rebuild

router = APIRouter()

rebuilding = False


async def _rebuild() -> int:
    global rebuilding
    if rebuilding:
        raise HTTPException(409, detail="知识库正在重建,请稍后再试")
    rebuilding = True
    try:
        return await run_in_threadpool(rebuild)
    finally:
        rebuilding = False


@router.get("/api/documents")
async def list_documents(_=Depends(require_token)):
    settings = get_settings()
    files = []
    if settings.knowledge_dir.exists():
        for p in settings.knowledge_dir.rglob("*"):
            if p.is_file():
                stat = p.stat()
                files.append({"name": p.name, "size": stat.st_size, "modified": stat.st_mtime})
    return {"files": sorted(files, key=lambda f: f["name"])}


@router.post("/api/documents")
async def upload_document(file: UploadFile, _=Depends(require_token)):
    settings = get_settings()
    name = Path(file.filename or "").name
    if not name or Path(name).suffix.lower() not in settings.upload_exts:
        raise HTTPException(400, detail=f"仅支持 {'/'.join(settings.upload_exts)} 文件")
    settings.knowledge_dir.mkdir(parents=True, exist_ok=True)
    (settings.knowledge_dir / name).write_bytes(await file.read())
    inserted = await _rebuild()
    return {"saved": name, "inserted": inserted}


@router.post("/api/rebuild")
async def rebuild_kb(_=Depends(require_token)):
    inserted = await _rebuild()
    return {"inserted": inserted}
