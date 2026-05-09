import os
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


class MimeMismatchError(ValueError):
    """Raised when the detected MIME type does not match the expected output format."""
    pass


def assert_mime_type_matches(file_path: str, output_format: str) -> None:
    """Verify the detected MIME type matches the expected output format.

    Raises MimeMismatchError if MIME mismatch is detected.
    Skips validation for text-based formats that lack reliable magic-byte signatures.

    Args:
        file_path: Path to the output file produced by the converter.
        output_format: Expected output format (e.g. "pdf", "docx").

    Raises:
        FileNotFoundError: The output file does not exist.
        MimeMismatchError: The detected MIME type doesn't match the expected format.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Output file not found: {file_path}")

    # Text-based and open-container formats — no reliable magic-byte signature.
    # Skip validation to avoid false negatives from converters that wrap
    # plain-text in a different container (e.g. Gotenberg wrapping HTML in a
    # multipart/alternative response).
    if output_format in (
        "txt", "md", "csv", "html",
        "wav", "ogg", "flac",
    ):
        return

    detected = magic.from_file(file_path, mime=True)
    expected = MIME_BY_FORMAT.get(output_format)
    if expected and detected != expected:
        raise MimeMismatchError(
            f"MIME mismatch: expected {expected}, got {detected} "
            f"for output format {output_format}"
        )