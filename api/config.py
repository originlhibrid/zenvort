from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_PATH: str = "/data/zenvort.db"
    REDIS_URL: str = "redis://redis:6379/0"
    PORT: int = 3000
    INTERNAL_SECRET: str = ""
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = ""
    R2_PUBLIC_URL: str = ""
    ALLOWED_ORIGIN: str = "http://localhost:5173"
    WORKER_CONCURRENCY: int = 3
    GOTENBERG_URL: str = "http://gotenberg:3000"

    class Config:
        env_file = ".env"
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
