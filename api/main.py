import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.config import get_settings
from api.database import init_db
from api.routes import auth, jobs, user, admin, formats, pdf_jobs, spreadsheet_jobs

settings = get_settings()

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info(
        f"Zenvort API starting | DB: {settings.DB_PATH} | "
        f"R2 bucket: {settings.R2_BUCKET_NAME} | "
        f"GOTENBERG_URL: {settings.GOTENBERG_URL}"
    )
    yield


app = FastAPI(title="Zenvort API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten to your domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter


@app.middleware("http")
async def internal_only(request: Request, call_next):
    """Require X-Internal-Secret only for admin/storage paths.
    User-facing paths (/user/me, /jobs etc.) are open to Bearer auth."""
    _internal_paths = {"/admin", "/storage"}
    if any(request.url.path.startswith(p) for p in _internal_paths):
        secret = request.headers.get("X-Internal-Secret", "")
        expected = settings.INTERNAL_SECRET

        if secret != expected:
            return JSONResponse(
                status_code=403,
                content={"error": "Forbidden"},
            )

    return await call_next(request)


@app.get("/health")
async def health():
    return {
        "ok": True,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


app.include_router(auth, prefix="/auth", tags=["auth"])
app.include_router(jobs, prefix="/jobs", tags=["jobs"])
app.include_router(user, prefix="/user", tags=["user"])
app.include_router(formats, prefix="/formats", tags=["formats"])
app.include_router(pdf_jobs, prefix="/pdf", tags=["pdf"])
app.include_router(spreadsheet_jobs, prefix="/spreadsheet", tags=["spreadsheet"])
app.include_router(admin, prefix="/admin", tags=["admin"])


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail},
        )
    logging.exception(exc)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )