"""
Robust Data Upload Module

Provides:
- Streaming file upload (memory-efficient)
- SHA-256 file deduplication
- Async processing via Celery
- Progress tracking
"""

import hashlib
import os
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from loguru import logger

from src.config.settings import settings


router = APIRouter(prefix="/upload", tags=["upload"])

# Constants
CHUNK_SIZE = 1024 * 1024  # 1MB chunks for streaming
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class UploadStatus(BaseModel):
    """Status of an upload job."""
    job_id: str
    status: str  # "pending", "processing", "completed", "failed"
    progress: float  # 0.0 to 1.0
    message: str
    file_hash: Optional[str] = None
    row_count: Optional[int] = None
    error: Optional[str] = None


# In-memory job tracker (would use Redis in production)
_upload_jobs: Dict[str, UploadStatus] = {}


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of a file using streaming reads."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def check_duplicate(file_hash: str) -> Optional[Path]:
    """Check if file with hash already exists in upload directory."""
    # Check existing parquet files for matching hash
    hash_file = UPLOAD_DIR / f"{file_hash}.hash"
    if hash_file.exists():
        # Read the path from hash file
        original_path = hash_file.read_text().strip()
        if Path(original_path).exists():
            return Path(original_path)
    return None


def save_hash_mapping(file_hash: str, parquet_path: Path) -> None:
    """Save hash -> parquet path mapping for deduplication."""
    hash_file = UPLOAD_DIR / f"{file_hash}.hash"
    hash_file.write_text(str(parquet_path))


async def stream_upload_to_temp(file: UploadFile) -> tuple[Path, int]:
    """
    Stream upload file to temporary location, returning path and size.
    Uses constant memory regardless of file size.
    """
    # Create temp file with appropriate extension
    ext = Path(file.filename).suffix if file.filename else ".tmp"
    temp_fd, temp_path = tempfile.mkstemp(suffix=ext, dir=UPLOAD_DIR)
    temp_path = Path(temp_path)
    
    total_size = 0
    try:
        with os.fdopen(temp_fd, "wb") as temp_file:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                temp_file.write(chunk)
                total_size += len(chunk)
                
                # Check size limit during upload (fail fast)
                if total_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds maximum size of {MAX_FILE_SIZE // (1024*1024)}MB"
                    )
        
        return temp_path, total_size
        
    except Exception as e:
        # Cleanup on error
        if temp_path.exists():
            temp_path.unlink()
        raise


def process_file_sync(job_id: str, temp_path: Path, file_hash: str, sheet_name: Optional[str] = None):
    """
    Process uploaded file synchronously (called by background task or Celery).
    Converts CSV/Excel to Parquet and saves to DuckDB.
    """
    try:
        _upload_jobs[job_id].status = "processing"
        _upload_jobs[job_id].message = "Parsing file..."
        
        import pandas as pd
        from src.database.duckdb_manager import get_duckdb_manager
        
        # Parse file based on extension
        ext = temp_path.suffix.lower()
        if ext == ".csv":
            df = pd.read_csv(temp_path)
        elif ext in [".xlsx", ".xls"]:
            if sheet_name:
                df = pd.read_excel(temp_path, sheet_name=sheet_name)
            else:
                df = pd.read_excel(temp_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
        
        _upload_jobs[job_id].message = f"Processing {len(df)} rows..."
        _upload_jobs[job_id].progress = 0.5
        
        # Save to DuckDB/Parquet
        duckdb_mgr = get_duckdb_manager()
        row_count = duckdb_mgr.save_campaigns(df)
        
        # Save hash mapping for deduplication
        parquet_path = Path("data/campaigns.parquet")
        save_hash_mapping(file_hash, parquet_path)
        
        # Update job status
        _upload_jobs[job_id].status = "completed"
        _upload_jobs[job_id].progress = 1.0
        _upload_jobs[job_id].message = f"Successfully imported {row_count} rows"
        _upload_jobs[job_id].row_count = row_count
        _upload_jobs[job_id].file_hash = file_hash
        
        logger.info(f"Upload job {job_id} completed: {row_count} rows")
        
    except Exception as e:
        logger.error(f"Upload job {job_id} failed: {e}")
        _upload_jobs[job_id].status = "failed"
        _upload_jobs[job_id].error = str(e)
        _upload_jobs[job_id].message = f"Processing failed: {str(e)}"
        
    finally:
        # Cleanup temp file
        if temp_path.exists():
            temp_path.unlink()


@router.post("/stream")
async def stream_upload(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    sheet_name: Optional[str] = Form(None),
):
    """
    Streaming file upload with deduplication.
    
    Features:
    - Memory-efficient streaming (constant memory usage)
    - SHA-256 deduplication (skip re-upload of identical files)
    - Async processing via background tasks
    - Progress tracking via job_id
    
    Returns:
        job_id for tracking upload progress
    """
    # Validate file extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    ext = Path(file.filename).suffix.lower()
    if ext not in [".csv", ".xlsx", ".xls"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file format '{ext}'. Allowed: .csv, .xlsx, .xls"
        )
    
    try:
        # Stream to temp file
        logger.info(f"Streaming upload: {file.filename}")
        temp_path, file_size = await stream_upload_to_temp(file)
        
        # Compute hash for deduplication
        file_hash = compute_file_hash(temp_path)
        logger.info(f"File hash: {file_hash[:16]}... ({file_size / 1024 / 1024:.1f}MB)")
        
        # Check for duplicate
        existing_path = check_duplicate(file_hash)
        if existing_path:
            # Clean up temp file
            temp_path.unlink()
            logger.info(f"Duplicate detected, skipping re-import")
            return JSONResponse({
                "status": "duplicate",
                "message": "File already uploaded (identical content detected)",
                "file_hash": file_hash,
                "original_upload": str(existing_path)
            })
        
        # Create job for tracking
        job_id = f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_hash[:8]}"
        _upload_jobs[job_id] = UploadStatus(
            job_id=job_id,
            status="pending",
            progress=0.1,
            message="File uploaded, queuing for processing...",
            file_hash=file_hash
        )
        
        # Process in background
        background_tasks.add_task(
            process_file_sync,
            job_id,
            temp_path,
            file_hash,
            sheet_name
        )
        
        return JSONResponse({
            "status": "accepted",
            "job_id": job_id,
            "file_hash": file_hash,
            "file_size_mb": round(file_size / 1024 / 1024, 2),
            "message": "File queued for processing. Use /upload/status/{job_id} to track progress."
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{job_id}")
async def get_upload_status(job_id: str):
    """Get the status of an upload job."""
    if job_id not in _upload_jobs:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    return _upload_jobs[job_id]


@router.get("/jobs")
async def list_upload_jobs():
    """List all upload jobs (for debugging)."""
    return list(_upload_jobs.values())
