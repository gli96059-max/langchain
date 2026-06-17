"""
PostgreSQL 数据访问层。

核心变化（相对 SQLite 版本）：
- 所有用户共享一个连接池，通过 user_id 列隔离数据
- 所有函数为 async，支持高并发
- 使用 WAL 风格（PostgreSQL 默认 MVCC），读写不互斥
"""

import json
import uuid
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import asyncpg
from passlib.context import CryptContext

_pctx = CryptContext(schemes=["pbkdf2_sha256"])
_pool: asyncpg.Pool | None = None


# ── Pool management ────────────────────────────────────────────────


async def init_pool(dsn: str | None = None):
    """Create the shared asyncpg connection pool (idempotent)."""
    global _pool
    if _pool is not None:
        return
    dsn = dsn or os.getenv("DATABASE_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    _pool = await asyncpg.create_pool(
        dsn,
        min_size=2,
        max_size=20,
        command_timeout=30,
        max_inactive_connection_lifetime=300,
    )


async def close_pool():
    """Close the connection pool (called on shutdown)."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    """Return the initialized pool (synchronous accessor for other modules)."""
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_pool() first.")
    return _pool


# ── Schema ─────────────────────────────────────────────────────────


async def init_db():
    """Create all tables if they don't exist (idempotent)."""
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT NOT NULL,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title TEXT NOT NULL DEFAULT '新对话',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (id, user_id)
            );
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id BIGSERIAL,
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                image_url TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (id)
            );
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_lookup
            ON messages(user_id, session_id, id);
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS dietary_profiles (
                user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                allergies TEXT NOT NULL DEFAULT '',
                restrictions TEXT NOT NULL DEFAULT '',
                preferences TEXT NOT NULL DEFAULT '',
                difficulty_preference TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS recipes (
                id TEXT NOT NULL,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                session_id TEXT NOT NULL,
                name TEXT NOT NULL,
                recipe_data JSONB NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (id, user_id)
            );
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS shopping_lists (
                id TEXT NOT NULL,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                session_id TEXT DEFAULT '',
                items JSONB NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (id, user_id)
            );
        """)


# ── Users (was app/master_db.py) ───────────────────────────────────


async def create_user(username: str, password: str) -> dict | None:
    if not username or len(password) < 6:
        return None
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM users WHERE username = $1", username,
        )
        if row:
            return None
        uid = uuid.uuid4().hex
        pw_hash = _pctx.hash(password)
        await conn.execute(
            "INSERT INTO users (id, username, password_hash) VALUES ($1, $2, $3)",
            uid, username, pw_hash,
        )
        row = await conn.fetchrow(
            "SELECT id, username, created_at FROM users WHERE id = $1", uid,
        )
        return dict(row) if row else None


async def verify_user(username: str, password: str) -> dict | None:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM users WHERE username = $1", username,
        )
        if not row:
            return None
        user = dict(row)
        if not _pctx.verify(password, user["password_hash"]):
            return None
        return {
            "id": user["id"],
            "username": user["username"],
            "created_at": user["created_at"].isoformat() if hasattr(user["created_at"], "isoformat") else str(user["created_at"]),
        }


async def get_user_by_id(user_id: str) -> dict | None:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, username, created_at FROM users WHERE id = $1", user_id,
        )
        return dict(row) if row else None


# ── Sessions ───────────────────────────────────────────────────────


async def create_session(user_id: str, title: str = "新对话") -> dict:
    pool = get_pool()
    sid = uuid.uuid4().hex[:12]
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO sessions (id, user_id, title) VALUES ($1, $2, $3)",
            sid, user_id, title,
        )
        row = await conn.fetchrow(
            "SELECT id, title, created_at, updated_at FROM sessions WHERE id = $1 AND user_id = $2",
            sid, user_id,
        )
        return dict(row)


async def list_sessions(user_id: str) -> list[dict]:
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT s.id, s.title, s.created_at, s.updated_at,
                   COALESCE(m.cnt, 0)::int AS msg_count
            FROM sessions s
            LEFT JOIN (
                SELECT session_id, COUNT(*) AS cnt
                FROM messages
                WHERE user_id = $1
                GROUP BY session_id
            ) m ON m.session_id = s.id
            WHERE s.user_id = $1
            ORDER BY s.updated_at DESC
        """, user_id)
        return [dict(r) for r in rows]


async def get_session(user_id: str, session_id: str) -> dict | None:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, title, created_at, updated_at FROM sessions WHERE id = $1 AND user_id = $2",
            session_id, user_id,
        )
        return dict(row) if row else None


async def update_session_title(user_id: str, session_id: str, title: str):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE sessions SET title = $1, updated_at = NOW() WHERE id = $2 AND user_id = $3",
            title, session_id, user_id,
        )


async def touch_session(user_id: str, session_id: str):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE sessions SET updated_at = NOW() WHERE id = $1 AND user_id = $2",
            session_id, user_id,
        )


async def delete_session(user_id: str, session_id: str):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM messages WHERE session_id = $1 AND user_id = $2",
            session_id, user_id,
        )
        await conn.execute(
            "DELETE FROM sessions WHERE id = $1 AND user_id = $2",
            session_id, user_id,
        )


async def batch_delete_sessions(user_id: str, ids: list[str]):
    if not ids:
        return
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM messages WHERE session_id = ANY($1::text[]) AND user_id = $2",
            ids, user_id,
        )
        await conn.execute(
            "DELETE FROM sessions WHERE id = ANY($1::text[]) AND user_id = $2",
            ids, user_id,
        )


# ── Messages ────────────────────────────────────────────────────────


async def add_message(
    user_id: str, session_id: str, role: str, content: str,
    image_url: str | None = None,
) -> dict:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO messages (session_id, user_id, role, content, image_url) "
            "VALUES ($1, $2, $3, $4, $5) "
            "RETURNING id, session_id, role, content, image_url, created_at",
            session_id, user_id, role, content, image_url,
        )
        return dict(row)


async def get_messages(user_id: str, session_id: str) -> list[dict]:
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, session_id, role, content, image_url, created_at "
            "FROM messages WHERE user_id = $1 AND session_id = $2 ORDER BY id ASC",
            user_id, session_id,
        )
        return [dict(r) for r in rows]


# ── Recipes (library) ──────────────────────────────────────────────


async def save_recipe(user_id: str, session_id: str, recipe_data: dict) -> dict:
    rid = uuid.uuid4().hex[:12]
    name = recipe_data.get("name", "")
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO recipes (id, user_id, session_id, name, recipe_data) "
            "VALUES ($1, $2, $3, $4, $5::jsonb) "
            "RETURNING id, session_id, name, recipe_data, created_at",
            rid, user_id, session_id, name,
            json.dumps(recipe_data, ensure_ascii=False),
        )
        d = dict(row)
        d["recipe_data"] = json.loads(d["recipe_data"])
        return d


async def list_all_recipes(
    user_id: str,
    search_text: str | None = None,
    difficulty: str | None = None,
    ingredient: str | None = None,
    cuisine_type: str | None = None,
    taste: str | None = None,
) -> list[dict]:
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, session_id, name, recipe_data, created_at "
            "FROM recipes WHERE user_id = $1 ORDER BY created_at DESC",
            user_id,
        )

    result = []
    for r in rows:
        d = dict(r)
        d["recipe_data"] = json.loads(d["recipe_data"])
        result.append(d)

    # ── filtering (same logic as SQLite version) ──
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


async def delete_recipe(user_id: str, recipe_id: str) -> bool:
    pool = get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM recipes WHERE id = $1 AND user_id = $2",
            recipe_id, user_id,
        )
        return "DELETE 1" in result


async def batch_delete_recipes(user_id: str, ids: list[str]):
    if not ids:
        return
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM recipes WHERE id = ANY($1::text[]) AND user_id = $2",
            ids, user_id,
        )


# ── Dietary Profile ────────────────────────────────────────────────


async def get_dietary_profile(user_id: str) -> dict | None:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM dietary_profiles WHERE user_id = $1", user_id,
        )
        return dict(row) if row else None


async def upsert_dietary_profile(
    user_id: str, allergies: str, restrictions: str, preferences: str,
    difficulty_preference: str = "",
) -> dict:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO dietary_profiles
                (user_id, allergies, restrictions, preferences, difficulty_preference)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (user_id) DO UPDATE SET
                allergies = EXCLUDED.allergies,
                restrictions = EXCLUDED.restrictions,
                preferences = EXCLUDED.preferences,
                difficulty_preference = EXCLUDED.difficulty_preference,
                updated_at = NOW()
            RETURNING *
        """, user_id, allergies, restrictions, preferences, difficulty_preference)
        return dict(row)


# ── Shopping Lists ─────────────────────────────────────────────────


async def save_shopping_list(
    user_id: str, name: str, session_id: str, items: list[dict],
) -> dict:
    sid = uuid.uuid4().hex[:12]
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO shopping_lists (id, user_id, name, session_id, items) "
            "VALUES ($1, $2, $3, $4, $5::jsonb) RETURNING *",
            sid, user_id, name, session_id,
            json.dumps(items, ensure_ascii=False),
        )
        return _parse_shopping_list(row)


async def list_shopping_lists(user_id: str) -> list[dict]:
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM shopping_lists WHERE user_id = $1 ORDER BY updated_at DESC",
            user_id,
        )
        return [_parse_shopping_list(r) for r in rows]


async def get_shopping_list(user_id: str, list_id: str) -> dict | None:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM shopping_lists WHERE id = $1 AND user_id = $2",
            list_id, user_id,
        )
        return _parse_shopping_list(row) if row else None


async def update_shopping_list_items(
    user_id: str, list_id: str, items: list[dict],
) -> dict | None:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE shopping_lists SET items = $1::jsonb, updated_at = NOW() "
            "WHERE id = $2 AND user_id = $3 RETURNING *",
            json.dumps(items, ensure_ascii=False), list_id, user_id,
        )
        return _parse_shopping_list(row) if row else None


async def delete_shopping_list(user_id: str, list_id: str):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM shopping_lists WHERE id = $1 AND user_id = $2",
            list_id, user_id,
        )


def _parse_shopping_list(row) -> dict:
    d = dict(row)
    d["items"] = json.loads(d["items"])
    return d
