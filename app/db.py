import secrets
import aiosqlite
from datetime import datetime, timezone

from app.config import get_settings


async def init_db() -> None:
    db_path = get_settings().DB_PATH
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT DEFAULT 'queued',
                endpoint TEXT,
                result_url TEXT,
                filename TEXT,
                error TEXT,
                webhook_url TEXT,
                created_at TEXT,
                updated_at TEXT
            )"""
        )
        await db.execute(
            """CREATE TABLE IF NOT EXISTS api_keys (
                key_id TEXT PRIMARY KEY,
                key_hash TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                tier TEXT DEFAULT 'free',
                is_active INTEGER DEFAULT 1,
                requests_today INTEGER DEFAULT 0,
                requests_total INTEGER DEFAULT 0,
                last_used_at TEXT,
                created_at TEXT
            )"""
        )
        await db.execute(
            """CREATE TABLE IF NOT EXISTS usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_id TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                job_id TEXT,
                file_size_bytes INTEGER,
                status_code INTEGER,
                created_at TEXT
            )"""
        )
        await db.commit()


async def create_job(job_id: str, endpoint: str, webhook_url: str | None = None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    db_path = get_settings().DB_PATH
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT INTO jobs (job_id, status, endpoint, webhook_url, created_at, updated_at)
               VALUES (?, 'queued', ?, ?, ?, ?)""",
            (job_id, endpoint, webhook_url, now, now),
        )
        await db.commit()


async def update_job(
    job_id: str,
    status: str,
    result_url: str | None = None,
    filename: str | None = None,
    error: str | None = None,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    db_path = get_settings().DB_PATH
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """UPDATE jobs SET status = ?, result_url = ?, filename = ?, error = ?, updated_at = ?
               WHERE job_id = ?""",
            (status, result_url, filename, error, now, job_id),
        )
        await db.commit()


async def get_job(job_id: str) -> dict | None:
    db_path = get_settings().DB_PATH
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def create_api_key(name: str, tier: str = "free") -> dict:
    import hashlib
    key_id = secrets.token_hex(16)
    raw_key = f"zv_{secrets.token_hex(16)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    db_path = get_settings().DB_PATH
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT INTO api_keys (key_id, key_hash, name, tier, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (key_id, key_hash, name, tier, now),
        )
        await db.commit()
    return {"key_id": key_id, "api_key": raw_key, "name": name, "tier": tier}


async def get_key_by_hash(key_hash: str) -> dict | None:
    db_path = get_settings().DB_PATH
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM api_keys WHERE key_hash = ?", (key_hash,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_key_by_id(key_id: str) -> dict | None:
    db_path = get_settings().DB_PATH
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM api_keys WHERE key_id = ?", (key_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def check_and_increment_usage(
    key_id: str,
    tier: str,
    endpoint: str,
    job_id: str,
    file_size: int,
    status_code: int,
) -> None:
    """
    Atomically checks the daily rate limit AND increments usage counters in one UPDATE.
    Raises HTTPException(429) immediately if the limit has already been reached.
    No race window: the check and increment happen in a single SQL statement.
    """
    import hashlib
    from datetime import datetime, timezone

    limits = {"free": 50, "pro": 500, "enterprise": 10000}
    limit = limits.get(tier, 50)
    now = datetime.now(timezone.utc).isoformat()
    db_path = get_settings().DB_PATH

    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        # Atomic: UPDATE ... WHERE requests_today < :limit
        # rowcount == 1 means the row matched AND was updated → under limit, allowed
        # rowcount == 0 means no row matched the WHERE clause → over limit, denied
        cursor = await db.execute(
            """
            UPDATE api_keys
            SET requests_today = requests_today + 1,
                requests_total = requests_total + 1,
                last_used_at = ?
            WHERE key_id = ?
              AND is_active = 1
              AND requests_today < ?
            """,
            (now, key_id, limit),
        )
        await db.commit()

        if cursor.rowcount == 0:
            # Rate limit already reached — fetch current count for resets_at
            async with aiosqlite.connect(db_path) as db2:
                db2.row_factory = aiosqlite.Row
                async with db2.execute(
                    "SELECT requests_today FROM api_keys WHERE key_id = ?", (key_id,)
                ) as cur:
                    row = await cur.fetchone()
            from datetime import datetime as dt, timedelta, timezone as tz
            next_midnight = (dt.now(tz.utc) + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Daily rate limit exceeded",
                    "code": "RATE_LIMIT_EXCEEDED",
                    "tier": tier,
                    "limit": limit,
                    "resets_at": next_midnight.isoformat(),
                },
            )

        # Under limit — also log the call
        await db.execute(
            """INSERT INTO usage_log (key_id, endpoint, job_id, file_size_bytes, status_code, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (key_id, endpoint, job_id, file_size, status_code, now),
        )
        await db.commit()


async def deactivate_key(key_id: str) -> None:
    db_path = get_settings().DB_PATH
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE api_keys SET is_active = 0 WHERE key_id = ?", (key_id,)
        )
        await db.commit()


async def list_keys() -> list[dict]:
    db_path = get_settings().DB_PATH
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT key_id, name, tier, is_active, requests_today, requests_total, last_used_at, created_at FROM api_keys"
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def reset_daily_counts() -> None:
    db_path = get_settings().DB_PATH
    async with aiosqlite.connect(db_path) as db:
        await db.execute("UPDATE api_keys SET requests_today = 0")
        await db.commit()


async def get_usage_logs(key_id: str, limit: int = 100, offset: int = 0) -> list[dict]:
    db_path = get_settings().DB_PATH
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT * FROM usage_log WHERE key_id = ?
               ORDER BY id DESC LIMIT ? OFFSET ?""",
            (key_id, limit, offset),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]
