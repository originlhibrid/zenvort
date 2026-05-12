import os
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db import init_db, reset_daily_counts
from app.routers import convert, pdf, ocr, image, media, jobs, admin


settings = get_settings()
logger = logging.getLogger("zenvort.api")


async def daily_reset_loop():
    while True:
        now = datetime.now(timezone.utc)
        next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        wait = (next_midnight - now).total_seconds()
        logger.info(f"Daily reset scheduled in {wait:.0f}s (at {next_midnight.isoformat()})")
        await asyncio.sleep(wait)
        try:
            await reset_daily_counts()
            logger.info("Daily request counts reset")
        except Exception:
            logger.exception("Failed to reset daily counts")


async def periodic_cleanup_loop():
    """
    Background task to periodically clean up orphaned files.
    
    Runs every 30 minutes to catch:
    - Files from crashed API instances (that missed startup cleanup)
    - Files from workers that crashed before cleanup
    - Any race conditions in the cleanup logic
    """
    cleanup_interval = 1800  # 30 minutes
    
    while True:
        await asyncio.sleep(cleanup_interval)
        
        try:
            loop = asyncio.get_running_loop()
            cleaned = await loop.run_in_executor(None, cleanup_orphaned_files)
            if cleaned > 0:
                logger.info(f"Periodic cleanup removed {cleaned} orphaned files")
        except Exception:
            logger.exception("Periodic orphan cleanup failed (non-critical)")


async def periodic_r2_cleanup_loop():
    """
    Background task to clean up old files in R2 storage.
    
    Runs daily to clean:
    - Orphaned input files (uploaded but never processed) older than 24 hours
    - Output files older than 30 days
    
    This handles the case where:
    - Input files were uploaded but job was never dispatched
    - Output files that are no longer needed
    """
    cleanup_interval = 86400  # 24 hours
    
    while True:
        await asyncio.sleep(cleanup_interval)
        
        try:
            from app.storage_cleanup import cleanup_all
            
            logger.info("Starting daily R2 storage cleanup")
            results = cleanup_all(
                retention_days=30,  # Keep outputs for 30 days
                max_age_hours=24,   # Orphaned inputs after 24 hours
            )
            
            # Detailed logging for monitoring
            inputs_deleted = results["orphaned_inputs"]["deleted_count"]
            inputs_size = results["orphaned_inputs"]["deleted_size_bytes"]
            outputs_deleted = results["old_outputs"]["deleted_count"]
            outputs_size = results["old_outputs"]["deleted_size_bytes"]
            
            if inputs_deleted > 0 or outputs_deleted > 0:
                logger.info(
                    f"R2 cleanup: {inputs_deleted} orphaned inputs "
                    f"({inputs_size / 1024 / 1024:.2f} MB), "
                    f"{outputs_deleted} old outputs "
                    f"({outputs_size / 1024 / 1024:.2f} MB) removed"
                )
            else:
                logger.info("R2 cleanup: nothing to clean")
                
        except Exception:
            logger.exception("Periodic R2 cleanup failed (non-critical)")


def cleanup_orphaned_files() -> int:
    """
    Startup cleanup for orphaned temp files.
    
    Handles the edge case where:
    - API server crashes after saving input to /tmp/zenvort/{job_id}/
    - But before dispatching the Celery task
    - Result: orphaned files that workers will never claim
    
    Deletes anything older than 1 hour.
    Never raises - failures are logged but don't stop startup.
    
    Returns:
        Number of items cleaned up
    """
    import shutil
    
    temp_dir = Path(settings.TEMP_DIR)
    if not temp_dir.exists():
        logger.debug("Temp dir does not exist, skipping cleanup")
        return 0
    
    # Age threshold: files older than this are considered orphaned
    max_age = timedelta(hours=1)
    cutoff = datetime.now() - max_age
    
    cleaned = 0
    failed = 0
    
    try:
        for item in temp_dir.iterdir():
            try:
                # Re-check existence (handles race with concurrent cleanup)
                if not item.exists():
                    continue
                    
                # Get modification time
                mtime = datetime.fromtimestamp(item.stat().st_mtime)
                
                if mtime < cutoff:
                    if item.is_dir():
                        shutil.rmtree(item, ignore_errors=True)
                        logger.info(f"Cleaned orphaned directory: {item.name}")
                    else:
                        item.unlink(missing_ok=True)  # Handle race condition
                        logger.info(f"Cleaned orphaned file: {item.name}")
                    cleaned += 1
                else:
                    logger.debug(f"Skipping recent item (age OK): {item.name}")
                    
            except FileNotFoundError:
                # Item was deleted by another process - not an error
                continue
            except Exception as e:
                logger.warning(f"Failed to cleanup {item}: {e}")
                failed += 1
                
    except Exception as e:
        # Directory scan failed - not critical, just log it
        logger.error(f"Orphaned file scan failed: {e}")
        return 0
    
    if cleaned > 0:
        logger.info(f"Orphaned file cleanup complete: {cleaned} items removed, {failed} failures")
    
    return cleaned


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.ADMIN_SECRET:
        import warnings
        warnings.warn("ADMIN_SECRET is not set. All admin endpoints are disabled.", stacklevel=2)
    
    os.makedirs(settings.TEMP_DIR, exist_ok=True)
    
    # Clean up any orphaned files from crashed/restarted instances
    # Run in executor to avoid blocking startup if directory is large
    loop = asyncio.get_running_loop()
    try:
        cleaned = await loop.run_in_executor(None, cleanup_orphaned_files)
        if cleaned:
            logger.info(f"Startup cleanup removed {cleaned} orphaned files")
    except Exception:
        logger.exception("Startup orphan cleanup failed (non-critical)")
    
    await init_db()
    
    # Start background tasks
    reset_task = asyncio.create_task(daily_reset_loop())
    local_cleanup_task = asyncio.create_task(periodic_cleanup_loop())
    r2_cleanup_task = asyncio.create_task(periodic_r2_cleanup_loop())
    
    logger.info("Zenvort API started")
    yield
    
    # Cleanup on shutdown
    reset_task.cancel()
    local_cleanup_task.cancel()
    r2_cleanup_task.cancel()


app = FastAPI(title="Zenvort API", version="2.0.0", lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(exc)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "code": "INTERNAL_ERROR"},
    )


app.include_router(convert.router)
app.include_router(pdf.router)
app.include_router(ocr.router)
app.include_router(image.router)
app.include_router(media.router)
app.include_router(jobs.router)
app.include_router(admin.router)


@app.get("/v1/health")
async def health():
    redis_status = "ok"
    storage_status = "ok"
    worker_status = "ok"

    try:
        from app.worker import celery_app
        celery_app.control.inspect().active()
    except Exception:
        worker_status = "error"

    try:
        import redis
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
    except Exception:
        redis_status = "error"

    try:
        from app.storage import get_s3_client
        client = get_s3_client()
        client.head_bucket(Bucket=settings.R2_BUCKET_NAME)
    except Exception:
        storage_status = "error"

    return {
        "status": "ok",
        "redis": redis_status,
        "storage": storage_status,
        "worker": worker_status,
    }
