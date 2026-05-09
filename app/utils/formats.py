import magic


IMAGE_FORMATS = frozenset(("jpg", "jpeg", "png", "webp", "avif", "bmp", "tiff", "gif"))
DOCUMENT_FORMATS = frozenset(("docx", "pptx", "odt", "xlsx", "ods", "odp"))
MARKUP_FORMATS = frozenset(("md", "html", "rtf", "txt"))
SPREADSHEET_FORMATS = frozenset(("xlsx", "csv", "json"))
AUDIO_FORMATS = frozenset(("mp3", "wav", "ogg", "flac"))
VIDEO_FORMATS = frozenset(("mp4", "avi", "mov", "webm", "mkv"))


GOTENBERG_FORMATS = DOCUMENT_FORMATS | MARKUP_FORMATS | frozenset(("pdf",))
PANDOC_FORMATS = frozenset(("md", "html", "rtf", "txt"))
IMAGE_TO_PDF_FORMATS = frozenset(("jpg", "jpeg", "png", "tiff", "bmp"))
PDF_OUTPUT_FORMATS = frozenset(("pdf",))
DOCX_OUTPUT_FORMATS = frozenset(("docx",))
PILLOW_OUTPUT_FORMATS = IMAGE_FORMATS | frozenset(("pdf",))


MIME_TO_FORMAT = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.oasis.opendocument.text": "odt",
    "application/vnd.oasis.opendocument.spreadsheet": "ods",
    "application/vnd.oasis.opendocument.presentation": "odp",
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/avif": "avif",
    "image/bmp": "bmp",
    "image/tiff": "tiff",
    "image/gif": "gif",
    "image/svg+xml": "svg",
    "text/plain": "txt",
    "text/markdown": "md",
    "text/html": "html",
    "application/rtf": "rtf",
    "text/csv": "csv",
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
    "audio/ogg": "ogg",
    "audio/flac": "flac",
    "video/mp4": "mp4",
    "video/x-msvideo": "avi",
    "video/quicktime": "mov",
    "video/webm": "webm",
}


def detect_format(file_path: str | Path) -> str | None:
    mime = magic.from_file(str(file_path), mime=True)
    return MIME_TO_FORMAT.get(mime)


def extension_to_format(ext: str) -> str:
    ext = ext.lower().lstrip(".")
    return ext if ext else ""


def is_document_format(fmt: str) -> bool:
    return fmt in DOCUMENT_FORMATS


def is_image_format(fmt: str) -> bool:
    return fmt in IMAGE_FORMATS


def is_audio_format(fmt: str) -> bool:
    return fmt in AUDIO_FORMATS


def is_video_format(fmt: str) -> bool:
    return fmt in VIDEO_FORMATS


def is_spreadsheet_format(fmt: str) -> bool:
    return fmt in SPREADSHEET_FORMATS


CONVERSION_ROUTES = {
    ("docx", "pdf"): "gotenberg",
    ("pptx", "pdf"): "gotenberg",
    ("odt", "pdf"): "gotenberg",
    ("xlsx", "pdf"): "gotenberg",
    ("ods", "pdf"): "gotenberg",
    ("odp", "pdf"): "gotenberg",
    ("md", "pdf"): "gotenberg",
    ("html", "pdf"): "gotenberg",
    ("rtf", "pdf"): "pandoc",
    ("txt", "pdf"): "gotenberg",
    ("md", "docx"): "pandoc",
    ("md", "html"): "pandoc",
    ("md", "rtf"): "pandoc",
    ("html", "docx"): "gotenberg",
    ("html", "rtf"): "pandoc",
    ("rtf", "docx"): "pandoc",
    ("rtf", "html"): "pandoc",
    ("txt", "docx"): "gotenberg",
    ("txt", "html"): "gotenberg",
    ("txt", "rtf"): "pandoc",
    ("pdf", "docx"): "pdf2docx",
    ("svg", "pdf"): "cairosvg",
    ("svg", "png"): "cairosvg",
    ("jpg", "pdf"): "img2pdf",
    ("png", "pdf"): "img2pdf",
    ("jpeg", "pdf"): "img2pdf",
    ("tiff", "pdf"): "img2pdf",
    ("bmp", "pdf"): "img2pdf",
    ("gif", "pdf"): "img2pdf",
}


def get_converter(input_format: str, output_format: str) -> str | None:
    return CONVERSION_ROUTES.get((input_format, output_format))
