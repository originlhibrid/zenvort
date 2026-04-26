from PIL import Image
from worker.security.path_guard import sanitize_and_assert_tmp_path


SUPPORTED = {
    ("jpg", "png"), ("jpg", "webp"), ("jpg", "avif"),
    ("png", "jpg"), ("png", "webp"), ("png", "avif"),
    ("webp", "jpg"), ("webp", "png"),
}

FMT_MAP = {"jpg": "JPEG", "png": "PNG", "webp": "WEBP", "avif": "AVIF"}


def convert(
    input_path: str,
    output_path: str,
    input_format: str,
    output_format: str,
    timeout_s: float = 30.0,
) -> None:
    sanitize_and_assert_tmp_path(input_path)
    sanitize_and_assert_tmp_path(output_path)

    img = Image.open(input_path)

    # JPG does not support alpha or palette — convert to RGB
    if img.mode in ("RGBA", "P") and output_format == "jpg":
        img = img.convert("RGB")

    fmt = FMT_MAP[output_format]
    img.save(output_path, format=fmt)

    print(f"[pillow] converted {input_format}→{output_format}")
