from pathlib import Path

from PIL import Image
from pdf2image import convert_from_path


def ocr_file(input_path: str, output_path: str, language: str = "eng") -> None:
    input_ext = Path(input_path).suffix.lower()

    if input_ext == ".pdf":
        _ocr_pdf(input_path, output_path, language)
    else:
        _ocr_image(input_path, output_path, language)


def _ocr_image(input_path: str, output_path: str, language: str) -> None:
    try:
        import pytesseract

        img_text = pytesseract.image_to_string(
            Image.open(input_path),
            lang=language,
        )
        Path(output_path).write_text(img_text, encoding="utf-8")
    except Exception as e:
        raise RuntimeError(f"pytesseract OCR failed: {e}")


def _ocr_pdf(input_path: str, output_path: str, language: str) -> None:
    try:
        import pytesseract
    except ImportError as e:
        raise RuntimeError(f"Required library not available: {e}")

    images = convert_from_path(input_path, dpi=300, fmt="png")
    if not images:
        raise RuntimeError("pdf2image produced no pages")

    text_parts = []
    for img in images:
        text = pytesseract.image_to_string(img, lang=language)
        text_parts.append(text)

    full_text = "\n\n".join(text_parts)
    Path(output_path).write_text(full_text, encoding="utf-8")
