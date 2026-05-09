#!/usr/bin/env python3
"""
Safety-net cleanup for orphaned R2 files.

Finds DONE jobs older than 20 minutes that still have output_url set
and deletes the files from R2.  Run this as a daily cron as a last
line of defence — the primary mechanism is the 20-minute Celery task.

Usage:
    docker compose exec worker python worker/scripts/clear_stale_jobs.py
"""

import sys
import os
import logging
import sqlite3
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "/app")

from worker.config import get_settings
from worker.storage import delete_file

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("cleanup")


def main() -> None:
    settings = get_settings()
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row

    # 20-minute cutoff
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()

    rows = conn.execute(
        """SELECT id, output_url FROM jobs
           WHERE status = 'done' AND output_url IS NOT NULL AND updated_at < ?""",
        (cutoff,),
    ).fetchall()
    conn.close()

    if not rows:
        logger.info("No orphaned output files found.")
        return

    logger.info(f"Found {len(rows)} orphaned output file(s). Cleaning up...")

    deleted = 0
    for row in rows:
        try:
            delete_file(row["output_url"])
            logger.info(f"[cleanup] Deleted orphaned output for job {row['id']}: {row['output_url']}")
            deleted += 1
        except Exception as e:
            logger.warning(f"[cleanup] Could not delete {row['output_url']}: {e}")

    logger.info(f"Cleanup complete. Deleted {deleted}/{len(rows)} file(s).")


if __name__ == "__main__":
    main()
