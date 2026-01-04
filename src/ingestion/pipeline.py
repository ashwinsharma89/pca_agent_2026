"""
Data Sink (Layer 4) and Pipeline Orchestrator

Final layer that stores validated data to Parquet with partitioning.
Also provides the Pipeline class that chains all layers together.

Design Pattern: Pipeline/Builder Pattern
Input: Validated DataFrame from Layer 3
Output: Parquet files with date partitioning
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Iterator
from datetime import datetime
from loguru import logger

from .adapters import BaseAdapter, get_adapter
from .normalizer import DataNormalizer, normalize_dataframe, SchemaEnforcer
from .validators import DataValidator, ValidationResult, validate_dataframe


# Default data directory
DATA_DIR = Path("data")
DEFAULT_CAMPAIGNS_DIR = DATA_DIR / "campaigns"


class ParquetSink:
    """
    Writes DataFrames to Parquet with optional date partitioning.
    
    Features:
    - Date-based partitioning (year/month)
    - Snappy compression
    - Append mode support
    """
    
    def __init__(
        self,
        base_path: Path = DEFAULT_CAMPAIGNS_DIR,
        partition_by: Optional[str] = "date",
        compression: str = "snappy"
    ):
        """
        Initialize Parquet sink.
        
        Args:
            base_path: Base directory for parquet files
            partition_by: Column to partition by (or None for single file)
            compression: Compression algorithm (snappy, gzip, zstd)
        """
        self.base_path = Path(base_path)
        self.partition_by = partition_by
        self.compression = compression
        self.rows_written = 0
        
        # Create directory if needed
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def write(self, df: pd.DataFrame) -> int:
        """
        Write DataFrame to Parquet storage.
        
        Args:
            df: DataFrame to write
        
        Returns:
            Number of rows written
        """
        if df.empty:
            return 0
        
        if self.partition_by and self.partition_by in df.columns:
            return self._write_partitioned(df)
        else:
            return self._write_single(df)
    
    def _write_partitioned(self, df: pd.DataFrame) -> int:
        """Write with date partitioning."""
        rows_written = 0
        
        # Ensure date column is datetime
        if self.partition_by == 'date':
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df = df.dropna(subset=['date'])
            
            if df.empty:
                logger.warning("No valid dates for partitioning")
                return 0
            
            # Group by year/month
            df['_year'] = df['date'].dt.year
            df['_month'] = df['date'].dt.month
            
            for (year, month), group_df in df.groupby(['_year', '_month']):
                partition_path = self.base_path / f"year={year}" / f"month={month:02d}"
                partition_path.mkdir(parents=True, exist_ok=True)
                
                # Remove temp columns
                write_df = group_df.drop(columns=['_year', '_month'])
                
                # Generate filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_path = partition_path / f"data_{timestamp}.parquet"
                
                write_df.to_parquet(
                    file_path,
                    compression=self.compression,
                    index=False
                )
                
                rows_written += len(write_df)
                logger.debug(f"Wrote {len(write_df)} rows to {file_path}")
        
        self.rows_written += rows_written
        return rows_written
    
    def _write_single(self, df: pd.DataFrame) -> int:
        """Write to a single parquet file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = self.base_path / f"data_{timestamp}.parquet"
        
        df.to_parquet(
            file_path,
            compression=self.compression,
            index=False
        )
        
        rows_written = len(df)
        self.rows_written += rows_written
        logger.info(f"Wrote {rows_written} rows to {file_path}")
        
        return rows_written


class IngestionPipeline:
    """
    Orchestrates the full ingestion pipeline.
    
    Pipeline: Adapter -> Normalizer -> Validator -> Sink
    
    Features:
    - Chunk-based processing for memory efficiency
    - Error handling and recovery
    - Progress callbacks
    - Detailed reporting
    """
    
    def __init__(
        self,
        adapter: BaseAdapter,
        sink: Optional[ParquetSink] = None,
        strict_validation: bool = False,
        on_progress: Optional[Callable[[int, int], None]] = None
    ):
        """
        Initialize the pipeline.
        
        Args:
            adapter: Source adapter
            sink: Target sink (defaults to ParquetSink)
            strict_validation: If True, fail on validation errors
            on_progress: Callback for progress updates (rows_processed, total_rows)
        """
        self.adapter = adapter
        self.sink = sink or ParquetSink()
        self.normalizer = DataNormalizer()
        self.validator = DataValidator(strict=strict_validation)
        self.on_progress = on_progress
        
        # Statistics
        self.stats = {
            "chunks_processed": 0,
            "rows_read": 0,
            "rows_normalized": 0,
            "rows_validated": 0,
            "rows_written": 0,
            "validation_errors": [],
            "validation_warnings": [],
            "processing_time_seconds": 0
        }
    
    def run(self) -> Dict[str, Any]:
        """
        Execute the full ingestion pipeline.
        
        Returns:
            Dictionary with processing statistics
        """
        import time
        start_time = time.time()
        
        logger.info(f"Starting ingestion pipeline from {self.adapter.source_type}")
        
        try:
            for chunk in self.adapter.read_chunks():
                self._process_chunk(chunk)
                
                if self.on_progress:
                    self.on_progress(
                        self.stats["rows_written"],
                        self.stats["rows_read"]
                    )
            
            self.stats["processing_time_seconds"] = round(time.time() - start_time, 2)
            
            logger.info(
                f"Ingestion complete: {self.stats['rows_written']} rows written, "
                f"{len(self.stats['validation_errors'])} errors, "
                f"{len(self.stats['validation_warnings'])} warnings"
            )
            
            return self.stats
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            self.stats["error"] = str(e)
            raise
    
    def _process_chunk(self, chunk: pd.DataFrame) -> None:
        """Process a single chunk through the pipeline."""
        self.stats["chunks_processed"] += 1
        self.stats["rows_read"] += len(chunk)
        
        # Layer 2: Normalize
        normalized = self.normalizer.normalize(chunk)
        self.stats["rows_normalized"] += len(normalized)
        
        # Enforce schema constraints
        normalized, violations = SchemaEnforcer.enforce_constraints(normalized)
        for violation in violations:
            self.stats["validation_warnings"].append({
                "chunk": self.stats["chunks_processed"],
                "message": violation
            })
        
        # Layer 3: Validate
        validated, validation_result = self.validator.validate(normalized)
        self.stats["rows_validated"] += validation_result.valid_rows
        
        # Collect errors and warnings
        self.stats["validation_errors"].extend(validation_result.errors)
        self.stats["validation_warnings"].extend(validation_result.warnings)
        
        # Layer 4: Write to Sink
        if not validated.empty:
            rows_written = self.sink.write(validated)
            self.stats["rows_written"] += rows_written


# Convenience function for one-shot ingestion
def ingest_file(
    file_path: str,
    output_dir: Optional[str] = None,
    strict: bool = False
) -> Dict[str, Any]:
    """
    Convenience function to ingest a file through the full pipeline.
    
    Args:
        file_path: Path to CSV or Excel file
        output_dir: Output directory (defaults to data/campaigns)
        strict: If True, fail on validation errors
    
    Returns:
        Processing statistics
    """
    adapter = get_adapter(file_path)
    sink = ParquetSink(Path(output_dir) if output_dir else DEFAULT_CAMPAIGNS_DIR)
    
    pipeline = IngestionPipeline(
        adapter=adapter,
        sink=sink,
        strict_validation=strict
    )
    
    return pipeline.run()


def ingest_dataframe(
    df: pd.DataFrame,
    output_dir: Optional[str] = None,
    strict: bool = False
) -> Dict[str, Any]:
    """
    Ingest a DataFrame through the pipeline.
    
    Args:
        df: Input DataFrame
        output_dir: Output directory
        strict: If True, fail on validation errors
    
    Returns:
        Processing statistics
    """
    # Normalize
    normalized = normalize_dataframe(df, strict_mode=False)
    
    # Validate
    validated, result = validate_dataframe(normalized, strict=strict)
    
    # Write
    sink = ParquetSink(Path(output_dir) if output_dir else DEFAULT_CAMPAIGNS_DIR)
    rows_written = sink.write(validated)
    
    return {
        "rows_read": len(df),
        "rows_normalized": len(normalized),
        "rows_validated": result.valid_rows,
        "rows_written": rows_written,
        "validation_errors": result.errors,
        "validation_warnings": result.warnings
    }
