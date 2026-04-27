import subprocess
from pathlib import Path
from worker.security.path_guard import sanitize_and_assert_tmp_path

SUPPORTED = {
    "epub": ["html", "txt", "docx", "pdf"],
    "docx": ["epub"],
    "html": ["epub"],
    "md":   ["epub"],
}

def convert(input_path: str, output_path: str, input_format: str,
            output_format: str, timeout_s: float = 120.0) -> None:
    sanitize_and_assert_tmp_path(input_path)
    sanitize_and_assert_tmp_path(output_path)

    if output_format == "pdf":
        # epub→pdf: two-step via html
        html_path = str(Path(output_path).with_suffix(".html"))
        subprocess.run(
            ["pandoc", input_path, "-o", html_path, "--standalone"],
            capture_output=True, text=True, timeout=timeout_s, check=True
        )
        # pass html to gotenberg
        from worker.converters import gotenberg
        gotenberg.convert(html_path, output_path, "html", "pdf", timeout_s)
        return

    result = subprocess.run(
        ["pandoc", input_path, "-o", output_path, "--standalone"],
        capture_output=True, text=True, timeout=timeout_s
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Pandoc failed (exit {result.returncode}): "
            f"{result.stderr[-500:] if result.stderr else 'no stderr'}"
        )

    if not Path(output_path).exists() or Path(output_path).stat().st_size == 0:
        raise RuntimeError("Pandoc produced no output")