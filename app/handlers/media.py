import subprocess


FFMPEG_TIMEOUT = 300


def convert_media(input_path: str, output_path: str, output_format: str) -> None:
    cmd = ["ffmpeg", "-y", "-i", input_path]
    audio_exts = {"mp3", "wav", "ogg", "flac"}
    output_ext = output_format.lower()

    if output_ext in audio_exts and not _is_audio_only(input_path):
        cmd.append("-vn")

    cmd.extend(["-f", output_ext, output_path])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=FFMPEG_TIMEOUT)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {result.stderr[-500:]}")


def _is_audio_only(input_path: str) -> bool:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv", input_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return "audio" in result.stdout and "video" not in result.stdout
    except Exception:
        return False


def extract_audio(input_path: str, output_path: str, output_format: str = "mp3") -> None:
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vn",
        "-f", output_format,
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=FFMPEG_TIMEOUT)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg audio extraction failed: {result.stderr[-500:]}")


def convert_to_gif(input_path: str, output_path: str, fps: int = 15) -> None:
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", f"fps={fps},scale=320:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
        "-f", "gif",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=FFMPEG_TIMEOUT)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg GIF conversion failed: {result.stderr[-500:]}")
