from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_PATH: str = "/data/zenvort.db"
    REDIS_URL: str = "redis://redis:6379/0"
    WORKER_CONCURRENCY: int = 3
    GOTENBERG_URL: str = "http://gotenberg:3000"
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = ""

    class Config:
        env_file = ".env"
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
