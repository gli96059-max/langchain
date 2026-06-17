import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

_RESOURCE_DIR = Path(__file__).resolve().parent.parent / "resources"


def _user_db_path(user_id: str) -> Path:
    return _RESOURCE_DIR / f"user_{user_id}.db"


def get_connection(user_id: str):
    _RESOURCE_DIR.mkdir(parents=True, exist_ok=True)
    path = _user_db_path(user_id)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_user_db(user_id: str):
    conn = get_connection(user_id)
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

        CREATE TABLE IF NOT EXISTS dietary_profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            allergies TEXT NOT NULL DEFAULT '',
            restrictions TEXT NOT NULL DEFAULT '',
            preferences TEXT NOT NULL DEFAULT '',
            difficulty_preference TEXT NOT NULL DEFAULT '',
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

        CREATE TABLE IF NOT EXISTS shopping_lists (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            session_id TEXT DEFAULT '',
            items TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
    """)
    conn.commit()
    # Migration for existing databases
    try:
        conn.execute("ALTER TABLE dietary_profile ADD COLUMN difficulty_preference TEXT NOT NULL DEFAULT ''")
        conn.commit()
    except Exception:
        pass
    conn.close()


# ── Sessions ──────────────────────────────────────────────────────────

def create_session(user_id: str, title: str = "新对话") -> dict:
    conn = get_connection(user_id)
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


def list_sessions(user_id: str) -> list[dict]:
    conn = get_connection(user_id)
    rows = conn.execute("""
        SELECT s.*, IFNULL(m.cnt, 0) as msg_count
        FROM sessions s
        LEFT JOIN (SELECT session_id, COUNT(*) as cnt FROM messages GROUP BY session_id) m
        ON m.session_id = s.id
        ORDER BY s.updated_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_session(user_id: str, session_id: str) -> dict | None:
    conn = get_connection(user_id)
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_session_title(user_id: str, session_id: str, title: str):
    conn = get_connection(user_id)
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
        (title, now, session_id),
    )
    conn.commit()
    conn.close()


def touch_session(user_id: str, session_id: str):
    conn = get_connection(user_id)
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE sessions SET updated_at = ? WHERE id = ?",
        (now, session_id),
    )
    conn.commit()
    conn.close()


def delete_session(user_id: str, session_id: str):
    conn = get_connection(user_id)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()


def batch_delete_sessions(user_id: str, ids: list[str]):
    conn = get_connection(user_id)
    conn.execute("PRAGMA foreign_keys = ON")
    placeholders = ",".join("?" for _ in ids)
    conn.execute(f"DELETE FROM sessions WHERE id IN ({placeholders})", ids)
    conn.commit()
    conn.close()


# ── Messages ──────────────────────────────────────────────────────────

def add_message(user_id: str, session_id: str, role: str, content: str, image_url: str | None = None) -> dict:
    conn = get_connection(user_id)
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


def get_messages(user_id: str, session_id: str) -> list[dict]:
    conn = get_connection(user_id)
    rows = conn.execute(
        "SELECT * FROM messages WHERE session_id = ? ORDER BY id ASC",
        (session_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Recipes (library) ────────────────────────────────────────────────

def save_recipe(user_id: str, session_id: str, recipe_data: dict) -> dict:
    conn = get_connection(user_id)
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


def list_all_recipes(
    user_id: str,
    search_text: str | None = None,
    difficulty: str | None = None,
    ingredient: str | None = None,
    cuisine_type: str | None = None,
    taste: str | None = None,
) -> list[dict]:
    conn = get_connection(user_id)
    rows = conn.execute(
        "SELECT * FROM recipes ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["recipe_data"] = json.loads(d["recipe_data"])
        result.append(d)

    filtered = []
    for r in result:
        data = r["recipe_data"]
        ok = True

        if search_text:
            st = search_text.lower()
            name = (data.get("name") or "").lower()
            reason = (data.get("reason") or "").lower()
            ings = " ".join(i.lower() for i in (data.get("ingredients") or []))
            if st not in name and st not in reason and st not in ings:
                ok = False

        if difficulty and data.get("difficulty") != difficulty:
            ok = False

        if ingredient:
            ing_lower = ingredient.lower()
            ings = [i.lower() for i in (data.get("ingredients") or [])]
            if not any(ing_lower in i for i in ings):
                ok = False

        if cuisine_type:
            ct = data.get("cuisine_type") or ""
            if ct.lower() != cuisine_type.lower():
                ok = False

        if taste:
            ta = data.get("taste") or ""
            if ta.lower() != taste.lower():
                ok = False

        if ok:
            filtered.append(r)

    return filtered


def delete_recipe(user_id: str, recipe_id: str) -> bool:
    conn = get_connection(user_id)
    cursor = conn.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def batch_delete_recipes(user_id: str, ids: list[str]):
    conn = get_connection(user_id)
    placeholders = ",".join("?" for _ in ids)
    conn.execute(f"DELETE FROM recipes WHERE id IN ({placeholders})", ids)
    conn.commit()
    conn.close()


# ── Dietary Profile ──────────────────────────────────────────────────

def get_dietary_profile(user_id: str) -> dict | None:
    conn = get_connection(user_id)
    row = conn.execute("SELECT * FROM dietary_profile WHERE id = 1").fetchone()
    conn.close()
    return dict(row) if row else None


def upsert_dietary_profile(user_id: str, allergies: str, restrictions: str, preferences: str, difficulty_preference: str = "") -> dict:
    conn = get_connection(user_id)
    now = datetime.now(timezone.utc).isoformat()
    existing = conn.execute("SELECT * FROM dietary_profile WHERE id = 1").fetchone()
    if existing:
        conn.execute(
            "UPDATE dietary_profile SET allergies = ?, restrictions = ?, preferences = ?, difficulty_preference = ?, updated_at = ? WHERE id = 1",
            (allergies, restrictions, preferences, difficulty_preference, now),
        )
    else:
        conn.execute(
            "INSERT INTO dietary_profile (id, allergies, restrictions, preferences, difficulty_preference, created_at, updated_at) VALUES (1, ?, ?, ?, ?, ?, ?)",
            (allergies, restrictions, preferences, difficulty_preference, now, now),
        )
    conn.commit()
    row = conn.execute("SELECT * FROM dietary_profile WHERE id = 1").fetchone()
    conn.close()
    return dict(row)


# ── Shopping Lists ───────────────────────────────────────────────────

def save_shopping_list(user_id: str, name: str, session_id: str, items: list[dict]) -> dict:
    conn = get_connection(user_id)
    sid = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO shopping_lists (id, name, session_id, items, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (sid, name, session_id or "", json.dumps(items, ensure_ascii=False), now, now),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM shopping_lists WHERE id = ?", (sid,)).fetchone()
    conn.close()
    return _parse_shopping_list(row)


def list_shopping_lists(user_id: str) -> list[dict]:
    conn = get_connection(user_id)
    rows = conn.execute("SELECT * FROM shopping_lists ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [_parse_shopping_list(r) for r in rows]


def get_shopping_list(user_id: str, list_id: str) -> dict | None:
    conn = get_connection(user_id)
    row = conn.execute("SELECT * FROM shopping_lists WHERE id = ?", (list_id,)).fetchone()
    conn.close()
    return _parse_shopping_list(row) if row else None


def update_shopping_list_items(user_id: str, list_id: str, items: list[dict]) -> dict | None:
    conn = get_connection(user_id)
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE shopping_lists SET items = ?, updated_at = ? WHERE id = ?",
        (json.dumps(items, ensure_ascii=False), now, list_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM shopping_lists WHERE id = ?", (list_id,)).fetchone()
    conn.close()
    return _parse_shopping_list(row) if row else None


def delete_shopping_list(user_id: str, list_id: str):
    conn = get_connection(user_id)
    conn.execute("DELETE FROM shopping_lists WHERE id = ?", (list_id,))
    conn.commit()
    conn.close()


def _parse_shopping_list(row) -> dict:
    d = dict(row)
    d["items"] = json.loads(d["items"])
    return d
