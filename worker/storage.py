import boto3
from botocore.config import Config
from worker.config import get_settings

settings = get_settings()


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def upload_file(local_path: str, storage_key: str, content_type: str) -> str:
    s3 = get_s3_client()
    s3.upload_file(
        local_path,
        settings.R2_BUCKET_NAME,
        storage_key,
        ExtraArgs={"ContentType": content_type},
    )
    return f"{settings.R2_PUBLIC_URL}/{storage_key}"


def download_file(storage_key: str, local_path: str) -> None:
    s3 = get_s3_client()
    s3.download_file(settings.R2_BUCKET_NAME, storage_key, local_path)


def delete_file(storage_key: str) -> None:
    s3 = get_s3_client()
    s3.delete_object(Bucket=settings.R2_BUCKET_NAME, Key=storage_key)
