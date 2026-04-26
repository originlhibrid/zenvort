import os
import subprocess
from worker.security.path_guard import sanitize_and_assert_tmp_path


def convert(
    input_path: str,
    output_path: str,
    input_format: str,
    output_format: str,
    timeout_s: float = 300.0,
) -> None:
    sanitize_and_assert_tmp_path(input_path)
    sanitize_and_assert_tmp_path(output_path)

    cmd = ["ffmpeg", "-y", "-i", input_path, output_path]
    result = subprocess.run(cmd, capture_output=True, timeout=timeout_s)

    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg: exit {result.returncode}: {result.stderr.decode()[:500]}"
        )

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError("ffmpeg: output file missing or empty")

    print(f"[ffmpeg] converted {input_format}→{output_format}")
