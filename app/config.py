from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = ""
    R2_ENDPOINT_URL: str = "https://{account_id}.r2.cloudflarestorage.com"
    GOTENBERG_URL: str = "http://gotenberg:3000"
    REDIS_URL: str = "redis://redis:6379/0"  # Reserved for Celery integration
    DB_PATH: str = "./zenvort.db"
    MAX_FILE_SIZE_MB: int = 100
    TEMP_DIR: str = "/tmp/zenvort"
    PRESIGNED_EXPIRY_SECONDS: int = 3600
    ADMIN_SECRET: str = ""

    class Config:
        env_file = ".env"
        extra = "allow"


@lru_cache
def get_settings() -> Settings:
    return Settings()
