import tempfile
from pathlib import Path

from PIL import Image


PIL_FMT_MAP = {
    "jpg": "JPEG",
    "jpeg": "JPEG",
    "png": "PNG",
    "webp": "WEBP",
    "avif": "AVIF",
    "bmp": "BMP",
    "tiff": "TIFF",
    "gif": "GIF",
}


def convert_image(input_path: str, output_path: str, output_format: str, quality: int = 85) -> None:
    if output_format == "svg":
        raise ValueError("SVG output not supported via Pillow")

    img = Image.open(input_path)

    if img.mode in ("RGBA", "P") and output_format in ("jpg", "jpeg"):
        img = img.convert("RGB")
    elif img.mode == "P" and output_format in ("png", "webp", "avif", "tiff"):
        img = img.convert("RGBA")

    fmt = PIL_FMT_MAP.get(output_format, output_format.upper())
    save_kwargs = {"format": fmt}
    if output_format in ("jpg", "jpeg", "webp", "avif"):
        save_kwargs["quality"] = quality

    img.save(output_path, **save_kwargs)


def resize_image(
    input_path: str,
    output_path: str,
    width: int | None = None,
    height: int | None = None,
    maintain_aspect: bool = True,
) -> None:
    img = Image.open(input_path)
    orig_w, orig_h = img.size

    if width is None and height is None:
        raise ValueError("At least one of width or height must be provided")

    if maintain_aspect:
        if width and height:
            img = img.resize((width, height))
        elif width:
            ratio = width / orig_w
            new_h = int(orig_h * ratio)
            img = img.resize((width, new_h))
        elif height:
            ratio = height / orig_h
            new_w = int(orig_w * ratio)
            img = img.resize((new_w, height))
    else:
        img = img.resize((width or orig_w, height or orig_h))

    img.save(output_path)


def svg_to_pdf(input_path: str, output_path: str) -> None:
    import cairosvg

    svg_data = Path(input_path).read_bytes()
    cairosvg.svg2pdf(bytestring=svg_data, write_to=output_path)


def svg_to_png(input_path: str, output_path: str) -> None:
    import cairosvg

    svg_data = Path(input_path).read_bytes()
    cairosvg.svg2png(bytestring=svg_data, write_to=output_path)


def image_to_pdf(input_path: str, output_path: str) -> None:
    import img2pdf

    with open(input_path, "rb") as f:
        pdf_bytes = img2pdf.convert(f)
    Path(output_path).write_bytes(pdf_bytes)
