import os
import aiosqlite
import asyncio
import logging
from datetime import datetime, timezone
from typing import AsyncIterator

DB_PATH = os.getenv("DB_PATH", "/data/zenvort.db")

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """Create all tables if they don't exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Enable WAL mode for better concurrent access
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA busy_timeout=30000")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          TEXT PRIMARY KEY,
                email       TEXT UNIQUE NOT NULL,
                password    TEXT,
                api_key     TEXT UNIQUE NOT NULL,
                api_key_hash TEXT UNIQUE NOT NULL,
                role        TEXT DEFAULT 'user',
                webhook_url TEXT,
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id             TEXT PRIMARY KEY,
                user_id        TEXT,
                status         TEXT DEFAULT 'pending'
                               CHECK(status IN ('pending','processing','done','failed')),
                input_url      TEXT,
                output_url     TEXT,
                input_format   TEXT,
                output_format  TEXT,
                error          TEXT,
                converter_used TEXT,
                created_at     TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        await db.commit()
        logger.info("✅ Database tables initialised")


async def get_db() -> AsyncIterator[aiosqlite.Connection]:
    """Yield a connection per request, auto-closed afterwards."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        try:
            yield db
        finally:
            await db.close()


def row_to_dict(row: aiosqlite.Row) -> dict:
    """Convert aiosqlite.Row to plain dict."""
    return dict(row)
