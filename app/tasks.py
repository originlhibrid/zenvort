import os
import sqlite3
import shutil
import glob
from pathlib import Path

from app.worker import celery_app
from app.storage import upload_file, generate_download_url, get_s3_client
from app.config import get_settings

settings = get_settings()
DB_PATH = getattr(settings, "DB_PATH", "./zenvort.db")


def _sync_update_job(
    job_id: str,
    status: str,
    result_url: str | None = None,
    filename: str | None = None,
    error: str | None = None,
) -> None:
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """UPDATE jobs SET status = ?, result_url = ?, filename = ?, error = ?, updated_at = ?
           WHERE job_id = ?""",
        (status, result_url, filename, error, now, job_id),
    )
    conn.commit()
    conn.close()


def _sync_get_job(job_id: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def _fire_webhook(job_id: str, status: str, result_url: str | None, filename: str | None, error: str | None) -> None:
    row = _sync_get_job(job_id)
    if not row:
        return
    webhook_url = row.get("webhook_url")
    if not webhook_url:
        return
    try:
        import httpx
        payload = {"job_id": job_id, "status": status}
        if result_url:
            payload["url"] = result_url
        if filename:
            payload["filename"] = filename
        if error:
            payload["error"] = error
        httpx.post(webhook_url, json=payload, timeout=10.0)
    except Exception:
        pass


def _cleanup(job_id: str) -> None:
    tmp = Path(settings.TEMP_DIR)
    for f in glob.glob(f"{tmp}/{job_id}-*"):
        try:
            os.unlink(f)
        except OSError:
            pass
    job_dir = tmp / job_id
    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)


def _upload_output(local_path: str, job_id: str, filename: str) -> str:
    storage_key = f"outputs/{job_id}/{filename}"
    content_type = "application/octet-stream"
    if filename.endswith(".pdf"):
        content_type = "application/pdf"
    elif filename.endswith(".txt"):
        content_type = "text/plain"
    elif filename.endswith(".zip"):
        content_type = "application/zip"
    upload_file(local_path, storage_key, content_type)
    return generate_download_url(storage_key)


@celery_app.task(bind=True, name="tasks.process_pdf")
def process_pdf(self, job_id: str, operation: str, input_path: str, params: dict) -> dict:
    from app.handlers.pdf_ops import (
        merge_pdfs, split_pdf, rotate_pdf, watermark_pdf,
        stamp_pdf, encrypt_pdf, decrypt_pdf, compress_pdf,
        read_metadata, write_metadata, get_bookmarks, write_bookmarks,
        flatten_pdf, convert_to_pdfa,
    )

    _sync_update_job(job_id, "processing")

    output_ext = params.get("output_ext", "pdf")
    output_path = str(Path(settings.TEMP_DIR) / f"{job_id}-output.{output_ext}")
    webhook_url = params.pop("_webhook_url", None)

    try:
        if operation == "merge":
            input_paths = params["input_paths"]
            merge_pdfs(input_paths, output_path)
        elif operation == "split":
            pages = params["pages"]
            split_pdf(input_path, output_path, pages)
        elif operation == "rotate":
            degrees = params["degrees"]
            pages = params.get("pages")
            rotate_pdf(input_path, output_path, degrees, pages)
        elif operation == "watermark":
            watermark_pdf(
                input_path, output_path,
                text=params["text"],
                opacity=params.get("opacity", 0.3),
                font_size=params.get("font_size", 48),
                color=params.get("color", "#FF0000"),
                angle=params.get("angle", 45),
            )
        elif operation == "stamp":
            stamp_pdf(
                input_path, output_path,
                stamp_path=params["stamp_path"],
                position=params.get("position", "bottom-right"),
                scale=params.get("scale", 0.2),
            )
        elif operation == "encrypt":
            encrypt_pdf(
                input_path, output_path,
                password=params["password"],
                owner_password=params.get("owner_password"),
                permissions=params.get("permissions"),
            )
        elif operation == "decrypt":
            decrypt_pdf(input_path, output_path, password=params["password"])
        elif operation == "compress":
            compress_pdf(input_path, output_path, quality=params.get("quality", "medium"))
        elif operation == "metadata":
            read_metadata(input_path)
            output_path = None
        elif operation == "write_metadata":
            write_metadata(input_path, output_path, params.get("metadata", {}))
        elif operation == "bookmarks":
            get_bookmarks(input_path)
            output_path = None
        elif operation == "write_bookmarks":
            write_bookmarks(input_path, output_path, params.get("bookmarks", []))
        elif operation == "flatten":
            flatten_pdf(input_path, output_path)
        elif operation == "pdfa":
            convert_to_pdfa(input_path, output_path, standard=params.get("standard", "PDF/A-2b"))
        else:
            raise ValueError(f"Unknown PDF operation: {operation}")

        if output_path and Path(output_path).exists():
            filename = f"output.{output_ext}"
            result_url = _upload_output(output_path, job_id, filename)
            _sync_update_job(job_id, "done", result_url=result_url, filename=filename)
        else:
            _sync_update_job(job_id, "done", result_url=None, filename="input.pdf")

        _fire_webhook(job_id, "done", result_url or None, filename=filename if output_path else "input.pdf", error=None)

    except Exception as e:
        _sync_update_job(job_id, "failed", error=str(e))
        _fire_webhook(job_id, "failed", result_url=None, filename=None, error=str(e))
        raise

    finally:
        _cleanup(job_id)


@celery_app.task(bind=True, name="tasks.process_convert")
def process_convert(self, job_id: str, input_path: str, params: dict) -> dict:
    input_format = params["input_format"]
    output_format = params["output_format"]
    output_ext = params.get("output_ext", output_format)
    output_path = str(Path(settings.TEMP_DIR) / f"{job_id}-output.{output_ext}")

    _sync_update_job(job_id, "processing")
    webhook_url = params.pop("_webhook_url", None)

    try:
        if input_format in ("mp4", "avi", "mov", "webm") and output_ext in ("mp3", "wav", "ogg", "flac"):
            from app.handlers.media import extract_audio
            extract_audio(input_path, output_path, output_ext)
        elif input_format == "mp4" and output_ext == "gif":
            from app.handlers.media import convert_to_gif
            convert_to_gif(input_path, output_path)
        elif input_format in ("mp4", "avi", "mov", "webm") and output_ext in ("mp4", "webm"):
            from app.handlers.media import convert_media
            convert_media(input_path, output_path, output_ext)
        elif input_format in ("mp3", "wav", "ogg", "flac") and output_ext in ("mp3", "wav", "ogg", "flac"):
            from app.handlers.media import convert_media
            convert_media(input_path, output_path, output_ext)
        elif input_format in ("jpg", "jpeg", "png", "webp", "avif", "bmp", "tiff", "gif") and output_ext == "pdf":
            from app.handlers.images import image_to_pdf
            image_to_pdf(input_path, output_path)
        elif input_format == "svg" and output_ext == "pdf":
            from app.handlers.images import svg_to_pdf
            svg_to_pdf(input_path, output_path)
        elif input_format == "svg" and output_ext == "png":
            from app.handlers.images import svg_to_png
            svg_to_png(input_path, output_path)
        elif all(f in ("jpg", "jpeg", "png", "webp", "avif", "bmp", "tiff", "gif") for f in (input_format, output_ext)):
            from app.handlers.images import convert_image
            convert_image(input_path, output_path, output_ext)
        else:
            from app.handlers.documents import _gotenberg_convert
            _gotenberg_convert(input_path, output_path, output_format)

        filename = f"output.{output_ext}"
        result_url = _upload_output(output_path, job_id, filename)
        _sync_update_job(job_id, "done", result_url=result_url, filename=filename)
        _fire_webhook(job_id, "done", result_url, filename=filename, error=None)

    except Exception as e:
        _sync_update_job(job_id, "failed", error=str(e))
        _fire_webhook(job_id, "failed", result_url=None, filename=None, error=str(e))
        raise

    finally:
        _cleanup(job_id)


@celery_app.task(bind=True, name="tasks.process_ocr")
def process_ocr(self, job_id: str, input_path: str, params: dict) -> dict:
    from app.handlers.ocr import ocr_file

    _sync_update_job(job_id, "processing")
    webhook_url = params.pop("_webhook_url", None)

    try:
        language = params.get("language", "eng")
        output_path = str(Path(settings.TEMP_DIR) / f"{job_id}-output.txt")
        ocr_file(input_path, output_path, language)

        filename = "output.txt"
        result_url = _upload_output(output_path, job_id, filename)
        _sync_update_job(job_id, "done", result_url=result_url, filename=filename)
        _fire_webhook(job_id, "done", result_url, filename=filename, error=None)

    except Exception as e:
        _sync_update_job(job_id, "failed", error=str(e))
        _fire_webhook(job_id, "failed", result_url=None, filename=None, error=str(e))
        raise

    finally:
        _cleanup(job_id)


@celery_app.task(bind=True, name="tasks.process_image")
def process_image(self, job_id: str, operation: str, input_path: str, params: dict) -> dict:
    from app.handlers.images import convert_image, resize_image, svg_to_pdf, svg_to_png

    _sync_update_job(job_id, "processing")
    webhook_url = params.pop("_webhook_url", None)

    try:
        if operation == "convert":
            output_format = params["output_format"]
            quality = params.get("quality", 85)
            input_ext = params["input_ext"]
            output_ext = output_format
            output_path = str(Path(settings.TEMP_DIR) / f"{job_id}-output.{output_ext}")

            if input_ext == "svg" and output_format == "pdf":
                svg_to_pdf(input_path, output_path)
            elif input_ext == "svg" and output_format == "png":
                svg_to_png(input_path, output_path)
            else:
                convert_image(input_path, output_path, output_format, quality)

        elif operation == "resize":
            input_ext = params["input_ext"]
            output_path = str(Path(settings.TEMP_DIR) / f"{job_id}-resized.{input_ext}")
            resize_image(
                input_path, output_path,
                width=params.get("width"),
                height=params.get("height"),
                maintain_aspect=params.get("maintain_aspect", True),
            )
            output_ext = input_ext

        filename = f"output.{output_ext}" if operation == "convert" else f"resized.{input_ext}"
        result_url = _upload_output(output_path, job_id, filename)
        _sync_update_job(job_id, "done", result_url=result_url, filename=filename)
        _fire_webhook(job_id, "done", result_url, filename=filename, error=None)

    except Exception as e:
        _sync_update_job(job_id, "failed", error=str(e))
        _fire_webhook(job_id, "failed", result_url=None, filename=None, error=str(e))
        raise

    finally:
        _cleanup(job_id)


@celery_app.task(bind=True, name="tasks.process_media")
def process_media(self, job_id: str, input_path: str, params: dict) -> dict:
    from app.handlers.media import convert_media, extract_audio, convert_to_gif

    _sync_update_job(job_id, "processing")
    webhook_url = params.pop("_webhook_url", None)

    try:
        input_ext = params["input_ext"]
        output_format = params["output_format"]
        output_path = str(Path(settings.TEMP_DIR) / f"{job_id}-output.{output_format}")

        if input_ext == "mp4" and output_format == "mp3":
            extract_audio(input_path, output_path, "mp3")
        elif input_ext == "mp4" and output_format == "gif":
            convert_to_gif(input_path, output_path)
        else:
            convert_media(input_path, output_path, output_format)

        filename = f"output.{output_format}"
        result_url = _upload_output(output_path, job_id, filename)
        _sync_update_job(job_id, "done", result_url=result_url, filename=filename)
        _fire_webhook(job_id, "done", result_url, filename=filename, error=None)

    except Exception as e:
        _sync_update_job(job_id, "failed", error=str(e))
        _fire_webhook(job_id, "failed", result_url=None, filename=None, error=str(e))
        raise

    finally:
        _cleanup(job_id)
