from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from app.auth import verify_api_key
from app.db import get_job, check_and_increment_usage
from app.storage import download_file
from app.config import get_settings
from app.response import abort


settings = get_settings()
router = APIRouter(prefix="/v1/jobs", tags=["jobs"])


@router.get("/{job_id}")
async def get_job_status(
    job_id: str,
    download: bool = Query(False, description="Stream file as attachment"),
    key: dict = Depends(verify_api_key),
):
    tier = key.get("tier", "free")
    endpoint = f"/v1/jobs/{job_id}"

    await check_and_increment_usage(key["key_id"], tier, endpoint, job_id, 0, 200)

    try:
        job = await get_job(job_id)
        if not job:
            abort(404, "Job not found", "NOT_FOUND", job_id=job_id)

        response = {
            "job_id": job["job_id"],
            "status": job["status"],
            "created_at": job["created_at"],
        }

        if job["status"] == "done":
            response["filename"] = job["filename"]
            response["url"] = job["result_url"]
            response["updated_at"] = job["updated_at"]

            if download and job["result_url"]:
                tmp_dir = Path(settings.TEMP_DIR)
                tmp_dir.mkdir(parents=True, exist_ok=True)
                local_path = tmp_dir / f"{job_id}_{job['filename']}"
                download_file(f"outputs/{job_id}/{job['filename']}", str(local_path))
                return FileResponse(
                    path=str(local_path),
                    filename=job["filename"],
                    media_type="application/octet-stream",
                )

        elif job["status"] == "failed":
            response["error"] = job["error"]

        return response
    except HTTPException:
        raise
    except Exception:
        raise