import os
import time
import io
import markdown
import httpx
from worker.config import get_settings

settings = get_settings()

GOTENBERG_URL = settings.GOTENBERG_URL
LIBREOFFICE_ROUTE = "/forms/libreoffice/convert"
PDFENGINES_ROUTE = "/forms/pdfengines/convert"

MIME_MAP = {
    "pdf":  "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "html": "text/html",
    "txt":  "text/plain",
    "png":  "image/png",
    "jpg":  "image/jpeg",
    "jpeg": "image/jpeg",
    "odt":  "application/vnd.oasis.opendocument.text",
}


def convert(
    input_path: str,
    output_path: str,
    input_format: str,
    output_format: str,
    timeout_s: float = 120.0,
) -> None:
    from worker.security.path_guard import sanitize_and_assert_tmp_path

    sanitize_and_assert_tmp_path(input_path)
    sanitize_and_assert_tmp_path(output_path)

    endpoint = PDFENGINES_ROUTE if input_format in ("png", "jpg", "jpeg") and output_format == "pdf" else LIBREOFFICE_ROUTE

    file_bytes: bytes
    mime: str
    ext: str
    if input_format == "md":
        with open(input_path, "r", encoding="utf-8") as f:
            md_text = f.read()
        html_content = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
        file_bytes = html_content.encode("utf-8")
        mime = "text/html"
        ext = "html"
    else:
        with open(input_path, "rb") as f:
            file_bytes = f.read()
        mime = MIME_MAP.get(input_format, "application/octet-stream")
        ext = input_format

    start = time.perf_counter()

    with httpx.Client(timeout=httpx.Timeout(timeout_s, connect=5.0)) as client:
        response = client.post(
            f"{GOTENBERG_URL}{endpoint}",
            files={"files": (f"input.{ext}", file_bytes, mime)},
        )

    duration_ms = int((time.perf_counter() - start) * 1000)
    print(f"[gotenberg] converting {input_format}->{output_format} via {endpoint} in {duration_ms}ms")

    if response.status_code != 200:
        raise RuntimeError(
            f"gotenberg: HTTP {response.status_code} for "
            f"{input_format}->{output_format}: {response.text[:500]}"
        )

    try:
        with open(output_path, "wb") as f:
            for chunk in response.iter_bytes(chunk_size=8192):
                f.write(chunk)
    except Exception:
        if os.path.exists(output_path):
            os.unlink(output_path)
        raise

    if os.path.getsize(output_path) == 0:
        raise RuntimeError(f"gotenberg: empty output for {input_format}->{output_format}")

    print(f"[gotenberg] done in {duration_ms}ms ({os.path.getsize(output_path)} bytes)")