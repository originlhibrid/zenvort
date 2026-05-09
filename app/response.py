import os
from typing import Any
from fastapi import Response, HTTPException
from fastapi.responses import FileResponse


def build_response(
    job_id: str,
    output_path: str | None,
    filename: str,
    accept_header: str | None,
    download_param: bool,
) -> Response:
    if download_param or (accept_header and "octet-stream" in accept_header):
        if not output_path or not os.path.exists(output_path):
            raise FileNotFoundError(f"Output file not found: {output_path}")
        return FileResponse(
            path=output_path,
            filename=filename,
            media_type="application/octet-stream",
        )

    from app.storage import generate_download_url

    if not output_path:
        raise FileNotFoundError("Output file not found")

    storage_key = f"outputs/{job_id}/{filename}"
    url = generate_download_url(storage_key)

    return {
        "job_id": job_id,
        "status": "done",
        "filename": filename,
        "url": url,
        "expires_in": 3600,
    }


def error_response(message: str, code: str, job_id: str | None = None) -> dict[str, Any]:
    resp: dict[str, Any] = {"error": message, "code": code}
    if job_id:
        resp["job_id"] = job_id
    return resp


def abort(status_code: int, message: str, code: str, job_id: str | None = None):
    raise HTTPException(status_code=status_code, detail=error_response(message, code, job_id))
