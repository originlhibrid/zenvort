import os
import uuid
import shutil
from pathlib import Path

from app.config import get_settings


def _tmp_dir() -> Path:
    return Path(get_settings().TEMP_DIR)


def ensure_temp_dir(job_id: str) -> Path:
    path = _tmp_dir() / job_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def cleanup_temp_dir(job_id: str) -> None:
    path = _tmp_dir() / job_id
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)


def save_upload(file_content: bytes, job_id: str, filename: str) -> Path:
    dest_dir = ensure_temp_dir(job_id)
    dest_path = dest_dir / filename
    Path(dest_path).write_bytes(file_content)
    return dest_path


def temp_input_path(job_id: str, ext: str) -> Path:
    return ensure_temp_dir(job_id) / f"input.{ext}"


def temp_output_path(job_id: str, filename: str) -> Path:
    return ensure_temp_dir(job_id) / filename


def new_job_id() -> str:
    return str(uuid.uuid4())
