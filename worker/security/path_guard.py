import os

TMP_DIR = "/tmp/zenvort"


class PathTraversalError(PermissionError):
    """Raised when a resolved path escapes the sandbox directory."""
    pass


def sanitize_and_assert_tmp_path(path: str) -> str:
    """Resolve and validate that a path stays within the temp directory sandbox.

    Resolves all symlinks and relative components via realpath, then checks
    that the resulting path is a child of TMP_DIR.

    Args:
        path: Any path string (relative or absolute, may contain "..").

    Returns:
        The canonical absolute path if valid.

    Raises:
        PathTraversalError: Path resolves outside TMP_DIR (sandbox escape detected).
    """
    resolved = os.path.realpath(path)
    if not resolved.startswith(TMP_DIR + "/") and resolved != TMP_DIR:
        raise PathTraversalError(
            f"Path traversal detected: {path!r} resolves to {resolved!r} "
            f"(outside sandbox {TMP_DIR!r})"
        )
    return resolved