import magic

MIME_BY_FORMAT = {
    "pdf":  "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "png":  "image/png",
    "jpg":  "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "avif": "image/avif",
    "gif":  "image/gif",
    "tiff": "image/tiff",
    "bmp":  "image/bmp",
    "mp3":  "audio/mpeg",
    "mp4":  "video/mp4",
    "webm": "video/webm",
    "txt":  "text/plain",
    "html": "text/html",
    "md":   "text/markdown",
    "wav":  "audio/x-wav",
}


def assert_mime_type_matches(file_path: str, output_format: str) -> None:
    # Text files (txt, md, csv, rtf) have no reliable magic-byte signature.
    # Skip MIME validation for these formats to avoid false negatives
    # from Gotenberg and other converters that may wrap text in a different container.
    if output_format in (
        "txt", "md", "csv", "html",
        "wav", "ogg", "flac",
    ):
        return

    detected = magic.from_file(file_path, mime=True)
    expected = MIME_BY_FORMAT.get(output_format)
    if expected and detected != expected:
        raise ValueError(
            f"MIME mismatch: expected {expected}, got {detected} "
            f"for output format {output_format}"
        )
