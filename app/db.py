import sqlite3
import uuid
from pathlib import Path
from typing import Optional

_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;
CREATE TABLE IF NOT EXISTS sessions (
    id         TEXT PRIMARY KEY,
    title      TEXT NOT NULL DEFAULT '新会话',
    user_id    TEXT NOT NULL DEFAULT 'default',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role       TEXT NOT NULL CHECK (role IN ('user','assistant')),
    content    TEXT NOT NULL,
    sources    TEXT,
    model      TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id);
"""


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = _connect(path)
    conn.executescript(_SCHEMA)
    conn.close()


def create_session(path: Path, title: str = "新会话") -> str:
    session_id = uuid.uuid4().hex
    conn = _connect(path)
    conn.execute("INSERT INTO sessions (id, title) VALUES (?, ?)", (session_id, title))
    conn.commit()
    conn.close()
    return session_id


def get_session(path: Path, session_id: str) -> Optional[dict]:
    conn = _connect(path)
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_sessions(path: Path) -> list[dict]:
    conn = _connect(path)
    rows = conn.execute("SELECT * FROM sessions ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_session(path: Path, session_id: str) -> bool:
    conn = _connect(path)
    cursor = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def list_messages(path: Path, session_id: str) -> list[dict]:
    conn = _connect(path)
    rows = conn.execute(
        "SELECT * FROM messages WHERE session_id = ? ORDER BY id", (session_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def add_message(path: Path, session_id: str, role: str, content: str, sources: Optional[str], model: Optional[str]) -> None:
    conn = _connect(path)
    conn.execute(
        "INSERT INTO messages (session_id, role, content, sources, model) VALUES (?, ?, ?, ?, ?)",
        (session_id, role, content, sources, model),
    )
    conn.commit()
    conn.close()


def touch_session(path: Path, session_id: str) -> None:
    conn = _connect(path)
    conn.execute("UPDATE sessions SET updated_at = datetime('now') WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()
