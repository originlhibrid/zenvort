from PIL import Image
from worker.security.path_guard import sanitize_and_assert_tmp_path


# Full support matrix — 10 input × 7 output formats (no self-loops)
PIL_ROUTES = {
    ("jpg",  "png"),  ("jpg",  "webp"), ("jpg",  "avif"),
    ("jpg",  "bmp"),  ("jpg",  "tiff"), ("jpg",  "gif"),
    ("png",  "jpg"),  ("png",  "webp"), ("png",  "avif"),
    ("png",  "bmp"),  ("png",  "tiff"), ("png",  "gif"),
    ("webp", "jpg"),  ("webp", "png"),  ("webp", "avif"),
    ("webp", "bmp"),  ("webp", "tiff"), ("webp", "gif"),
    ("avif", "jpg"),  ("avif", "png"),  ("avif", "webp"),
    ("avif", "bmp"),  ("avif", "tiff"), ("avif", "gif"),
    ("bmp",  "jpg"),  ("bmp",  "png"),  ("bmp",  "webp"),
    ("bmp",  "avif"), ("bmp",  "tiff"), ("bmp",  "gif"),
    ("tiff", "jpg"),  ("tiff", "png"),  ("tiff", "webp"),
    ("tiff", "avif"), ("tiff", "bmp"),  ("tiff", "gif"),
    ("gif",  "jpg"),  ("gif",  "png"),  ("gif",  "webp"),
    ("gif",  "avif"), ("gif",  "bmp"),  ("gif",  "tiff"),
}

FMT_MAP = {
    "jpg":  "JPEG",
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
    timeout_s: float = 30.0,
) -> None:
    sanitize_and_assert_tmp_path(input_path)
    sanitize_and_assert_tmp_path(output_path)

    pair = (input_format, output_format)
    if pair not in PIL_ROUTES:
        raise RuntimeError(
            f"pillow: unsupported conversion {input_format}→{output_format}"
        )

    img = Image.open(input_path)

    # JPG does not support alpha or palette — always convert to RGB first
    if img.mode in ("RGBA", "P") and output_format in ("jpg", "jpeg"):
        img = img.convert("RGB")
    elif img.mode == "P" and output_format in ("png", "webp", "avif", "tiff"):
        img = img.convert("RGBA")

    fmt = FMT_MAP[output_format]
    img.save(output_path, format=fmt)

    print(f"[pillow] converted {input_format}→{output_format}")