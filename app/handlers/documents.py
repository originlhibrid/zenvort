import os
import time
import subprocess
import tempfile
from pathlib import Path

import httpx
from PIL import Image

from app.config import get_settings
from app.utils.formats import PANDOC_FORMATS, GOTENBERG_FORMATS


def _get_gotenberg_url() -> str:
    return get_settings().GOTENBERG_URL


def convert_to_pdf(input_path: str, output_path: str) -> None:
    _gotenberg_convert(input_path, output_path, "pdf")


def convert_to_docx(input_path: str, output_path: str) -> None:
    _gotenberg_convert(input_path, output_path, "docx")


def convert_to_html(input_path: str, output_path: str) -> None:
    _gotenberg_convert(input_path, output_path, "html")


def convert_to_rtf(input_path: str, output_path: str) -> None:
    _gotenberg_convert(input_path, output_path, "rtf")


def convert_to_txt(input_path: str, output_path: str) -> None:
    _gotenberg_convert(input_path, output_path, "txt")


def convert_to_xlsx(input_path: str, output_path: str) -> None:
    _gotenberg_convert(input_path, output_path, "xlsx")


def convert_markdown_to_pdf(input_path: str, output_path: str) -> None:
    _gotenberg_convert(input_path, output_path, "pdf")


def convert_markdown_to_docx(input_path: str, output_path: str) -> None:
    _gotenberg_markdown_to_docx(input_path, output_path)


def _gotenberg_markdown_to_docx(input_path: str, output_path: str) -> None:
    with open(input_path, "r", encoding="utf-8") as f:
        md_text = f.read()
    import markdown
    html_content = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
    html_path = input_path + ".html"
    try:
        Path(html_path).write_text(html_content, encoding="utf-8")
        _gotenberg_convert(html_path, output_path, "docx")
    finally:
        if os.path.exists(html_path):
            os.unlink(html_path)


def _pandoc_convert(input_path: str, output_path: str) -> None:
    result = subprocess.run(
        ["pandoc", input_path, "-o", output_path, "--standalone"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Pandoc failed: {result.stderr[-300:]}")


def _gotenberg_convert(input_path: str, output_path: str, output_format: str) -> None:
    mime_map = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "html": "text/html",
        "txt": "text/plain",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    ext = Path(input_path).suffix.lstrip(".") or Path(input_path).name.split(".")[-1]

    with open(input_path, "rb") as f:
        file_bytes = f.read()

    mime = mime_map.get(output_format, "application/octet-stream")

    form_fields = [("files", (f"input.{ext}", file_bytes, mime))]
    if output_format in ("docx", "xlsx"):
        form_fields.append(("format", (None, output_format)))

    with httpx.Client(timeout=httpx.Timeout(120.0, connect=5.0)) as client:
        response = client.post(
            f"{_get_gotenberg_url()}/forms/libreoffice/convert",
            files=form_fields,
        )

    if response.status_code != 200:
        raise RuntimeError(
            f"Gotenberg returned HTTP {response.status_code}: {response.text[:500]}"
        )

    with open(output_path, "wb") as f:
        for chunk in response.iter_bytes(chunk_size=8192):
            f.write(chunk)
