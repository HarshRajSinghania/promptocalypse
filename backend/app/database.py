from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import aiosqlite

from app.config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL COLLATE NOCASE,
    current_level INTEGER NOT NULL DEFAULT 1 CHECK(current_level BETWEEN 1 AND 3),
    start_time TEXT NOT NULL,
    completed_at TEXT,
    total_prompts INTEGER NOT NULL DEFAULT 0,
    total_chars INTEGER NOT NULL DEFAULT 0,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    final_score REAL NOT NULL DEFAULT 0.0,
    is_disqualified INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS prompt_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL REFERENCES users(id),
    level INTEGER NOT NULL,
    prompt_text TEXT NOT NULL,
    response_text TEXT NOT NULL,
    char_count INTEGER NOT NULL,
    is_firewall_blocked INTEGER NOT NULL DEFAULT 0,
    is_leak_blocked INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL REFERENCES users(id),
    level INTEGER NOT NULL,
    submitted_key TEXT NOT NULL,
    is_correct INTEGER NOT NULL,
    submitted_at TEXT NOT NULL
);
"""


async def get_db() -> aiosqlite.Connection:
    """
    Return an aiosqlite database connection configured with WAL mode and pragmas.
    """
    settings = get_settings()
    db = await aiosqlite.connect(settings.DB_PATH)
    await db.execute("PRAGMA journal_mode = WAL;")
    await db.execute("PRAGMA synchronous = NORMAL;")
    await db.execute("PRAGMA busy_timeout = 5000;")
    await db.execute("PRAGMA foreign_keys = ON;")
    db.row_factory = aiosqlite.Row
    return db


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[aiosqlite.Connection, None]:
    """
    Context manager that provides an aiosqlite database connection and ensures it is closed.
    """
    db = await get_db()
    try:
        yield db
    finally:
        await db.close()


async def init_db() -> None:
    """
    Initialize SQLite database tables matching the PRD specification.
    """
    db = await get_db()
    try:
        await db.executescript(SCHEMA)
        await db.commit()
    finally:
        await db.close()
