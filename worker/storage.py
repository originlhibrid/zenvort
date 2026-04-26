import boto3
from worker.config import get_settings

_settings = None


def _get_s3_client():
    global _settings
    if _settings is None:
        _settings = get_settings()
    s3 = boto3.Session(
        aws_access_key_id=_settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=_settings.R2_SECRET_ACCESS_KEY,
    ).client(
        "s3",
        endpoint_url=f"https://{_settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        region_name="auto",
    )
    return s3


def upload_file(local_path: str, storage_key: str, content_type: str) -> None:
    _get_s3_client().upload_file(
        local_path,
        get_settings().R2_BUCKET_NAME,
        storage_key,
        ExtraArgs={"ContentType": content_type},
    )


def download_file(storage_key: str, local_path: str) -> None:
    _get_s3_client().download_file(get_settings().R2_BUCKET_NAME, storage_key, local_path)


def delete_file(storage_key: str) -> None:
    _get_s3_client().delete_object(Bucket=get_settings().R2_BUCKET_NAME, Key=storage_key)