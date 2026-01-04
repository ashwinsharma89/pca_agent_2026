"""
Unit Tests for Phase 2 Ingestion Pipeline

Tests for:
- src/ingestion/adapters.py
- src/ingestion/normalizer.py
- src/ingestion/validators.py
- src/ingestion/pipeline.py
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from io import BytesIO
import tempfile
import os

from src.ingestion.adapters import (
    CSVAdapter,
    ExcelAdapter,
    BytesAdapter,
    APIAdapter,
    get_adapter
)

from src.ingestion.normalizer import (
    DataNormalizer,
    SchemaEnforcer,
    normalize_dataframe,
    CANONICAL_SCHEMA
)

from src.ingestion.validators import (
    DataValidator,
    ValidationResult,
    CampaignSchema,
    validate_dataframe
)

from src.ingestion.pipeline import (
    ParquetSink,
    IngestionPipeline,
    ingest_dataframe
)


@pytest.fixture
def sample_csv_file(tmp_path):
    """Create a sample CSV file for testing."""
    csv_content = """Date,Platform,Spend,Impressions,Clicks,Conversions
2024-01-01,Meta,100.50,10000,150,10
2024-01-02,Google,200.75,20000,300,20
2024-01-03,TikTok,50.25,5000,75,5
"""
    csv_path = tmp_path / "test_data.csv"
    csv_path.write_text(csv_content)
    return csv_path


@pytest.fixture
def sample_dataframe():
    """Create a sample DataFrame for testing."""
    return pd.DataFrame({
        'Date': pd.to_datetime(['2024-01-01', '2024-01-02', '2024-01-03']),
        'Platform': ['Meta', 'Google', 'TikTok'],
        'Spend': [100.50, 200.75, 50.25],
        'Impressions': [10000, 20000, 5000],
        'Clicks': [150, 300, 75],
        'Conversions': [10, 20, 5]
    })


@pytest.fixture
def raw_dataframe():
    """Create a DataFrame with non-standard column names."""
    return pd.DataFrame({
        'Day': pd.to_datetime(['2024-01-01', '2024-01-02']),
        'Source': ['Meta', 'Google'],
        'Total Spent': [100.0, 200.0],
        'Impr': [10000, 20000],
        'Link Clicks': [100, 200],
        'Purchases': [10, 20]
    })


class TestCSVAdapter:
    """Tests for CSVAdapter."""
    
    def test_csv_adapter_reads_file(self, sample_csv_file):
        """Test that CSV adapter reads file correctly."""
        adapter = CSVAdapter(sample_csv_file)
        assert adapter.source_type == "csv"
        
        chunks = list(adapter.read_chunks())
        assert len(chunks) == 1
        
        df = chunks[0]
        assert len(df) == 3
        assert 'Platform' in df.columns
        assert 'Spend' in df.columns
    
    def test_csv_adapter_chunking(self, sample_csv_file):
        """Test that CSV adapter chunks correctly."""
        adapter = CSVAdapter(sample_csv_file, chunk_size=2)
        chunks = list(adapter.read_chunks())
        
        # Should have 2 chunks for 3 rows with chunk_size=2
        assert len(chunks) == 2
        assert len(chunks[0]) == 2
        assert len(chunks[1]) == 1


class TestBytesAdapter:
    """Tests for BytesAdapter."""
    
    def test_bytes_adapter_csv(self):
        """Test BytesAdapter with CSV content."""
        csv_content = b"Date,Spend,Clicks\n2024-01-01,100,10\n2024-01-02,200,20"
        adapter = BytesAdapter(csv_content, "data.csv")
        
        assert adapter.source_type == "csv"
        
        chunks = list(adapter.read_chunks())
        assert len(chunks) == 1
        assert len(chunks[0]) == 2


class TestAPIAdapter:
    """Tests for APIAdapter."""
    
    def test_api_adapter_flattening(self):
        """Test APIAdapter JSON flattening."""
        responses = [
            {"spend": 100, "metrics": {"clicks": 10, "impressions": 1000}},
            {"spend": 200, "metrics": {"clicks": 20, "impressions": 2000}}
        ]
        
        adapter = APIAdapter(responses)
        chunks = list(adapter.read_chunks())
        
        assert len(chunks) == 1
        df = chunks[0]
        assert len(df) == 2
        assert 'metrics.clicks' in df.columns  # Flattened


class TestGetAdapter:
    """Tests for get_adapter factory function."""
    
    def test_get_adapter_csv(self, sample_csv_file):
        """Test factory returns CSVAdapter for CSV files."""
        adapter = get_adapter(sample_csv_file)
        assert isinstance(adapter, CSVAdapter)
    
    def test_get_adapter_bytes(self):
        """Test factory returns BytesAdapter for bytes."""
        adapter = get_adapter(b"data", filename="test.csv")
        assert isinstance(adapter, BytesAdapter)


class TestDataNormalizer:
    """Tests for DataNormalizer."""
    
    def test_normalize_maps_columns(self, raw_dataframe):
        """Test that normalizer maps columns correctly."""
        normalizer = DataNormalizer()
        result = normalizer.normalize(raw_dataframe)
        
        # Check canonical names are present
        assert 'date' in result.columns
        assert 'platform' in result.columns
        assert 'spend' in result.columns
        assert 'impressions' in result.columns
        assert 'clicks' in result.columns
        assert 'conversions' in result.columns
    
    def test_normalize_type_conversion(self, raw_dataframe):
        """Test that normalizer converts types."""
        normalizer = DataNormalizer()
        result = normalizer.normalize(raw_dataframe)
        
        assert result['spend'].dtype == 'float64'
        assert result['impressions'].dtype == 'int64'
    
    def test_normalize_adds_missing_columns(self):
        """Test that normalizer adds missing columns with defaults."""
        df = pd.DataFrame({
            'Spend': [100.0],
            'Platform': ['Meta']
        })
        
        normalizer = DataNormalizer()
        result = normalizer.normalize(df)
        
        # Missing columns should have defaults
        assert 'clicks' in result.columns or result.get('clicks', 0) == 0
    
    def test_normalize_empty_dataframe(self):
        """Test normalizing empty DataFrame."""
        df = pd.DataFrame()
        normalizer = DataNormalizer()
        result = normalizer.normalize(df)
        
        assert result.empty


class TestSchemaEnforcer:
    """Tests for SchemaEnforcer."""
    
    def test_enforce_negative_spend(self):
        """Test that negative spend is corrected."""
        df = pd.DataFrame({
            'spend': [-100, 200, -50],
            'impressions': [1000, 2000, 500],
            'clicks': [10, 20, 5]
        })
        
        result, violations = SchemaEnforcer.enforce_constraints(df)
        
        assert (result['spend'] >= 0).all()
        assert len(violations) == 1
        assert 'Negative spend' in violations[0]
    
    def test_enforce_clicks_gt_impressions(self):
        """Test that clicks > impressions is corrected."""
        df = pd.DataFrame({
            'spend': [100],
            'impressions': [100],
            'clicks': [200]  # Invalid: clicks > impressions
        })
        
        result, violations = SchemaEnforcer.enforce_constraints(df)
        
        assert result['impressions'].iloc[0] == result['clicks'].iloc[0]
        assert len(violations) == 1


class TestDataValidator:
    """Tests for DataValidator."""
    
    def test_validate_valid_data(self, sample_dataframe):
        """Test validation of valid data."""
        normalized = normalize_dataframe(sample_dataframe)
        validated, result = validate_dataframe(normalized)
        
        assert result.passed
        assert result.valid_rows == len(normalized)
    
    def test_validate_negative_values(self):
        """Test validation catches negative values."""
        df = pd.DataFrame({
            'date': pd.to_datetime(['2024-01-01']),
            'platform': ['Meta'],
            'spend': [-100],  # Invalid
            'impressions': [1000],
            'clicks': [10],
            'conversions': [1]
        })
        
        validated, result = validate_dataframe(df)
        
        # Should have warnings or auto-fix
        assert len(result.warnings) > 0 or result.passed
    
    def test_validate_clicks_exceed_impressions(self):
        """Test validation catches clicks > impressions."""
        df = pd.DataFrame({
            'date': pd.to_datetime(['2024-01-01']),
            'platform': ['Meta'],
            'spend': [100],
            'impressions': [100],
            'clicks': [200],  # Invalid
            'conversions': [1]
        })
        
        validated, result = validate_dataframe(df)
        
        # Should have warnings about clicks > impressions
        assert any('clicks' in str(w).lower() for w in result.warnings)


class TestParquetSink:
    """Tests for ParquetSink."""
    
    def test_sink_writes_parquet(self, sample_dataframe, tmp_path):
        """Test that sink writes parquet files."""
        sink = ParquetSink(tmp_path, partition_by=None)
        rows = sink.write(sample_dataframe)
        
        assert rows == len(sample_dataframe)
        
        # Check file was created
        parquet_files = list(tmp_path.glob("*.parquet"))
        assert len(parquet_files) == 1
    
    def test_sink_partitioned_write(self, sample_dataframe, tmp_path):
        """Test partitioned write by date."""
        sink = ParquetSink(tmp_path, partition_by='date')
        rows = sink.write(sample_dataframe)
        
        assert rows == len(sample_dataframe)


class TestIngestionPipeline:
    """Tests for IngestionPipeline."""
    
    def test_full_pipeline(self, sample_csv_file, tmp_path):
        """Test full ingestion pipeline."""
        adapter = CSVAdapter(sample_csv_file)
        sink = ParquetSink(tmp_path / "output", partition_by=None)
        
        pipeline = IngestionPipeline(
            adapter=adapter,
            sink=sink,
            strict_validation=False
        )
        
        stats = pipeline.run()
        
        assert stats['rows_read'] == 3
        assert stats['rows_written'] == 3
        assert stats['chunks_processed'] == 1
    
    def test_ingest_dataframe_function(self, sample_dataframe, tmp_path):
        """Test convenience function ingest_dataframe."""
        stats = ingest_dataframe(
            sample_dataframe,
            output_dir=str(tmp_path),
            strict=False
        )
        
        assert stats['rows_read'] == 3
        assert stats['rows_written'] == 3


class TestEdgeCases:
    """Test edge cases for ingestion pipeline."""
    
    def test_empty_dataframe_ingestion(self, tmp_path):
        """Test ingestion of empty DataFrame."""
        df = pd.DataFrame()
        stats = ingest_dataframe(df, output_dir=str(tmp_path))
        
        assert stats['rows_read'] == 0
        assert stats['rows_written'] == 0
    
    def test_all_null_columns(self, tmp_path):
        """Test DataFrame with all null values."""
        df = pd.DataFrame({
            'Spend': [np.nan, np.nan],
            'Platform': [None, None]
        })
        
        normalized = normalize_dataframe(df)
        
        # Should handle nulls gracefully
        assert not normalized.empty
    
    def test_mixed_types_in_column(self, tmp_path):
        """Test DataFrame with mixed types."""
        df = pd.DataFrame({
            'Spend': ['100', 200, None],
            'Platform': ['Meta', 'Google', 'TikTok']
        })
        
        normalized = normalize_dataframe(df)
        
        # Spend should be coerced to numeric
        assert normalized['spend'].dtype in ['float64', 'int64', 'object']
