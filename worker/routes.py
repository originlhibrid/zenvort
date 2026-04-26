from typing import Callable, TypedDict
from worker.converters.gotenberg import convert as gotenberg
from worker.converters.ffmpeg import convert as ffmpeg
from worker.converters.pillow import convert as pillow

ConverterFn = Callable[[str, str, str, str], None]


class ConversionRoute(TypedDict):
    converters: list[ConverterFn]
    description: str


ROUTES: dict[str, ConversionRoute] = {
    "pdf→png":   {"converters": [gotenberg], "description": "PDF to PNG via Gotenberg"},
    "pdf→jpg":   {"converters": [gotenberg], "description": "PDF to JPG via Gotenberg"},
    "pdf→txt":   {"converters": [gotenberg], "description": "PDF to TXT via Gotenberg"},
    "pdf→docx":  {"converters": [gotenberg], "description": "PDF to DOCX via Gotenberg"},
    "pdf→html":  {"converters": [gotenberg], "description": "PDF to HTML via Gotenberg"},
    "pdf→pdf":   {"converters": [gotenberg], "description": "PDF optimization via Gotenberg"},
    "docx→pdf":  {"converters": [gotenberg], "description": "DOCX to PDF via Gotenberg"},
    "docx→txt":  {"converters": [gotenberg], "description": "DOCX to TXT via Gotenberg"},
    "docx→html": {"converters": [gotenberg], "description": "DOCX to HTML via Gotenberg"},
    "md→pdf":    {"converters": [gotenberg], "description": "Markdown to PDF via Gotenberg"},
    "md→html":   {"converters": [gotenberg], "description": "Markdown to HTML via Gotenberg"},
    "md→txt":    {"converters": [gotenberg], "description": "Markdown to TXT via Gotenberg"},
    "md→docx":   {"converters": [gotenberg], "description": "Markdown to DOCX via Gotenberg"},
    "html→pdf":  {"converters": [gotenberg], "description": "HTML to PDF via Gotenberg"},
    "html→docx": {"converters": [gotenberg], "description": "HTML to DOCX via Gotenberg"},
    "png→pdf":   {"converters": [gotenberg], "description": "PNG to PDF via Gotenberg"},
    "jpg→pdf":   {"converters": [gotenberg], "description": "JPG to PDF via Gotenberg"},
    "jpg→png":   {"converters": [pillow],    "description": "JPG to PNG via Pillow"},
    "jpg→webp":  {"converters": [pillow],    "description": "JPG to WebP via Pillow"},
    "jpg→avif":  {"converters": [pillow],    "description": "JPG to AVIF via Pillow"},
    "png→jpg":   {"converters": [pillow],    "description": "PNG to JPG via Pillow"},
    "png→webp":  {"converters": [pillow],    "description": "PNG to WebP via Pillow"},
    "png→avif":  {"converters": [pillow],    "description": "PNG to AVIF via Pillow"},
    "mp4→mp3":   {"converters": [ffmpeg],    "description": "MP4 to MP3 via FFmpeg"},
    "mp4→webm":  {"converters": [ffmpeg],    "description": "MP4 to WebM via FFmpeg"},
    "mp3→wav":   {"converters": [ffmpeg],    "description": "MP3 to WAV via FFmpeg"},
    "wav→mp3":   {"converters": [ffmpeg],    "description": "WAV to MP3 via FFmpeg"},
}

VALID_INPUT_FORMATS = list({k.split("→")[0] for k in ROUTES})
VALID_OUTPUT_FORMATS = list({k.split("→")[1] for k in ROUTES})


def get_route(input_format: str, output_format: str) -> ConversionRoute | None:
    return ROUTES.get(f"{input_format}→{output_format}")
