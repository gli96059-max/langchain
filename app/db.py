import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB_DIR = Path(__file__).resolve().parent.parent / "resources"
DB_PATH = DB_DIR / "sessions.db"


def get_connection():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL DEFAULT '新对话',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            image_url TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS favorites (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            recipe_data TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS dietary_profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            allergies TEXT NOT NULL DEFAULT '',
            restrictions TEXT NOT NULL DEFAULT '',
            preferences TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS recipes (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            name TEXT NOT NULL,
            recipe_data TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );
    """)
    conn.commit()
    conn.close()


def create_session(title: str = "新对话") -> dict:
    conn = get_connection()
    sid = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (sid, title, now, now),
    )
    conn.commit()
    session = conn.execute("SELECT * FROM sessions WHERE id = ?", (sid,)).fetchone()
    conn.close()
    return dict(session)


def list_sessions() -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM sessions ORDER BY updated_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_session(session_id: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_session_title(session_id: str, title: str):
    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
        (title, now, session_id),
    )
    conn.commit()
    conn.close()


def touch_session(session_id: str):
    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE sessions SET updated_at = ? WHERE id = ?",
        (now, session_id),
    )
    conn.commit()
    conn.close()


def delete_session(session_id: str):
    conn = get_connection()
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()


def add_message(session_id: str, role: str, content: str, image_url: str | None = None) -> dict:
    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "INSERT INTO messages (session_id, role, content, image_url, created_at) VALUES (?, ?, ?, ?, ?)",
        (session_id, role, content, image_url, now),
    )
    conn.commit()
    msg = conn.execute(
        "SELECT * FROM messages WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    conn.close()
    return dict(msg)


def get_messages(session_id: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM messages WHERE session_id = ? ORDER BY id ASC",
        (session_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Recipes (library) ────────────────────────────────────────────────

def save_recipe(session_id: str, recipe_data: dict) -> dict:
    conn = get_connection()
    rid = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()
    name = recipe_data.get("name", "")
    conn.execute(
        "INSERT INTO recipes (id, session_id, name, recipe_data, created_at) VALUES (?, ?, ?, ?, ?)",
        (rid, session_id, name, json.dumps(recipe_data, ensure_ascii=False), now),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM recipes WHERE id = ?", (rid,)).fetchone()
    conn.close()
    return dict(row)


def list_all_recipes() -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM recipes ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["recipe_data"] = json.loads(d["recipe_data"])
        result.append(d)
    return result


# ── Dietary Profile ──────────────────────────────────────────────────

def get_dietary_profile() -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM dietary_profile WHERE id = 1").fetchone()
    conn.close()
    return dict(row) if row else None


def upsert_dietary_profile(allergies: str, restrictions: str, preferences: str) -> dict:
    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()
    existing = conn.execute("SELECT * FROM dietary_profile WHERE id = 1").fetchone()
    if existing:
        conn.execute(
            "UPDATE dietary_profile SET allergies = ?, restrictions = ?, preferences = ?, updated_at = ? WHERE id = 1",
            (allergies, restrictions, preferences, now),
        )
    else:
        conn.execute(
            "INSERT INTO dietary_profile (id, allergies, restrictions, preferences, created_at, updated_at) VALUES (1, ?, ?, ?, ?, ?)",
            (allergies, restrictions, preferences, now, now),
        )
    conn.commit()
    row = conn.execute("SELECT * FROM dietary_profile WHERE id = 1").fetchone()
    conn.close()
    return dict(row)


# ── Favorites ─────────────────────────────────────────────────────────

def add_favorite(name: str, recipe_data: dict) -> dict:
    conn = get_connection()
    fid = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO favorites (id, name, recipe_data, created_at) VALUES (?, ?, ?, ?)",
        (fid, name, json.dumps(recipe_data, ensure_ascii=False), now),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM favorites WHERE id = ?", (fid,)).fetchone()
    conn.close()
    return dict(row)


def remove_favorite(favorite_id: str):
    conn = get_connection()
    conn.execute("DELETE FROM favorites WHERE id = ?", (favorite_id,))
    conn.commit()
    conn.close()


def list_favorites() -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM favorites ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["recipe_data"] = json.loads(d["recipe_data"])
        result.append(d)
    return result


init_db()
