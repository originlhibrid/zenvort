import os
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import logging

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.ADMIN_SECRET:
        import warnings
        warnings.warn("ADMIN_SECRET is not set. All admin endpoints are disabled.", stacklevel=2)
    os.makedirs(settings.TEMP_DIR, exist_ok=True)
    await init_db()
    reset_task = asyncio.create_task(daily_reset_loop())
    logger.info("Zenvort API started")
    yield
    reset_task.cancel()


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
