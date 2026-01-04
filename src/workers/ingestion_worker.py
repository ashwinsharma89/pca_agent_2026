"""
Celery Worker for Async File Processing

This module provides background task processing for:
- Large file ingestion
- Data transformation
- Parquet conversion

Usage:
    celery -A src.workers.ingestion_worker worker --loglevel=info
"""

from celery import Celery
from pathlib import Path
from typing import Optional
from datetime import datetime
import pandas as pd
from loguru import logger

from src.config.settings import settings

# Initialize Celery
celery_app = Celery(
    "pca_agent",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Celery Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minute timeout
    worker_prefetch_multiplier=1,  # Process one task at a time for memory control
    result_expires=3600,  # Results expire after 1 hour
)


class TaskProgress:
    """Helper for updating task progress in Celery."""
    
    def __init__(self, task):
        self.task = task
        self.current = 0
        self.total = 100
        
    def update(self, current: int, total: int = 100, message: str = ""):
        self.current = current
        self.total = total
        self.task.update_state(
            state="PROGRESS",
            meta={
                "current": current,
                "total": total,
                "percent": round(current / total * 100, 1),
                "message": message
            }
        )


@celery_app.task(bind=True, name="process_upload")
def process_upload(
    self,
    temp_path: str,
    file_hash: str,
    sheet_name: Optional[str] = None,
    original_filename: Optional[str] = None
):
    """
    Celery task to process uploaded files.
    
    Args:
        temp_path: Path to the temporary uploaded file
        file_hash: SHA-256 hash of the file (for deduplication tracking)
        sheet_name: Sheet name for Excel files
        original_filename: Original filename for logging
        
    Returns:
        dict with processing results
    """
    progress = TaskProgress(self)
    temp_path = Path(temp_path)
    
    try:
        progress.update(10, 100, "Starting file processing...")
        logger.info(f"Processing upload: {original_filename} (hash: {file_hash[:16]}...)")
        
        # Validate file exists
        if not temp_path.exists():
            raise FileNotFoundError(f"Temp file not found: {temp_path}")
        
        # Parse file based on extension
        progress.update(20, 100, "Parsing file...")
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
        
        row_count = len(df)
        logger.info(f"Parsed {row_count} rows from {original_filename}")
        
        progress.update(50, 100, f"Processing {row_count} rows...")
        
        # Normalize date columns
        date_columns = [col for col in df.columns if 'date' in col.lower()]
        for col in date_columns:
            try:
                df[col] = pd.to_datetime(df[col], errors='coerce')
            except Exception as e:
                logger.warning(f"Could not parse date column {col}: {e}")
        
        progress.update(70, 100, "Saving to data store...")
        
        # Import here to avoid circular imports
        from src.database.duckdb_manager import get_duckdb_manager
        
        # Save to DuckDB/Parquet
        duckdb_mgr = get_duckdb_manager()
        saved_count = duckdb_mgr.save_campaigns(df)
        
        # Save hash mapping for deduplication
        hash_file = Path("data/uploads") / f"{file_hash}.hash"
        hash_file.parent.mkdir(parents=True, exist_ok=True)
        hash_file.write_text(str(Path("data/campaigns.parquet")))
        
        progress.update(100, 100, f"Successfully imported {saved_count} rows")
        
        # Cleanup temp file
        if temp_path.exists():
            temp_path.unlink()
            logger.debug(f"Cleaned up temp file: {temp_path}")
        
        return {
            "status": "completed",
            "row_count": saved_count,
            "file_hash": file_hash,
            "message": f"Successfully imported {saved_count} rows"
        }
        
    except Exception as e:
        logger.error(f"File processing failed: {e}")
        
        # Cleanup on error
        if temp_path.exists():
            temp_path.unlink()
            
        return {
            "status": "failed",
            "error": str(e),
            "message": f"Processing failed: {str(e)}"
        }


@celery_app.task(bind=True, name="process_parquet_streaming")
def process_parquet_streaming(
    self,
    csv_path: str,
    output_path: str,
):
    """
    Celery task to convert large CSV to Parquet using Polars streaming.
    Uses constant memory regardless of file size.
    
    Args:
        csv_path: Path to input CSV file
        output_path: Path for output Parquet file
        
    Returns:
        dict with conversion results
    """
    progress = TaskProgress(self)
    
    try:
        import polars as pl
        
        progress.update(10, 100, "Scanning CSV structure...")
        
        # Use Polars lazy API for streaming
        lf = pl.scan_csv(csv_path)
        
        progress.update(30, 100, "Converting to Parquet (streaming)...")
        
        # Sink to Parquet (constant memory)
        lf.sink_parquet(
            output_path,
            compression="snappy",
            row_group_size=100_000  # Optimal for analytics queries
        )
        
        progress.update(100, 100, "Conversion complete")
        
        # Get row count from the written file
        result_lf = pl.scan_parquet(output_path)
        row_count = result_lf.select(pl.count()).collect().item()
        
        return {
            "status": "completed",
            "row_count": row_count,
            "output_path": output_path,
            "message": f"Converted {row_count} rows to Parquet"
        }
        
    except Exception as e:
        logger.error(f"Parquet conversion failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "message": f"Conversion failed: {str(e)}"
        }


# Health check task
@celery_app.task(name="health_check")
def health_check():
    """Simple health check task."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "worker": "ingestion_worker"
    }
