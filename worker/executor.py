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
    """Dispatch a file conversion through the converter chain for the given format pair.

    Tries each converter in the route list sequentially. If a converter fails,
    the next one is tried as a fallback. Only raises if ALL converters fail.

    Args:
        job_id: UUID of the conversion job (validated before dispatch).
        input_path: Absolute path to the input file (must be within TMP_DIR).
        output_path: Absolute path for the output file (must be within TMP_DIR).
        input_format: Source format (e.g. "pdf").
        output_format: Target format (e.g. "docx").

    Returns:
        dict with keys: "converter_used" (str), "attempts" (list[AttemptResult]).

    Raises:
        ValueError: Invalid job_id, or path traversal detected.
        RuntimeError: No route found, or all converters failed.
    """
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
        # Identify converter: prefer __spec__.name (module-installed), fallback
        # to __module__ (inline script-style).  This handles both the 1-file
        # converter style (functions with __module__) and 4-file style
        # (module-installed, where __spec__ is set).
        spec = getattr(converter_fn, "__spec__", None)
        if spec is not None:
            converter_name = f"{spec.name}.{converter_fn.__name__}"
        else:
            converter_name = f"{converter_fn.__module__}.{converter_fn.__name__}"

        if os.path.exists(output_path):
            os.unlink(output_path)

        start = time.perf_counter()
        error: str | None = None

        try:
            converter_fn(input_path, output_path, input_format, output_format)
        except Exception as exc:  # noqa: BLE001 — intentional broad catch for fallback chain
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

    # All converters failed — log internal details for ops, return sanitized for user
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