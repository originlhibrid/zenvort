from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from worker.routes import VALID_INPUT_FORMATS

router = APIRouter()

# ── Format constants (mirrors the FORMAT_OPTIONS exposed by the original Telegram bot) ──
# Maps each input format → list of output formats the bot exposed.
# The ROUTES dict in worker/routes.py has all dynamic routes, but this
# static map is what the Telegram UX showed (keyboard picker).

FORMAT_OPTIONS = {
    "pdf":   ["docx", "txt", "html", "png", "jpg"],
    "docx":  ["pdf"],
    "xlsx":  ["pdf"],
    "pptx":  ["pdf"],
    "odt":   ["pdf"],
    "ods":   ["pdf"],
    "odp":   ["pdf"],
    "md":    ["pdf", "html", "docx"],
    "rtf":   ["pdf", "html", "docx", "txt"],
    "txt":   ["pdf"],
    "jpg":   ["png", "webp", "avif", "tiff", "bmp", "gif", "pdf", "txt"],
    "png":   ["jpg", "webp", "avif", "tiff", "bmp", "gif", "pdf", "txt"],
    "webp":  ["jpg", "png", "avif", "tiff", "bmp", "gif", "pdf", "txt"],
    "avif":  ["jpg", "png", "webp", "tiff", "bmp", "gif", "pdf", "txt"],
    "bmp":   ["jpg", "png", "webp", "avif", "tiff", "gif", "pdf", "txt"],
    "tiff":  ["jpg", "png", "webp", "avif", "bmp", "gif", "pdf", "txt"],
    "gif":   ["jpg", "png", "webp", "avif", "tiff", "bmp", "pdf", "txt"],
    "svg":   ["png", "pdf"],
    "mp3":   ["wav", "ogg", "flac"],
    "wav":   ["mp3", "ogg", "flac"],
    "ogg":   ["mp3", "wav", "flac"],
    "flac":  ["mp3", "wav", "ogg"],
    "mp4":   ["mp3", "wav", "avi", "mov", "webm"],
    "avi":   ["mp3", "wav", "mp4", "mov", "webm"],
    "mov":   ["mp3", "wav", "mp4", "avi", "webm"],
    "webm":  ["mp3", "wav", "mp4", "avi", "mov"],
}


# ── Schemas ────────────────────────────────────────────────────────────────────

class FormatOutput(BaseModel):
    format: str
    label: str


class FormatDetail(BaseModel):
    input_format: str
    outputs: list[FormatOutput]


class FormatList(BaseModel):
    formats: list[str]
    total: int


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("", response_model=FormatList)
def list_formats():
    """List all supported input formats."""
    return FormatList(
        formats=sorted(VALID_INPUT_FORMATS),
        total=len(VALID_INPUT_FORMATS),
    )


@router.get("/{fmt}", response_model=FormatDetail)
def get_format_outputs(fmt: str):
    """List available output formats for a given input format."""
    # Check the static FORMAT_OPTIONS map first (what the bot exposed).
    # Falls back to deriving from ROUTES if fmt is in VALID_INPUT_FORMATS
    # but not in the static map (e.g. new routes added dynamically).
    from worker.routes import ROUTES
    if fmt in FORMAT_OPTIONS:
        outputs = FORMAT_OPTIONS[fmt]
    elif fmt in VALID_INPUT_FORMATS:
        outputs = sorted({k.split("→")[1] for k in ROUTES if k.startswith(f"{fmt}→")})
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Format '{fmt}' is not a supported input format",
        )

    return FormatDetail(
        input_format=fmt,
        outputs=[FormatOutput(format=o, label=o.upper()) for o in outputs],
    )