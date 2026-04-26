from pydantic_settings import BaseSettings
from pydantic import model_validator
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = ""
    DATABASE_URL_SYNC: str = ""
    REDIS_URL: str = "redis://redis:6379/0"
    PORT: int = 3000
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = ""
    R2_PUBLIC_URL: str = ""
    ALLOWED_ORIGIN: str = "http://localhost:5173"
    WORKER_CONCURRENCY: int = 3
    GOTENBERG_URL: str = "http://gotenberg:3002"

    @model_validator(mode="after")
    def check_required_secrets(self):
        required = [
            "DATABASE_URL",
            "DATABASE_URL_SYNC",
            "R2_ACCESS_KEY_ID",
            "R2_SECRET_ACCESS_KEY",
            "R2_BUCKET_NAME",
        ]
        for field in required:
            if not getattr(self, field):
                raise ValueError(f"Required secret {field} is not set")
        return self

    class Config:
        env_file = ".env"
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
