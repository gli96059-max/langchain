import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from passlib.context import CryptContext

_RESOURCE_DIR = Path(__file__).resolve().parent.parent / "resources"
_MASTER_DB = _RESOURCE_DIR / "app.db"

_pctx = CryptContext(schemes=["bcrypt"])


def _get_conn():
    _RESOURCE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_MASTER_DB), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_master_db():
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()


def create_user(username: str, password: str) -> dict | None:
    if not username or len(password) < 6:
        return None
    conn = _get_conn()
    existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if existing:
        conn.close()
        return None
    uid = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    pw_hash = _pctx.hash(password)
    conn.execute(
        "INSERT INTO users (id, username, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (uid, username, pw_hash, now),
    )
    conn.commit()
    row = conn.execute("SELECT id, username, created_at FROM users WHERE id = ?", (uid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def verify_user(username: str, password: str) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if not row:
        return None
    user = dict(row)
    if not _pctx.verify(password, user["password_hash"]):
        return None
    return {"id": user["id"], "username": user["username"], "created_at": user["created_at"]}


def get_user_by_id(user_id: str) -> dict | None:
    conn = _get_conn()
    row = conn.execute(
        "SELECT id, username, created_at FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None
