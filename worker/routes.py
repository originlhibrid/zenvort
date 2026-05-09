# Conversion route registry: maps (source_format, target_format) -> converter function
# worker/routes.py
# ~160 routes — each is a single line.  The converter handles internal
# library routing (e.g. documents.py picks pdf2docx vs pandoc vs gotenberg).

from worker.converters.documents import convert as documents
from worker.converters.images   import convert as images
from worker.converters.media   import convert as media
from worker.converters.ocr     import convert as ocr
from worker.converters.pdf_tools import convert as pdf_tools
from worker.converters.spreadsheet import convert as spreadsheet

ROUTES = {
    # ── Documents ────────────────────────────────────────────────────────
    "pdf→png":   [documents],
    "pdf→jpg":   [documents],
    "pdf→txt":   [documents, ocr],
    "pdf→docx":  [documents],
    "pdf→html":  [documents],
    "pdf→rtf":   [documents],

    "docx→pdf":  [documents],
    "docx→txt":  [documents],
    "docx→html": [documents],
    "docx→rtf":  [documents],

    "md→pdf":    [documents],
    "md→html":   [documents],
    "md→txt":    [documents],
    "md→docx":   [documents],
    "md→rtf":    [documents],

    "html→pdf":  [documents],
    "html→docx": [documents],
    "html→txt":  [documents],

    "xlsx→pdf":  [documents],
    "xlsx→txt":  [documents],
    "xlsx→docx": [documents],

    "pptx→pdf":  [documents],
    "pptx→html": [documents],
    "pptx→txt":  [documents],
    "pptx→docx": [documents],

    "odt→pdf":   [documents],
    "odt→txt":   [documents],
    "odt→html":  [documents],
    "odt→docx":  [documents],

    "ods→pdf":   [documents],
    "ods→html":  [documents],
    "ods→txt":   [documents],

    "odp→pdf":   [documents],

    "rtf→txt":   [documents],
    "rtf→html":  [documents],
    "rtf→docx":  [documents],
    "rtf→pdf":   [documents],

    "csv→pdf":   [documents],
    "csv→html":  [documents],
    "csv→txt":   [documents],
    "csv→docx":  [documents],

    "txt→pdf":   [documents],
    "txt→html":  [documents],
    "txt→docx":  [documents],
    "txt→rtf":   [documents],

    # ── Images ───────────────────────────────────────────────────────────
    "jpg→png":   [images],
    "jpg→webp":  [images],
    "jpg→avif":  [images],
    "jpg→pdf":   [images],
    "jpg→bmp":   [images],
    "jpg→tiff":  [images],
    "jpg→gif":   [images],

    "png→jpg":   [images],
    "png→webp":  [images],
    "png→avif":  [images],
    "png→pdf":   [images],
    "png→bmp":   [images],
    "png→tiff":  [images],
    "png→gif":   [images],

    "webp→jpg":  [images],
    "webp→png":  [images],
    "webp→avif": [images],
    "webp→bmp":  [images],
    "webp→tiff": [images],
    "webp→gif":  [images],
    "webp→pdf":  [images],

    "avif→jpg":  [images],
    "avif→png":  [images],
    "avif→webp": [images],
    "avif→bmp":  [images],
    "avif→tiff": [images],
    "avif→gif":  [images],
    "avif→pdf":  [images],

    "bmp→jpg":   [images],
    "bmp→png":   [images],
    "bmp→webp":  [images],
    "bmp→avif":  [images],
    "bmp→tiff":  [images],
    "bmp→gif":   [images],
    "bmp→pdf":   [images],

    "tiff→jpg":  [images],
    "tiff→png":  [images],
    "tiff→webp": [images],
    "tiff→avif": [images],
    "tiff→bmp":  [images],
    "tiff→gif":  [images],
    "tiff→pdf":  [images],

    "gif→jpg":   [images],
    "gif→png":   [images],
    "gif→webp":  [images],
    "gif→avif":  [images],
    "gif→bmp":   [images],
    "gif→tiff":  [images],
    "gif→pdf":   [images],

    "svg→pdf":   [images],
    "svg→png":   [images],

    # ── Media ────────────────────────────────────────────────────────────
    "mp4→mp3":   [media],
    "mp4→webm":  [media],
    "mp4→avi":   [media],
    "mp4→mov":   [media],
    "mp4→gif":   [media],
    "mp4→ogg":   [media],
    "mp4→flac":  [media],
    "mp4→wav":   [media],

    "mp3→wav":   [media],
    "mp3→ogg":   [media],
    "mp3→flac":  [media],
    "mp3→mp4":   [media],
    "mp3→webm":  [media],

    "wav→mp3":   [media],
    "wav→ogg":   [media],
    "wav→flac":  [media],
    "wav→mp4":   [media],
    "wav→webm":  [media],

    "webm→mp4":  [media],
    "webm→mp3":  [media],
    "webm→avi":  [media],
    "webm→mov":  [media],
    "webm→ogg":  [media],
    "webm→flac": [media],
    "webm→wav":  [media],

    "avi→mp4":   [media],
    "avi→mp3":   [media],
    "avi→webm":  [media],
    "avi→mov":   [media],
    "avi→ogg":   [media],
    "avi→flac":  [media],
    "avi→wav":   [media],
    "avi→gif":   [media],

    "mov→mp4":   [media],
    "mov→mp3":   [media],
    "mov→webm":  [media],
    "mov→avi":   [media],
    "mov→ogg":   [media],
    "mov→flac":  [media],
    "mov→wav":   [media],
    "mov→gif":   [media],

    "ogg→mp3":   [media],
    "ogg→wav":   [media],
    "ogg→flac":  [media],
    "ogg→mp4":   [media],
    "ogg→webm":  [media],

    "flac→mp3":  [media],
    "flac→wav":  [media],
    "flac→ogg":  [media],
    "flac→mp4":  [media],
    "flac→webm": [media],

    # ── OCR ──────────────────────────────────────────────────────────────
    "jpg→txt":   [ocr],
    "png→txt":   [ocr],
    "webp→txt":  [ocr],
    "bmp→txt":   [ocr],
    "tiff→txt":  [ocr],
    "gif→txt":   [ocr],
    "avif→txt":  [ocr],

    # ── Spreadsheet (openpyxl) ──────────────────────────────────────────
    # xlsx→csv:  first sheet, comma-separated (sheet_name via job metadata)
    # xlsx→json: first sheet → array of row objects  (sheet_name via job metadata)
    # xlsx→html: all sheets as tabbed HTML table
    # csv→xlsx:  header bold, auto column width
    # json→xlsx: keys as headers, objects as rows
    "xlsx→csv":  [spreadsheet],
    "xlsx→html": [spreadsheet],
    "xlsx→json": [spreadsheet],
    "csv→xlsx":  [spreadsheet],
    "json→xlsx": [spreadsheet],

    # ── PDF Tools (pikepdf) ──────────────────────────────────────────────
    "pdf→pdf":   [pdf_tools],
    "pdf→pdfa":  [pdf_tools],
    "pdf→enc":   [pdf_tools],
    "pdf→dec":   [pdf_tools],
}

# Derived — never hardcoded.
VALID_INPUT_FORMATS  = sorted({k.split("→")[0] for k in ROUTES})
VALID_OUTPUT_FORMATS = sorted({k.split("→")[1] for k in ROUTES})