#!/usr/bin/env python3
"""
Safety-net cleanup for orphaned R2 files.

Finds DONE jobs older than 20 minutes that still have output_url set
and deletes the files from R2.  Run this as a daily cron as a last
line of defence — the primary mechanism is the 15-minute Celery task.

Usage:
    docker compose exec worker python worker/scripts/clear_stale_jobs.py

Cron example (run once per hour):
    0 * * * * docker exec zenvort-worker python worker/scripts/clear_stale_jobs.py
"""

import sys
import os
import logging
from datetime import datetime, timedelta, timezone

# Ensure /app is on the path so we can import worker modules
sys.path.insert(0, "/app")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from worker.config import get_settings
from worker.storage import delete_file
from api.models import Job

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("cleanup")


def main() -> None:
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL_SYNC, pool_pre_ping=True)
    Session = sessionmaker(engine)

    # 20-minute cutoff — jobs whose 15-minute output deletion should have fired
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=20)

    with Session() as db:
        stale = (
            db.query(Job)
            .filter(
                Job.status == "DONE",
                Job.updated_at < cutoff,
                Job.output_url.isnot(None),
            )
            .all()
        )

    if not stale:
        logger.info("No orphaned output files found.")
        return

    logger.info(f"Found {len(stale)} orphaned output file(s). Cleaning up...")

    deleted = 0
    for job in stale:
        try:
            delete_file(job.output_url)
            logger.info(f"[cleanup] Deleted orphaned output for job {job.id}: {job.output_url}")
            deleted += 1
        except Exception as e:
            logger.warning(f"[cleanup] Could not delete {job.output_url}: {e}")

    logger.info(f"Cleanup complete. Deleted {deleted}/{len(stale)} file(s).")


if __name__ == "__main__":
    main()
