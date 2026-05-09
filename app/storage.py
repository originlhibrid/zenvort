import boto3
from botocore.config import Config

from app.config import get_settings

_s3_client = None


def get_s3_client():
    global _s3_client
    if _s3_client is None:
        settings = get_settings()
        endpoint_url = settings.R2_ENDPOINT_URL.format(account_id=settings.R2_ACCOUNT_ID)
        _s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )
    return _s3_client


def upload_file(local_path: str, storage_key: str, content_type: str = "application/octet-stream") -> None:
    get_s3_client().upload_file(
        local_path,
        get_settings().R2_BUCKET_NAME,
        storage_key,
        ExtraArgs={"ContentType": content_type},
    )


def generate_download_url(storage_key: str, expires_seconds: int | None = None) -> str:
    settings = get_settings()
    if expires_seconds is None:
        expires_seconds = settings.PRESIGNED_EXPIRY_SECONDS
    return get_s3_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.R2_BUCKET_NAME, "Key": storage_key},
        ExpiresIn=expires_seconds,
    )


def download_file(storage_key: str, local_path: str) -> None:
    get_s3_client().download_file(
        get_settings().R2_BUCKET_NAME,
        storage_key,
        local_path,
    )
