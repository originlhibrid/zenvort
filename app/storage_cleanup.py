"""
R2 Storage Cleanup Module
=========================
Handles cleanup of old files in Cloudflare R2 storage.

Storage lifecycle:
- Input files: uploaded by API, consumed by workers, then orphaned if worker fails
- Output files: converted results, available for download via presigned URLs
- Presigned URLs expire after 1 hour (configurable), but the underlying files remain

This module provides:
1. Cleanup of orphaned input files (inputs/{job_id}/)
2. Cleanup of old output files (outputs/{job_id}/) older than retention period
3. Storage usage reporting
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.config import get_settings

logger = logging.getLogger("zenvort.storage_cleanup")


def get_storage_client():
    """Get S3 client for R2."""
    from app.storage import get_s3_client
    return get_s3_client()


def list_objects(prefix: str, max_keys: int = 1000) -> list[dict]:
    """
    List all objects in R2 with the given prefix.
    
    Returns list of dicts with 'Key', 'LastModified', 'Size'.
    """
    client = get_storage_client()
    bucket = get_settings().R2_BUCKET_NAME
    
    objects = []
    continuation_token = None
    
    while True:
        kwargs = {
            "Bucket": bucket,
            "Prefix": prefix,
            "MaxKeys": max_keys,
        }
        if continuation_token:
            kwargs["ContinuationToken"] = continuation_token
        
        response = client.list_objects_v2(**kwargs)
        
        if "Contents" in response:
            for obj in response["Contents"]:
                objects.append({
                    "Key": obj["Key"],
                    "LastModified": obj["LastModified"],
                    "Size": obj["Size"],
                })
        
        if not response.get("IsTruncated"):
            break
        
        continuation_token = response.get("NextContinuationToken")
    
    return objects


def delete_objects(keys: list[str]) -> int:
    """
    Delete multiple objects from R2.
    
    Returns number of objects deleted.
    """
    if not keys:
        return 0
    
    client = get_storage_client()
    bucket = get_settings().R2_BUCKET_NAME
    
    # S3 delete limit is 1000 per request
    deleted = 0
    for i in range(0, len(keys), 1000):
        batch = keys[i:i + 1000]
        
        response = client.delete_objects(
            Bucket=bucket,
            Delete={
                "Objects": [{"Key": key} for key in batch],
                "Quiet": True,
            }
        )
        
        if "Deleted" in response:
            deleted += len(response["Deleted"])
        
        if "Errors" in response:
            for error in response["Errors"]:
                logger.error(f"Failed to delete {error['Key']}: {error['Message']}")
    
    return deleted


def cleanup_old_outputs(retention_days: int = 30) -> dict:
    """
    Clean up output files older than retention period.
    
    Args:
        retention_days: Number of days to retain output files (default: 30)
    
    Returns:
        dict with 'deleted_count', 'deleted_size', 'errors'
    """
    settings = get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    
    logger.info(f"Cleaning up R2 outputs older than {retention_days} days")
    
    objects = list_objects(prefix="outputs/")
    
    to_delete = []
    total_size = 0
    
    for obj in objects:
        last_modified = obj["LastModified"]
        if last_modified.replace(tzinfo=timezone.utc) < cutoff:
            to_delete.append(obj["Key"])
            total_size += obj["Size"]
    
    if to_delete:
        logger.info(f"Found {len(to_delete)} old output files ({total_size / 1024 / 1024:.2f} MB)")
        deleted = delete_objects(to_delete)
        logger.info(f"Deleted {deleted} output files from R2")
    else:
        deleted = 0
        logger.info("No old output files to clean up")
    
    return {
        "deleted_count": deleted,
        "deleted_size_bytes": total_size,
        "errors": [],
    }


def cleanup_orphaned_inputs(max_age_hours: int = 24) -> dict:
    """
    Clean up orphaned input files (inputs/{job_id}/) older than max_age.
    
    These are files that were uploaded but never consumed by a worker,
    typically because:
    - The API crashed after upload but before task dispatch
    - The job was created but never dispatched
    - Worker failed before processing
    
    Args:
        max_age_hours: Maximum age in hours for input files (default: 24)
    
    Returns:
        dict with 'deleted_count', 'deleted_size', 'errors'
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    
    logger.info(f"Cleaning up orphaned R2 inputs older than {max_age_hours} hours")
    
    objects = list_objects(prefix="inputs/")
    
    to_delete = []
    total_size = 0
    
    for obj in objects:
        last_modified = obj["LastModified"]
        if last_modified.replace(tzinfo=timezone.utc) < cutoff:
            to_delete.append(obj["Key"])
            total_size += obj["Size"]
    
    if to_delete:
        logger.info(f"Found {len(to_delete)} orphaned input files ({total_size / 1024 / 1024:.2f} MB)")
        deleted = delete_objects(to_delete)
        logger.info(f"Deleted {deleted} orphaned input files from R2")
    else:
        deleted = 0
        logger.info("No orphaned input files to clean up")
    
    return {
        "deleted_count": deleted,
        "deleted_size_bytes": total_size,
        "errors": [],
    }


def get_storage_stats() -> dict:
    """
    Get current storage usage statistics.
    
    Returns:
        dict with input/output file counts and sizes
    """
    inputs = list_objects(prefix="inputs/")
    outputs = list_objects(prefix="outputs/")
    
    return {
        "inputs": {
            "count": len(inputs),
            "size_bytes": sum(obj["Size"] for obj in inputs),
        },
        "outputs": {
            "count": len(outputs),
            "size_bytes": sum(obj["Size"] for obj in outputs),
        },
        "total": {
            "count": len(inputs) + len(outputs),
            "size_bytes": sum(obj["Size"] for obj in inputs + outputs),
        },
    }


def cleanup_all(retention_days: int = 30, max_age_hours: int = 24) -> dict:
    """
    Run full storage cleanup.
    
    Args:
        retention_days: Days to retain output files
        max_age_hours: Hours to retain orphaned input files
    
    Returns:
        Combined results from all cleanup operations
    """
    results = {
        "orphaned_inputs": cleanup_orphaned_inputs(max_age_hours),
        "old_outputs": cleanup_old_outputs(retention_days),
    }
    
    total_deleted = (
        results["orphaned_inputs"]["deleted_count"] + 
        results["old_outputs"]["deleted_count"]
    )
    total_size = (
        results["orphaned_inputs"]["deleted_size_bytes"] + 
        results["old_outputs"]["deleted_size_bytes"]
    )
    
    logger.info(
        f"Storage cleanup complete: {total_deleted} files, "
        f"{total_size / 1024 / 1024:.2f} MB freed"
    )
    
    return results


# Constants for periodic cleanup
DEFAULT_RETENTION_DAYS = 30
DEFAULT_MAX_AGE_HOURS = 24