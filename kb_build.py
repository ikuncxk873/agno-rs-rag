from pathlib import Path

import lancedb
from agno.knowledge import Knowledge
from agno.knowledge.embedder.fastembed import FastEmbedEmbedder
from agno.vectordb.lancedb import LanceDb, SearchType

PROJECT_DIR = Path(__file__).resolve().parent
KNOWLEDGE_DIR = PROJECT_DIR / "knowledge"
LANCEDB_DIR = PROJECT_DIR / "data" / "lancedb"
TABLE_NAME = "rs_knowledge"
UPLOAD_EXTS = (".txt", ".md", ".pdf")


def create_vector_db() -> LanceDb:
    return LanceDb(
        uri=str(LANCEDB_DIR),
        table_name=TABLE_NAME,
        embedder=FastEmbedEmbedder(id="BAAI/bge-small-zh-v1.5", dimensions=512),
        search_type=SearchType.vector,
    )


def _reset_vector_db() -> None:
    # agno 2.8.7 的 LanceDb.delete() 是空实现(return False),旧向量永不清理
    # 用 lancedb 原生 drop_table 确保 rebuild 前清空
    db = lancedb.connect(str(LANCEDB_DIR))
    if TABLE_NAME in db.table_names():
        db.drop_table(TABLE_NAME)


def create_knowledge() -> Knowledge:
    return Knowledge(name="遥感知识库", vector_db=create_vector_db(), max_results=5)


def rebuild() -> int:
    _reset_vector_db()
    vector_db = create_vector_db()
    if vector_db.exists():
        print("已清空旧向量库")
    knowledge = Knowledge(name="遥感知识库", vector_db=vector_db, max_results=5)
    files = sorted(
        p for p in KNOWLEDGE_DIR.rglob("*")
        if p.is_file() and p.suffix.lower() in UPLOAD_EXTS
    )
    if not files:
        raise RuntimeError("knowledge 目录为空或不存在，知识库为空")
    ok = 0
    failed: list[tuple[str, str]] = []
    for file_path in files:
        try:
            knowledge.insert(path=str(file_path))
            ok += 1
            print(f"已入库: {file_path.name}")
        except Exception as exc:
            failed.append((file_path.name, str(exc)))
            print(f"入库失败: {file_path.name}: {exc}")
    if failed:
        names = ", ".join(name for name, _ in failed)
        raise RuntimeError(f"入库失败 {len(failed)} 个（成功 {ok} 个）: {names}")
    print(f"知识库构建完成,共 {ok} 个文档")
    return ok


if __name__ == "__main__":
    rebuild()
