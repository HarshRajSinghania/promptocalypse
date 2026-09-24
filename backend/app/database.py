"""
SQLite database initialization with WAL mode and performance PRAGMAs.

Implements Issue #1: SQLite Schema Initialization with WAL Mode & PRAGMAs.
Reference: docs/TECH-SPEC.md §3 — Database Specification & Indexing Strategy.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import aiosqlite

from app.config import get_settings

# ---------------------------------------------------------------------------
# SQL: Table Definitions
# ---------------------------------------------------------------------------
# Matches TECH-SPEC.md §3 exactly. Uses IF NOT EXISTS so init_db() is
# idempotent and safe to call on every application startup.
# ---------------------------------------------------------------------------

_CREATE_TABLES = """
-- 1. User state and final aggregates
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL COLLATE NOCASE,
    email TEXT NULL COLLATE NOCASE,
    current_level INTEGER NOT NULL DEFAULT 1 CHECK(current_level BETWEEN 1 AND 3),
    start_time TIMESTAMP NOT NULL,
    completed_at TIMESTAMP NULL,
    total_prompts INTEGER NOT NULL DEFAULT 0,
    total_chars INTEGER NOT NULL DEFAULT 0,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    final_score REAL NOT NULL DEFAULT 0.0,
    is_disqualified INTEGER NOT NULL DEFAULT 0
);

-- 2. Audit ledger for prompt submissions
CREATE TABLE IF NOT EXISTS prompt_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    level INTEGER NOT NULL CHECK(level BETWEEN 1 AND 3),
    prompt_text TEXT NOT NULL,
    response_text TEXT NOT NULL,
    char_count INTEGER NOT NULL,
    latency_ms INTEGER NOT NULL DEFAULT 0,
    is_firewall_blocked INTEGER NOT NULL DEFAULT 0,
    is_leak_blocked INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 3. Flag submission transaction history
CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    level INTEGER NOT NULL CHECK(level BETWEEN 1 AND 3),
    submitted_key TEXT NOT NULL,
    is_correct INTEGER NOT NULL,
    submitted_at TIMESTAMP NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
"""

# ---------------------------------------------------------------------------
# SQL: Index Definitions
# ---------------------------------------------------------------------------
# Composite leaderboard index enables the multi-tier tie-breaking ORDER BY
# used by GET /api/leaderboard without a filesort.
# ---------------------------------------------------------------------------

_CREATE_INDEXES = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username
    ON users(username);

CREATE INDEX IF NOT EXISTS idx_users_email
    ON users(email);

CREATE INDEX IF NOT EXISTS idx_leaderboard_rank
    ON users(
        final_score DESC,
        current_level DESC,
        total_prompts ASC,
        total_chars ASC,
        completed_at ASC
    );

CREATE INDEX IF NOT EXISTS idx_prompt_ledger_user
    ON prompt_ledger(user_id, level);

CREATE INDEX IF NOT EXISTS idx_submissions_user
    ON submissions(user_id);
"""

# ---------------------------------------------------------------------------
# PRAGMAs applied on every new connection
# ---------------------------------------------------------------------------
# - WAL:          Non-blocking concurrent readers during write transactions.
# - synchronous:  NORMAL is safe with WAL and avoids fsync on every commit.
# - busy_timeout: Wait up to 5 s for a write-lock instead of failing immediately.
# - cache_size:   -64000 → 64 MB in-memory page cache (negative = KiB).
# - foreign_keys: Enforce FK constraints at runtime (SQLite default is OFF).
# ---------------------------------------------------------------------------

_PRAGMAS = [
    "PRAGMA journal_mode = WAL;",
    "PRAGMA synchronous = NORMAL;",
    "PRAGMA busy_timeout = 5000;",
    "PRAGMA cache_size = -64000;",
    "PRAGMA foreign_keys = ON;",
]


async def _apply_pragmas(db: aiosqlite.Connection) -> None:
    """Apply performance and safety PRAGMAs to the given connection."""
    for pragma in _PRAGMAS:
        await db.execute(pragma)


async def init_db() -> None:
    """
    Initialize the SQLite database: apply PRAGMAs, create tables, and
    build indexes.

    This function is idempotent — safe to call on every application startup.
    It is invoked from the FastAPI ``startup`` event in ``app/main.py``.
    """
    settings = get_settings()
    db = await aiosqlite.connect(settings.DB_PATH)
    try:
        await _apply_pragmas(db)
        await db.executescript(_CREATE_TABLES)

        # Migration: Ensure email column exists if users table was created earlier
        async with db.execute("PRAGMA table_info(users)") as cursor:
            columns = [row[1] for row in await cursor.fetchall()]
            if "email" not in columns:
                await db.execute("ALTER TABLE users ADD COLUMN email TEXT NULL COLLATE NOCASE")

        await db.executescript(_CREATE_INDEXES)
        await db.commit()
    finally:
        await db.close()


async def get_db() -> aiosqlite.Connection:
    """
    Open and return a new aiosqlite connection with PRAGMAs applied.

    Callers are responsible for closing the connection when done.
    Prefer :func:`get_db_context` for automatic cleanup.
    """
    settings = get_settings()
    db = await aiosqlite.connect(settings.DB_PATH)
    await _apply_pragmas(db)
    db.row_factory = aiosqlite.Row
    return db


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[aiosqlite.Connection, None]:
    """
    Async context manager that yields a fully configured database connection
    and ensures it is closed on exit.

    Usage::

        async with get_db_context() as db:
            cursor = await db.execute("SELECT ...")
    """
    db = await get_db()
    try:
        yield db
    finally:
        await db.close()
