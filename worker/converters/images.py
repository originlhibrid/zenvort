# worker/converters/images.py
# All image conversions.
# Libraries: Pillow (raster↔raster), PyMuPDF (pdf→image),
#            img2pdf (image→pdf lossless), CairoSVG (svg→*)
#
# Internal routing:
#   svg→*         → CairoSVG
#   pdf→raster    → PyMuPDF
#   raster→pdf    → img2pdf (lossless) or Pillow→img2pdf fallback
#   raster↔raster → Pillow

import os
import logging
import tempfile
from pathlib import Path

from PIL import Image

from worker.security.path_guard import sanitize_and_assert_tmp_path

logger = logging.getLogger(__name__)

# Formats img2pdf supports directly (lossless PDF from raster).
IMG2PDF_SUPPORTED = frozenset(("jpg", "jpeg", "png", "tiff", "bmp"))

# All raster formats Pillow handles for raster↔raster and pdf→image output.
PILLOW_RASTER = frozenset(("jpg", "jpeg", "png", "webp", "avif", "bmp", "tiff", "gif"))

# Map from format string to PIL format name.
PIL_FMT_MAP = {
    "jpg":  "JPEG",
    "jpeg": "JPEG",
    "png":  "PNG",
    "webp": "WEBP",
    "avif": "AVIF",
    "bmp":  "BMP",
    "tiff": "TIFF",
    "gif":  "GIF",
}


def convert(
    input_path: str,
    output_path: str,
    input_format: str,
    output_format: str,
    timeout_s: float = 120.0,
) -> None:
    sanitize_and_assert_tmp_path(input_path)
    sanitize_and_assert_tmp_path(output_path)

    # SVG input: CairoSVG
    if input_format == "svg":
        logger.info(f"[{input_format}→{output_format}] using cairosvg")
        _cairosvg(input_path, output_path, output_format)

    # PDF → raster image: PyMuPDF
    elif input_format == "pdf" and output_format in PILLOW_RASTER:
        logger.info(f"[{input_format}→{output_format}] using pymupdf")
        _pymupdf(input_path, output_path, output_format)

    # Image → PDF: img2pdf (lossless) for supported inputs
    elif output_format == "pdf" and input_format in IMG2PDF_SUPPORTED:
        logger.info(f"[{input_format}→{output_format}] using img2pdf")
        _img2pdf(input_path, output_path)

    # Image → PDF: Pillow→PNG→img2pdf for unsupported raster formats
    elif output_format == "pdf":
        logger.info(f"[{input_format}→{output_format}] using pillow→img2pdf")
        _pillow_to_pdf(input_path, output_path, input_format)

    # Raster ↔ raster: Pillow
    elif input_format in PILLOW_RASTER and output_format in PILLOW_RASTER:
        logger.info(f"[{input_format}→{output_format}] using pillow")
        _pillow(input_path, output_path, input_format, output_format)

    else:
        raise ValueError(
            f"images converter does not support {input_format}→{output_format}"
        )

    _assert_output(output_path, input_format, output_format)


def _assert_output(output_path, input_format, output_format) -> None:
    p = Path(output_path)
    if not p.exists() or p.stat().st_size == 0:
        raise RuntimeError(
            f"images converter produced no output for {input_format}→{output_format}"
        )


def _cairosvg(input_path: str, output_path: str, output_format: str) -> None:
    import cairosvg

    svg_data = Path(input_path).read_bytes()
    if output_format == "pdf":
        cairosvg.svg2pdf(bytestring=svg_data, write_to=output_path)
    elif output_format == "png":
        cairosvg.svg2png(bytestring=svg_data, write_to=output_path)
    else:
        raise ValueError(f"cairosvg does not support svg→{output_format}")


def _pymupdf(input_path: str, output_path: str, output_format: str) -> None:
    import fitz

    doc = fitz.open(input_path)
    try:
        page = doc[0]
        mat = fitz.Matrix(2.0, 2.0)  # 144 DPI
        pix = page.get_pixmap(matrix=mat)
        if output_format in ("jpg", "jpeg"):
            pix.save(output_path, output="jpeg")
        else:
            pix.save(output_path)
    finally:
        doc.close()


def _img2pdf(input_path: str, output_path: str) -> None:
    import img2pdf

    with open(input_path, "rb") as f:
        pdf_bytes = img2pdf.convert(f)
    Path(output_path).write_bytes(pdf_bytes)


def _pillow_to_pdf(input_path: str, output_path: str, input_format: str) -> None:
    """Convert unsupported raster to PNG, then to PDF via img2pdf."""
    import img2pdf

    tmp_path = tempfile.mktemp(suffix=".png")
    try:
        img = Image.open(input_path)
        # Remove alpha / palette before saving as PNG for img2pdf
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
        img.save(tmp_path, "PNG")
        with open(tmp_path, "rb") as f:
            Path(output_path).write_bytes(img2pdf.convert(f))
    finally:
        os.unlink(tmp_path)


def _pillow(
    input_path: str,
    output_path: str,
    input_format: str,
    output_format: str,
) -> None:
    """
    Pillow raster↔raster conversion.
    Handles all mode conversions including:
      - RGBA/P → RGB for JPEG output
      - P → RGBA for formats that support alpha
      - GIF palette handling
    """
    img = Image.open(input_path)

    # JPG does not support alpha or palette — always convert to RGB first
    if img.mode in ("RGBA", "P") and output_format in ("jpg", "jpeg"):
        img = img.convert("RGB")
    elif img.mode == "P" and output_format in ("png", "webp", "avif", "tiff"):
        img = img.convert("RGBA")

    fmt = PIL_FMT_MAP[output_format]
    img.save(output_path, format=fmt)
    logger.info(f"[pillow] converted {input_format}→{output_format}")
