import os

TMP_DIR = "/tmp/zenvort"


def sanitize_and_assert_tmp_path(path: str) -> str:
    resolved = os.path.realpath(path)
    if not resolved.startswith(TMP_DIR + "/") and resolved != TMP_DIR:
        raise ValueError(f"Path traversal detected: {path} resolves to {resolved}")
    return resolved
