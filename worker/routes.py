# Total: 145 routes (removed 9 epub routes)
from typing import Callable, TypedDict
from worker.converters import gotenberg, ffmpeg, pillow, tesseract, calibre
from worker.converters.pandoc import convert as pandoc_convert

ConverterFn = Callable[[str, str, str, str], None]


class ConversionRoute(TypedDict):
    converters: list[ConverterFn]
    description: str


ROUTES: dict[str, ConversionRoute] = {
    # ── Documents (Gotenberg — LibreOffice) ───────────────────────────────
    "pdf→png":   {"converters": [gotenberg],                "description": "PDF to PNG via Gotenberg"},
    "pdf→jpg":   {"converters": [gotenberg],                "description": "PDF to JPG via Gotenberg"},
    "pdf→txt":   {"converters": [gotenberg, tesseract],     "description": "PDF to TXT via Gotenberg (fast) + Tesseract (scanned fallback)"},
    "pdf→docx":  {"converters": [gotenberg],                "description": "PDF to DOCX via Gotenberg"},
    "pdf→html":  {"converters": [gotenberg],                "description": "PDF to HTML via Gotenberg"},
    "pdf→rtf":   {"converters": [gotenberg],                "description": "PDF to RTF via Gotenberg"},

    "docx→pdf":  {"converters": [gotenberg],                "description": "DOCX to PDF via Gotenberg"},
    "docx→txt":  {"converters": [gotenberg],                "description": "DOCX to TXT via Gotenberg"},
    "docx→html": {"converters": [gotenberg],                "description": "DOCX to HTML via Gotenberg"},
    "docx→rtf":  {"converters": [pandoc_convert],           "description": "DOCX to RTF via Pandoc"},

    "md→pdf":    {"converters": [gotenberg],                "description": "Markdown to PDF via Gotenberg"},
    "md→html":   {"converters": [gotenberg],                "description": "Markdown to HTML via Gotenberg"},
    "md→txt":    {"converters": [gotenberg],                "description": "Markdown to TXT via Gotenberg"},
    "md→docx":   {"converters": [gotenberg],                "description": "Markdown to DOCX via Gotenberg"},
    "md→rtf":    {"converters": [gotenberg],                "description": "Markdown to RTF via Gotenberg"},

    "html→pdf":  {"converters": [gotenberg],                "description": "HTML to PDF via Gotenberg"},
    "html→docx": {"converters": [gotenberg],                "description": "HTML to DOCX via Gotenberg"},
    "html→txt":  {"converters": [gotenberg],                "description": "HTML to TXT via Gotenberg"},

    "xlsx→pdf":  {"converters": [gotenberg],                "description": "XLSX to PDF via Gotenberg"},
    "xlsx→html": {"converters": [gotenberg],                "description": "XLSX to HTML via Gotenberg"},
    "xlsx→csv":  {"converters": [gotenberg],                "description": "XLSX to CSV via Gotenberg"},
    "xlsx→txt":  {"converters": [gotenberg],                "description": "XLSX to TXT via Gotenberg"},
    "xlsx→docx": {"converters": [gotenberg],                "description": "XLSX to DOCX via Gotenberg"},

    "pptx→pdf":  {"converters": [gotenberg],                "description": "PPTX to PDF via Gotenberg"},
    "pptx→html": {"converters": [gotenberg],                "description": "PPTX to HTML via Gotenberg"},
    "pptx→txt":  {"converters": [gotenberg],                "description": "PPTX to TXT via Gotenberg"},
    "pptx→docx": {"converters": [gotenberg],                "description": "PPTX to DOCX via Gotenberg"},

    "odt→pdf":   {"converters": [gotenberg],                "description": "ODT to PDF via Gotenberg"},
    "odt→txt":   {"converters": [gotenberg],                "description": "ODT to TXT via Gotenberg"},
    "odt→html":  {"converters": [gotenberg],                "description": "ODT to HTML via Gotenberg"},
    "odt→docx":  {"converters": [gotenberg],                "description": "ODT to DOCX via Gotenberg"},

    "ods→pdf":   {"converters": [gotenberg],                "description": "ODS to PDF via Gotenberg"},
    "ods→html":  {"converters": [gotenberg],                "description": "ODS to HTML via Gotenberg"},
    "ods→txt":   {"converters": [gotenberg],                "description": "ODS to TXT via Gotenberg"},

    "odp→pdf":   {"converters": [gotenberg],                "description": "ODP to PDF via Gotenberg"},

    # RTF conversions — RTF is complex, use Gotenberg + Pandoc fallback
    "rtf→txt":   {"converters": [pandoc_convert],           "description": "RTF to TXT via Pandoc"},
    "rtf→html":  {"converters": [gotenberg, pandoc_convert], "description": "RTF to HTML via Gotenberg + Pandoc"},
    "rtf→docx":  {"converters": [pandoc_convert],            "description": "RTF to DOCX via Pandoc"},
    "rtf→pdf":   {"converters": [gotenberg, pandoc_convert], "description": "RTF to PDF via Gotenberg + Pandoc"},

    "csv→pdf":   {"converters": [gotenberg],                "description": "CSV to PDF via Gotenberg"},
    "csv→html":  {"converters": [gotenberg],                "description": "CSV to HTML via Gotenberg"},
    "csv→txt":   {"converters": [gotenberg],                "description": "CSV to TXT via Gotenberg"},
    "csv→docx":  {"converters": [gotenberg],                "description": "CSV to DOCX via Gotenberg"},

    "txt→pdf":   {"converters": [gotenberg],                "description": "TXT to PDF via Gotenberg"},
    "txt→html":  {"converters": [gotenberg],                "description": "TXT to HTML via Gotenberg"},
    "txt→docx":  {"converters": [gotenberg],                "description": "TXT to DOCX via Gotenberg"},

    # ── Images (Pillow — raster, Gotenberg for image→pdf) ──────────────────
    "jpg→png":   {"converters": [pillow],                    "description": "JPG to PNG via Pillow"},
    "jpg→webp":  {"converters": [pillow],                    "description": "JPG to WebP via Pillow"},
    "jpg→avif":  {"converters": [pillow],                    "description": "JPG to AVIF via Pillow"},
    "jpg→bmp":   {"converters": [pillow],                    "description": "JPG to BMP via Pillow"},
    "jpg→tiff":  {"converters": [pillow],                    "description": "JPG to TIFF via Pillow"},
    "jpg→gif":   {"converters": [pillow],                    "description": "JPG to GIF via Pillow"},
    "jpg→pdf":   {"converters": [gotenberg],                 "description": "JPG to PDF via Gotenberg"},

    "png→jpg":   {"converters": [pillow],                    "description": "PNG to JPG via Pillow"},
    "png→webp":  {"converters": [pillow],                    "description": "PNG to WebP via Pillow"},
    "png→avif":  {"converters": [pillow],                    "description": "PNG to AVIF via Pillow"},
    "png→bmp":   {"converters": [pillow],                    "description": "PNG to BMP via Pillow"},
    "png→tiff":  {"converters": [pillow],                    "description": "PNG to TIFF via Pillow"},
    "png→gif":   {"converters": [pillow],                    "description": "PNG to GIF via Pillow"},
    "png→pdf":   {"converters": [gotenberg],                 "description": "PNG to PDF via Gotenberg"},

    "webp→jpg":  {"converters": [pillow],                    "description": "WebP to JPG via Pillow"},
    "webp→png":  {"converters": [pillow],                    "description": "WebP to PNG via Pillow"},
    "webp→avif": {"converters": [pillow],                    "description": "WebP to AVIF via Pillow"},
    "webp→bmp":  {"converters": [pillow],                    "description": "WebP to BMP via Pillow"},
    "webp→tiff": {"converters": [pillow],                    "description": "WebP to TIFF via Pillow"},
    "webp→gif":  {"converters": [pillow],                    "description": "WebP to GIF via Pillow"},
    "webp→pdf":  {"converters": [gotenberg],                 "description": "WebP to PDF via Gotenberg"},

    "avif→jpg":  {"converters": [pillow],                    "description": "AVIF to JPG via Pillow"},
    "avif→png":  {"converters": [pillow],                    "description": "AVIF to PNG via Pillow"},
    "avif→webp": {"converters": [pillow],                    "description": "AVIF to WebP via Pillow"},
    "avif→bmp":  {"converters": [pillow],                    "description": "AVIF to BMP via Pillow"},
    "avif→tiff": {"converters": [pillow],                    "description": "AVIF to TIFF via Pillow"},
    "avif→gif":  {"converters": [pillow],                    "description": "AVIF to GIF via Pillow"},
    "avif→pdf":  {"converters": [gotenberg],                 "description": "AVIF to PDF via Gotenberg"},

    "bmp→jpg":   {"converters": [pillow],                    "description": "BMP to JPG via Pillow"},
    "bmp→png":   {"converters": [pillow],                    "description": "BMP to PNG via Pillow"},
    "bmp→webp":  {"converters": [pillow],                    "description": "BMP to WebP via Pillow"},
    "bmp→avif":  {"converters": [pillow],                    "description": "BMP to AVIF via Pillow"},
    "bmp→tiff":  {"converters": [pillow],                    "description": "BMP to TIFF via Pillow"},
    "bmp→gif":   {"converters": [pillow],                    "description": "BMP to GIF via Pillow"},

    "tiff→jpg":  {"converters": [pillow],                    "description": "TIFF to JPG via Pillow"},
    "tiff→png":  {"converters": [pillow],                    "description": "TIFF to PNG via Pillow"},
    "tiff→webp": {"converters": [pillow],                    "description": "TIFF to WebP via Pillow"},
    "tiff→avif": {"converters": [pillow],                    "description": "TIFF to AVIF via Pillow"},
    "tiff→bmp":  {"converters": [pillow],                    "description": "TIFF to BMP via Pillow"},
    "tiff→gif":  {"converters": [pillow],                    "description": "TIFF to GIF via Pillow"},

    "gif→jpg":   {"converters": [pillow],                    "description": "GIF to JPG via Pillow"},
    "gif→png":   {"converters": [pillow],                    "description": "GIF to PNG via Pillow"},
    "gif→webp":  {"converters": [pillow],                    "description": "GIF to WebP via Pillow"},
    "gif→avif":  {"converters": [pillow],                    "description": "GIF to AVIF via Pillow"},
    "gif→bmp":   {"converters": [pillow],                    "description": "GIF to BMP via Pillow"},
    "gif→tiff":  {"converters": [pillow],                    "description": "GIF to TIFF via Pillow"},
    "gif→pdf":   {"converters": [gotenberg],                 "description": "GIF to PDF via Gotenberg"},

    # ── Video/Audio (FFmpeg) ───────────────────────────────────────────────
    "mp4→mp3":   {"converters": [ffmpeg],                    "description": "MP4 to MP3 via FFmpeg"},
    "mp4→webm":  {"converters": [ffmpeg],                    "description": "MP4 to WebM via FFmpeg"},
    "mp4→avi":   {"converters": [ffmpeg],                    "description": "MP4 to AVI via FFmpeg"},
    "mp4→mov":   {"converters": [ffmpeg],                    "description": "MP4 to MOV via FFmpeg"},
    "mp4→gif":   {"converters": [ffmpeg],                    "description": "MP4 to GIF via FFmpeg"},
    "mp4→ogg":   {"converters": [ffmpeg],                    "description": "MP4 to OGG via FFmpeg"},
    "mp4→flac":  {"converters": [ffmpeg],                    "description": "MP4 to FLAC via FFmpeg"},

    "mp3→wav":   {"converters": [ffmpeg],                    "description": "MP3 to WAV via FFmpeg"},
    "mp3→ogg":   {"converters": [ffmpeg],                    "description": "MP3 to OGG via FFmpeg"},
    "mp3→flac":  {"converters": [ffmpeg],                    "description": "MP3 to FLAC via FFmpeg"},
    "mp3→mp4":   {"converters": [ffmpeg],                    "description": "MP3 to MP4 via FFmpeg"},

    "wav→mp3":   {"converters": [ffmpeg],                    "description": "WAV to MP3 via FFmpeg"},
    "wav→ogg":   {"converters": [ffmpeg],                    "description": "WAV to OGG via FFmpeg"},
    "wav→flac":  {"converters": [ffmpeg],                    "description": "WAV to FLAC via FFmpeg"},
    "wav→mp4":   {"converters": [ffmpeg],                    "description": "WAV to MP4 via FFmpeg"},

    "webm→mp4":  {"converters": [ffmpeg],                    "description": "WebM to MP4 via FFmpeg"},
    "webm→mp3":  {"converters": [ffmpeg],                    "description": "WebM to MP3 via FFmpeg"},
    "webm→avi":  {"converters": [ffmpeg],                    "description": "WebM to AVI via FFmpeg"},
    "webm→mov":  {"converters": [ffmpeg],                    "description": "WebM to MOV via FFmpeg"},
    "webm→ogg":  {"converters": [ffmpeg],                    "description": "WebM to OGG via FFmpeg"},
    "webm→flac": {"converters": [ffmpeg],                    "description": "WebM to FLAC via FFmpeg"},
    "webm→wav":  {"converters": [ffmpeg],                    "description": "WebM to WAV via FFmpeg"},

    "avi→mp4":   {"converters": [ffmpeg],                    "description": "AVI to MP4 via FFmpeg"},
    "avi→mp3":   {"converters": [ffmpeg],                    "description": "AVI to MP3 via FFmpeg"},
    "avi→webm":  {"converters": [ffmpeg],                    "description": "AVI to WebM via FFmpeg"},
    "avi→mov":   {"converters": [ffmpeg],                    "description": "AVI to MOV via FFmpeg"},
    "avi→ogg":   {"converters": [ffmpeg],                    "description": "AVI to OGG via FFmpeg"},
    "avi→flac":  {"converters": [ffmpeg],                    "description": "AVI to FLAC via FFmpeg"},
    "avi→wav":   {"converters": [ffmpeg],                    "description": "AVI to WAV via FFmpeg"},
    "avi→gif":   {"converters": [ffmpeg],                    "description": "AVI to GIF via FFmpeg"},

    "mov→mp4":   {"converters": [ffmpeg],                    "description": "MOV to MP4 via FFmpeg"},
    "mov→mp3":   {"converters": [ffmpeg],                    "description": "MOV to MP3 via FFmpeg"},
    "mov→webm":  {"converters": [ffmpeg],                    "description": "MOV to WebM via FFmpeg"},
    "mov→avi":   {"converters": [ffmpeg],                    "description": "MOV to AVI via FFmpeg"},
    "mov→ogg":   {"converters": [ffmpeg],                    "description": "MOV to OGG via FFmpeg"},
    "mov→flac":  {"converters": [ffmpeg],                    "description": "MOV to FLAC via FFmpeg"},
    "mov→wav":   {"converters": [ffmpeg],                    "description": "MOV to WAV via FFmpeg"},
    "mov→gif":   {"converters": [ffmpeg],                    "description": "MOV to GIF via FFmpeg"},

    "ogg→mp3":   {"converters": [ffmpeg],                    "description": "OGG to MP3 via FFmpeg"},
    "ogg→wav":   {"converters": [ffmpeg],                    "description": "OGG to WAV via FFmpeg"},
    "ogg→flac":  {"converters": [ffmpeg],                    "description": "OGG to FLAC via FFmpeg"},
    "ogg→mp4":   {"converters": [ffmpeg],                    "description": "OGG to MP4 via FFmpeg"},

    "flac→mp3":  {"converters": [ffmpeg],                    "description": "FLAC to MP3 via FFmpeg"},
    "flac→wav":  {"converters": [ffmpeg],                    "description": "FLAC to WAV via FFmpeg"},
    "flac→ogg":  {"converters": [ffmpeg],                    "description": "FLAC to OGG via FFmpeg"},
    "flac→mp4":  {"converters": [ffmpeg],                    "description": "FLAC to MP4 via FFmpeg"},

    # ── OCR (Tesseract) ──────────────────────────────────────────────────
    "jpg→txt":   {"converters": [tesseract],                 "description": "JPG OCR to TXT via Tesseract"},
    "png→txt":   {"converters": [tesseract],                 "description": "PNG OCR to TXT via Tesseract"},
    "webp→txt":  {"converters": [tesseract],                 "description": "WebP OCR to TXT via Tesseract"},
    "bmp→txt":   {"converters": [tesseract],                 "description": "BMP OCR to TXT via Tesseract"},
    "tiff→txt":  {"converters": [tesseract],                 "description": "TIFF OCR to TXT via Tesseract"},
    "gif→txt":   {"converters": [tesseract],                 "description": "GIF OCR to TXT via Tesseract"},
    "avif→txt":  {"converters": [tesseract],                 "description": "AVIF OCR to TXT via Tesseract"},
}

# ── Derived format lists — always in sync with ROUTES ──────────────────────
_VALID_INPUT:  set[str] = {k.split("→")[0] for k in ROUTES}
_VALID_OUTPUT: set[str] = {k.split("→")[1] for k in ROUTES}

VALID_INPUT_FORMATS  = sorted(_VALID_INPUT)
VALID_OUTPUT_FORMATS = sorted(_VALID_OUTPUT)


def get_route(input_format: str, output_format: str) -> ConversionRoute | None:
    return ROUTES.get(f"{input_format}→{output_format}")