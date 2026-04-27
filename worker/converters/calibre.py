# worker/converters/calibre.py
# Calibre ebook-convert — handles epub conversions Gotenberg cannot do
# Supports:
#   epub → pdf, docx, txt, html, rtf
#   docx → epub
#   rtf  → epub, pdf, txt, html

import os
import subprocess
from pathlib import Path
from worker.security.path_guard import sanitize_and_assert_tmp_path

SUPPORTED_INPUT  = {"epub", "docx", "rtf", "html", "txt", "pdf"}
SUPPORTED_OUTPUT = {"epub", "pdf", "docx", "txt", "html", "rtf"}

def convert(input_path: str, output_path: str, input_format: str,
            output_format: str, timeout_s: float = 120.0) -> None:
    sanitize_and_assert_tmp_path(input_path)
    sanitize_and_assert_tmp_path(output_path)

    if input_format not in SUPPORTED_INPUT:
        raise ValueError(f"Calibre does not support input format: {input_format}")
    if output_format not in SUPPORTED_OUTPUT:
        raise ValueError(f"Calibre does not support output format: {output_format}")

    # Headless Docker environment setup
    env = os.environ.copy()
    env["CALIBRE_NO_NATIVE_FILEDIALOGS"] = "1"
    env["CALIBRE_WORKER_OUTPUT"] = "1"
    env["DISABLEGPU"] = "1"
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu --no-sandbox --disable-software-rasterizer"
    env["HOME"] = "/tmp/calibre-home"
    env["CALIBRE_CONFIG_DIRECTORY"] = "/tmp/calibre-config"
    env["CALIBRE_TEMP_DIR"] = "/tmp/zenvort"

    os.makedirs("/tmp/calibre-home", exist_ok=True)
    os.makedirs("/tmp/calibre-config", exist_ok=True)

    result = subprocess.run(
        ["ebook-convert", input_path, output_path,
         "--no-default-epub-cover",
         "--pretty-print"],
        capture_output=True,
        text=True,
        timeout=timeout_s,
        env=env,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Calibre ebook-convert failed (exit {result.returncode}): "
            f"{result.stderr[-500:] if result.stderr else 'no stderr'}"
        )

    if not Path(output_path).exists() or Path(output_path).stat().st_size == 0:
        raise RuntimeError("Calibre produced no output file")