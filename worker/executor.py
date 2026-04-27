import os
import time
import uuid
import logging
from dataclasses import dataclass

from worker.security.path_guard import TMP_DIR, sanitize_and_assert_tmp_path
from worker.utils import _sanitize_error

logger = logging.getLogger("zenvort.worker")


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
        # Handle both functions (old style) and modules (new 4-file style).
        # Modules have __spec__.name but no __module__; functions have both.
        spec = getattr(converter_fn, "__spec__", None)
        if spec is not None:
            converter_name = spec.name + "." + converter_fn.__name__
        else:
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
                "attempts": attempts
                + [AttemptResult(converter_name, duration_ms, None)],
            }

        attempts.append(AttemptResult(converter_name, duration_ms, error))
        logger.info(f"[executor] {converter_name} failed: {error}")

    # Log full internal details for debugging — never expose to user
    logger.error(
        f"All converters failed for {input_format}→{output_format}:\n"
        + "\n".join(f"  {a.converter_name}: {a.error}" for a in attempts)
    )
    raise RuntimeError(
        _sanitize_error(
            "\n".join(attempt.error or "" for attempt in attempts),
            input_format,
            output_format,
        )
    )
