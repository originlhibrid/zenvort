# worker/utils.py
# Shared utilities.  Never expose internal library names, file paths,
# or dependency details to users — sanitize all error messages here.


def _sanitize_error(error: str, input_format: str, output_format: str) -> str:
    """
    Convert internal error messages to user-friendly messages.
    Never expose library names, file paths, or dependency details.
    """
    error_lower = error.lower()

    # Unsupported format combination
    if "does not support" in error_lower or "no route" in error_lower:
        return f"Conversion from {input_format} to {output_format} is not supported."

    # File is corrupted or unreadable
    if any(
        x in error_lower
        for x in ["invalid", "corrupt", "malformed", "cannot open", "not a valid"]
    ):
        return f"The uploaded {input_format} file appears to be corrupted or invalid."

    # File too large
    if any(x in error_lower for x in ["too large", "size limit", "413"]):
        return "The file is too large to convert."

    # Timeout
    if any(x in error_lower for x in ["timeout", "timed out", "time limit"]):
        return "Conversion timed out. Try with a smaller file."

    # Password protected
    if any(x in error_lower for x in ["password", "encrypted", "protected"]):
        return f"The {input_format} file is password protected and cannot be converted."

    # Out of memory
    if any(x in error_lower for x in ["memory", "oom", "killed"]):
        return "Conversion failed — file may be too complex. Try a smaller file."

    # Generic fallback — never expose internals
    return (
        f"Conversion from {input_format} to {output_format} failed. "
        "Please try again or contact support."
    )
