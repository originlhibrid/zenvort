import logging
import time
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from api.config import get_settings
from api.routes import auth, jobs, user, billing, admin

settings = get_settings()

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Zenvort API", version="1.0.0")

app.state.limiter = limiter

origins = [settings.ALLOWED_ORIGIN]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health")
async def health():
    return {
        "ok": True,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


app.include_router(auth, prefix="/auth", tags=["auth"])
app.include_router(jobs, prefix="/jobs", tags=["jobs"])
app.include_router(user, prefix="/user", tags=["user"])
app.include_router(billing, prefix="/billing", tags=["billing"])
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