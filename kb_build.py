from pathlib import Path

from agno.knowledge import Knowledge
from agno.knowledge.embedder.fastembed import FastEmbedEmbedder
from agno.vectordb.lancedb import LanceDb, SearchType

PROJECT_DIR = Path(__file__).resolve().parent
KNOWLEDGE_DIR = PROJECT_DIR / "knowledge"
LANCEDB_DIR = PROJECT_DIR / "data" / "lancedb"
TABLE_NAME = "rs_knowledge"


def create_vector_db() -> LanceDb:
    return LanceDb(
        uri=str(LANCEDB_DIR),
        table_name=TABLE_NAME,
        embedder=FastEmbedEmbedder(id="BAAI/bge-small-zh-v1.5", dimensions=512),
        search_type=SearchType.vector,
    )


def create_knowledge() -> Knowledge:
    return Knowledge(name="遥感知识库", vector_db=create_vector_db(), max_results=5)


def rebuild() -> None:
    vector_db = create_vector_db()
    if vector_db.exists():
        vector_db.delete()
        print("已清空旧向量库")
    knowledge = Knowledge(name="遥感知识库", vector_db=vector_db, max_results=5)
    for file_path in sorted(KNOWLEDGE_DIR.iterdir()):
        if file_path.is_file():
            knowledge.insert(path=str(file_path))
            print(f"已入库: {file_path.name}")
    print("知识库构建完成")


if __name__ == "__main__":
    rebuild()
