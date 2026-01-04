"""
Unified Ingestion Package

Provides a clean pipeline for data ingestion:
    Adapter -> Normalizer -> Validator -> Sink

Usage:
    from src.ingestion import ingest_file, ingest_dataframe, IngestionPipeline
    
    # Simple file ingestion
    stats = ingest_file("data.csv")
    
    # DataFrame ingestion
    stats = ingest_dataframe(df)
    
    # Custom pipeline
    from src.ingestion import CSVAdapter, ParquetSink, IngestionPipeline
    
    pipeline = IngestionPipeline(
        adapter=CSVAdapter("data.csv"),
        sink=ParquetSink(Path("output")),
        strict_validation=True
    )
    stats = pipeline.run()
"""

from .adapters import (
    BaseAdapter,
    CSVAdapter,
    ExcelAdapter,
    APIAdapter,
    DatabaseAdapter,
    BytesAdapter,
    get_adapter
)

from .normalizer import (
    DataNormalizer,
    SchemaEnforcer,
    normalize_dataframe,
    CANONICAL_SCHEMA
)

from .validators import (
    DataValidator,
    ValidationResult,
    CampaignSchema,
    validate_dataframe
)

from .pipeline import (
    ParquetSink,
    IngestionPipeline,
    ingest_file,
    ingest_dataframe
)


__all__ = [
    # Adapters
    'BaseAdapter',
    'CSVAdapter',
    'ExcelAdapter',
    'APIAdapter',
    'DatabaseAdapter',
    'BytesAdapter',
    'get_adapter',
    
    # Normalizer
    'DataNormalizer',
    'SchemaEnforcer',
    'normalize_dataframe',
    'CANONICAL_SCHEMA',
    
    # Validators
    'DataValidator',
    'ValidationResult',
    'CampaignSchema',
    'validate_dataframe',
    
    # Pipeline
    'ParquetSink',
    'IngestionPipeline',
    'ingest_file',
    'ingest_dataframe',
]
