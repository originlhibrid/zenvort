# worker/converters/tesseract.py
# Tesseract OCR — scanned image / PDF → searchable text
#
# Supported conversions:
#   image (jpg, png, webp, bmp, tiff, gif, avif) → txt
#   pdf (scanned) → txt
#
# The fallback chain "gotenberg → tesseract" on pdf→txt gives:
#   • Gotenberg first  : fast for text-based PDFs
#   • Tesseract second : correct for scanned / image-only PDFs

import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from PIL import Image

from worker.security.path_guard import sanitize_and_assert_tmp_path

DEFAULT_LANG = "eng"
DEFAULT_OEM   = "3"
DEFAULT_PSM   = "3"

# Tesseract cannot read these formats — pre-convert to PNG via Pillow first
_UNSUPPORTED_EXTS = frozenset(("avif", "heic", "heif", "jxl", "jfif"))

# Tesseract writes <output_base>.txt automatically; pass output_base, not "stdout"
TESS_CMD_BASE = ["tesseract", "-l", DEFAULT_LANG, "--oem", DEFAULT_OEM, "--psm", DEFAULT_PSM]


def convert(
    input_path: str,
    output_path: str,
    input_format: str,
    output_format: str,
    timeout_s: float = 120.0,
) -> None:
    sanitize_and_assert_tmp_path(input_path)
    sanitize_and_assert_tmp_path(output_path)

    input_path = Path(input_path)
    input_ext  = input_path.suffix.lstrip(".").lower()

    if input_ext == "pdf":
        _ocr_pdf(input_path, output_path, timeout_s)
    elif input_ext in _UNSUPPORTED_EXTS:
        # BUG 4 fix: pre-convert avif/heic/… to PNG, then OCR the PNG
        _ocr_via_png(input_path, output_path, timeout_s)
    else:
        _ocr_image(input_path, output_path, timeout_s)


def _ocr_image(image_path: Path, output_path: str, timeout_s: float) -> None:
    """
    BUG 4 fix: use file output mode — Tesseract writes <base>.txt automatically.
    Do NOT use stdout; passing "stdout" as the output name then writing the
    capture buffer can silently drop output if the capture is empty.
    """
    output_base = str(output_path).removesuffix(".txt")
    result = subprocess.run(
        [*TESS_CMD_BASE, str(image_path), output_base],
        capture_output  = True,
        text            = True,
        timeout         = timeout_s,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(
            f"[tesseract] exit {result.returncode}: {result.stderr.decode()[:300]}"
        )
    print(f"[tesseract] OCR image {image_path.name} → {Path(output_path).name}")


def _ocr_via_png(image_path: Path, output_path: str, timeout_s: float) -> None:
    """
    Pre-convert an unsupported format (avif, heic, etc.) to PNG via Pillow,
    then run tesseract on the temp PNG.
    """
    tmp_dir  = Path(tempfile.mkdtemp(prefix="tess-preconv-"))
    tmp_png  = tmp_dir / f"preconv.{image_path.suffix}.png"
    try:
        img = Image.open(image_path)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.save(tmp_png, format="PNG")
        _ocr_image(tmp_png, output_path, timeout_s)
        print(f"[tesseract] pre-converted {image_path.suffix} → PNG for OCR")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _ocr_pdf(pdf_path: Path, output_path: str, timeout_s: float) -> None:
    """
    Rasterise each page with pdftoppm at 300 DPI, OCR every page,
    then concatenate results.
    """
    pages_dir = Path(tempfile.mkdtemp(prefix="tess-pages-"))
    try:
        subprocess.run(
            ["pdftoppm", "-png", "-r", "300", str(pdf_path), str(pages_dir / "page")],
            capture_output=True,
            timeout=timeout_s,
            check=True,
        )
        page_files = sorted(pages_dir.glob("page-*.png"))
        if not page_files:
            raise RuntimeError(
                f"[tesseract] pdftoppm produced no pages for {pdf_path.name}"
            )

        lines: list[str] = []
        for i, page in enumerate(page_files, start=1):
            output_base = str((pages_dir / f"page-{i}").absolute())
            result = subprocess.run(
                [*TESS_CMD_BASE, str(page), output_base],
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
            if result.returncode not in (0, 1):
                continue  # skip pages that fail — not fatal
            text = result.stdout.strip()
            if text:
                lines.append(f"--- Page {i} ---\n{text}")

        Path(output_path).write_text("\n\n".join(lines), encoding="utf-8")
        print(
            f"[tesseract] OCR PDF {pdf_path.name} "
            f"({len(page_files)} pages) → {Path(output_path).name}"
        )
    finally:
        shutil.rmtree(pages_dir, ignore_errors=True)
