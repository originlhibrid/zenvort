import os
import subprocess
from worker.security.path_guard import sanitize_and_assert_tmp_path

# Audio formats (no video stream in output)
AUDIO_FORMATS = frozenset(("mp3", "wav", "flac", "ogg", "aac", "m4a", "wma"))
# Video formats (output has video)
VIDEO_FORMATS = frozenset(("mp4", "webm", "avi", "mov", "mkv", "gif"))


def convert(
    input_path: str,
    output_path: str,
    input_format: str,
    output_format: str,
    timeout_s: float = 300.0,
) -> None:
    sanitize_and_assert_tmp_path(input_path)
    sanitize_and_assert_tmp_path(output_path)

    # Probe the input for audio streams — BUG 3 fix for exit 234 (stream mapping).
    probe = subprocess.run(
        [
            "ffprobe", "-v", "quiet", "-select_streams", "a",
            "-show_entries", "stream=codec_type",
            "-of", "csv=p=0", input_path,
        ],
        capture_output=True, text=True,
    )
    has_audio = "audio" in probe.stdout

    if output_format in AUDIO_FORMATS:
        if has_audio:
            # Explicitly select first audio stream to avoid FFmpeg exit 234
            cmd = [
                "ffmpeg", "-y", "-i", input_path,
                "-vn", "-map", "0:a:0",
                output_path,
            ]
        else:
            # No audio stream — inject silent audio so container is valid
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                "-t", "0.1", "-y", output_path,
            ]
    elif output_format in VIDEO_FORMATS or output_format == "gif":
        cmd = ["ffmpeg", "-y", "-i", input_path, output_path]
    else:
        cmd = ["ffmpeg", "-y", "-i", input_path, output_path]

    result = subprocess.run(cmd, capture_output=True, timeout=timeout_s)

    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg: exit {result.returncode}: {result.stderr.decode()[:500]}"
        )

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError("ffmpeg: output file missing or empty")

    print(f"[ffmpeg] converted {input_format}→{output_format}")
