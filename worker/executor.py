import os
import time
import uuid
from dataclasses import dataclass
from worker.security.path_guard import TMP_DIR, sanitize_and_assert_tmp_path


@dataclass
class AttemptResult:
    converter_name: str
    duration_ms: float
    error: str | None


def execute_conversion(
    job_id: str,
    input_path: str,
    output_path: str,
    input_format: str,
    output_format: str,
) -> dict:
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise ValueError(f"Invalid job ID: {job_id}")

    sanitize_and_assert_tmp_path(input_path)
    sanitize_and_assert_tmp_path(output_path)

    from worker.routes import ROUTES
    converters = ROUTES.get(f"{input_format}→{output_format}")
    if not converters:
        raise RuntimeError(f"No conversion route for {input_format}→{output_format}")

    attempts: list[AttemptResult] = []

    for converter_fn in converters:
        converter_name = converter_fn.__module__ + "." + converter_fn.__name__

        if os.path.exists(output_path):
            os.unlink(output_path)

        start = time.perf_counter()
        error = None

        try:
            converter_fn(input_path, output_path, input_format, output_format)
        except Exception as exc:
            error = str(exc)

        duration_ms = int((time.perf_counter() - start) * 1000)

        if error is None:
            return {
                "converter_used": converter_name,
                "attempts": attempts + [
                    AttemptResult(converter_name, duration_ms, None)
                ],
            }

        attempts.append(AttemptResult(converter_name, duration_ms, error))
        print(f"[executor] {converter_name} failed: {error}")

    errors = "\n".join(f"{a.converter_name}: {a.error}" for a in attempts)
    raise RuntimeError(f"All converters failed for {input_format}→{output_format}:\n{errors}")