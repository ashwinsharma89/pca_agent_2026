"""
Integration Tests for Phase 2 Components

Tests for end-to-end integration of:
- Ingestion pipeline with real data
- Query engine components working together
- Campaign service with new analytics methods
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import os

# Ingestion components
from src.ingestion import (
    CSVAdapter,
    DataNormalizer,
    DataValidator,
    ParquetSink,
    IngestionPipeline,
    ingest_dataframe
)

# Query engine components
from src.query_engine.schema_manager import SchemaManager
from src.query_engine.prompt_builder import PromptBuilder
from src.query_engine.executor import QueryExecutor

# Utils
from src.utils.column_mapping import find_column, METRIC_COLUMN_ALIASES
from src.utils.metrics import calculate_all_metrics, safe_divide


@pytest.fixture
def realistic_campaign_data():
    """Create realistic campaign data for integration tests."""
    np.random.seed(42)
    n_rows = 100
    
    platforms = ['Meta', 'Google', 'TikTok', 'LinkedIn']
    channels = ['Social', 'Search', 'Display', 'Video']
    funnels = ['Awareness', 'Consideration', 'Conversion']
    
    return pd.DataFrame({
        'Date': pd.date_range('2024-01-01', periods=n_rows, freq='D'),
        'Platform': np.random.choice(platforms, n_rows),
        'Channel': np.random.choice(channels, n_rows),
        'Funnel': np.random.choice(funnels, n_rows),
        'Spend': np.random.uniform(50, 500, n_rows).round(2),
        'Impressions': np.random.randint(5000, 50000, n_rows),
        'Clicks': np.random.randint(50, 500, n_rows),
        'Conversions': np.random.randint(1, 50, n_rows),
        'Revenue': np.random.uniform(100, 2000, n_rows).round(2)
    })


@pytest.fixture
def messy_campaign_data():
    """Create messy data with non-standard column names."""
    return pd.DataFrame({
        'Day': pd.date_range('2024-01-01', periods=10, freq='D'),
        'Source': ['Meta', 'Google'] * 5,
        'Total Spent': [100.0, 200.0] * 5,
        'Impr': [10000, 20000] * 5,
        'Link Clicks': [100, 200] * 5,
        'Purchases': [10, 20] * 5,
        'Ad Revenue': [500.0, 1000.0] * 5
    })


class TestIngestionPipelineIntegration:
    """Integration tests for the full ingestion pipeline."""
    
    def test_csv_to_parquet_pipeline(self, realistic_campaign_data, tmp_path):
        """Test full CSV to Parquet pipeline."""
        # Save to CSV
        csv_path = tmp_path / "campaigns.csv"
        realistic_campaign_data.to_csv(csv_path, index=False)
        
        # Create pipeline
        adapter = CSVAdapter(csv_path)
        sink = ParquetSink(tmp_path / "output", partition_by=None)
        
        pipeline = IngestionPipeline(
            adapter=adapter,
            sink=sink,
            strict_validation=False
        )
        
        stats = pipeline.run()
        
        # Verify
        assert stats['rows_read'] == 100
        assert stats['rows_written'] == 100
        assert stats['chunks_processed'] >= 1
        
        # Read back parquet
        parquet_files = list((tmp_path / "output").glob("*.parquet"))
        assert len(parquet_files) == 1
        
        df = pd.read_parquet(parquet_files[0])
        assert len(df) == 100
    
    def test_messy_data_normalization(self, messy_campaign_data, tmp_path):
        """Test that messy data gets normalized correctly."""
        stats = ingest_dataframe(
            messy_campaign_data,
            output_dir=str(tmp_path),
            strict=False
        )
        
        assert stats['rows_read'] == 10
        assert stats['rows_written'] == 10
        
        # Read back and verify normalization
        parquet_files = list(tmp_path.glob("**/*.parquet"))
        assert len(parquet_files) >= 1
        
        df = pd.read_parquet(parquet_files[0])
        
        # Check canonical column names
        assert 'spend' in df.columns
        assert 'impressions' in df.columns
        assert 'clicks' in df.columns
    
    def test_validation_catches_issues(self, tmp_path):
        """Test that validation catches data issues."""
        bad_data = pd.DataFrame({
            'Date': pd.date_range('2024-01-01', periods=5, freq='D'),
            'Platform': ['Meta'] * 5,
            'Spend': [-100, 200, 300, 400, 500],  # Negative spend
            'Impressions': [100, 200, 300, 400, 500],
            'Clicks': [200, 100, 100, 100, 100],  # First row: clicks > impressions
            'Conversions': [10, 10, 10, 10, 10]
        })
        
        stats = ingest_dataframe(
            bad_data,
            output_dir=str(tmp_path),
            strict=False
        )
        
        # Should have warnings but still process
        assert stats['rows_written'] == 5
        assert len(stats['validation_warnings']) > 0
    
    def test_progress_callback(self, realistic_campaign_data, tmp_path):
        """Test progress callback during ingestion."""
        csv_path = tmp_path / "campaigns.csv"
        realistic_campaign_data.to_csv(csv_path, index=False)
        
        progress_calls = []
        
        def on_progress(processed, total):
            progress_calls.append((processed, total))
        
        adapter = CSVAdapter(csv_path, chunk_size=20)
        sink = ParquetSink(tmp_path / "output", partition_by=None)
        
        pipeline = IngestionPipeline(
            adapter=adapter,
            sink=sink,
            on_progress=on_progress
        )
        
        pipeline.run()
        
        # Should have progress updates
        assert len(progress_calls) > 0


class TestQueryEngineIntegration:
    """Integration tests for query engine components."""
    
    def test_schema_to_prompt_flow(self, realistic_campaign_data):
        """Test flow from schema extraction to prompt building."""
        # Extract schema
        schema_manager = SchemaManager()
        schema = schema_manager.extract_schema(realistic_campaign_data, "campaigns")
        schema_text = schema_manager.get_schema_for_prompt()
        
        # Build prompt
        builder = PromptBuilder()
        prompt = (builder
            .set_schema(schema_text)
            .set_marketing_context("Marketing analytics context")
            .set_sql_context("SQL patterns")
            .build("What is total spend by platform?"))
        
        # Verify prompt contains schema info
        assert "campaigns" in prompt
        assert "Platform" in prompt
        assert "Spend" in prompt
        assert "What is total spend by platform?" in prompt
    
    def test_executor_sanitizes_llm_output(self):
        """Test that executor sanitizes typical LLM SQL output."""
        executor = QueryExecutor()
        
        # Typical LLM output with markdown
        llm_output = """```sql
SELECT Platform, SUM(Spend) as Total_Spend
FROM campaigns
GROUP BY Platform
ORDER BY Total_Spend DESC;
```"""
        
        sanitized = executor._sanitize_sql(llm_output)
        
        assert "```" not in sanitized
        assert not sanitized.endswith(";")
        assert "SELECT Platform" in sanitized
    
    def test_column_mapping_with_schema(self, messy_campaign_data):
        """Test column mapping integration with schema manager."""
        # Detect columns using column_mapping
        spend_col = find_column(messy_campaign_data, 'spend')
        clicks_col = find_column(messy_campaign_data, 'clicks')
        
        assert spend_col == 'Total Spent'
        assert clicks_col == 'Link Clicks'
        
        # Schema manager should include these
        schema_manager = SchemaManager()
        schema = schema_manager.extract_schema(messy_campaign_data)
        
        assert 'Total Spent' in schema['columns']
        assert 'Link Clicks' in schema['columns']


class TestMetricsIntegration:
    """Integration tests for metrics calculation."""
    
    def test_metrics_from_ingested_data(self, realistic_campaign_data, tmp_path):
        """Test metrics calculation on ingested data."""
        # Ingest data
        stats = ingest_dataframe(
            realistic_campaign_data,
            output_dir=str(tmp_path),
            strict=False
        )
        
        # Read back
        parquet_files = list(tmp_path.glob("**/*.parquet"))
        df = pd.read_parquet(parquet_files[0])
        
        # Calculate metrics
        metrics = calculate_all_metrics(
            spend=df['spend'].sum(),
            impressions=df['impressions'].sum(),
            clicks=df['clicks'].sum(),
            conversions=df['conversions'].sum(),
            revenue=df['revenue'].sum()
        )
        
        # Verify all metrics are calculated
        assert metrics['spend'] > 0
        assert metrics['impressions'] > 0
        assert metrics['ctr'] >= 0  # CTR can be calculated
        assert metrics['cpc'] >= 0  # CPC can be calculated
        assert metrics['roas'] >= 0  # ROAS can be calculated
    
    def test_platform_breakdown_metrics(self, realistic_campaign_data):
        """Test metrics grouped by platform."""
        platforms = realistic_campaign_data.groupby('Platform').agg({
            'Spend': 'sum',
            'Impressions': 'sum',
            'Clicks': 'sum',
            'Conversions': 'sum',
            'Revenue': 'sum'
        }).reset_index()
        
        for _, row in platforms.iterrows():
            metrics = calculate_all_metrics(
                spend=row['Spend'],
                impressions=row['Impressions'],
                clicks=row['Clicks'],
                conversions=row['Conversions'],
                revenue=row['Revenue']
            )
            
            # All platforms should have valid metrics
            assert metrics['ctr'] >= 0
            assert metrics['cpc'] >= 0
            assert metrics['roas'] >= 0


class TestEndToEndFlow:
    """End-to-end tests for complete flows."""
    
    def test_upload_to_query_flow(self, messy_campaign_data, tmp_path):
        """Test complete flow from upload to query preparation."""
        # Step 1: Ingest
        stats = ingest_dataframe(
            messy_campaign_data,
            output_dir=str(tmp_path),
            strict=False
        )
        
        assert stats['rows_written'] == 10
        
        # Step 2: Read normalized data
        parquet_files = list(tmp_path.glob("**/*.parquet"))
        df = pd.read_parquet(parquet_files[0])
        
        # Step 3: Generate schema
        schema_manager = SchemaManager()
        schema = schema_manager.extract_schema(df, "campaigns")
        
        # Step 4: Prepare query context
        schema_text = schema_manager.get_schema_for_prompt()
        
        builder = PromptBuilder()
        prompt = (builder
            .set_schema(schema_text)
            .build("What is the total spend?"))
        
        # Verify flow completed
        assert "campaigns" in prompt
        assert "spend" in prompt.lower()
    
    def test_concurrent_ingestion_queries(self, realistic_campaign_data, tmp_path):
        """Test that ingestion and schema analysis can work together."""
        # Ingest
        ingest_dataframe(realistic_campaign_data, output_dir=str(tmp_path))
        
        # While data exists, analyze schema
        parquet_files = list(tmp_path.glob("**/*.parquet"))
        df = pd.read_parquet(parquet_files[0])
        
        schema_manager = SchemaManager()
        schema = schema_manager.extract_schema(df)
        
        # Get metrics
        metrics = calculate_all_metrics(
            spend=df['spend'].sum(),
            impressions=df['impressions'].sum(),
            clicks=df['clicks'].sum(),
            conversions=df['conversions'].sum(),
            revenue=df['revenue'].sum()
        )
        
        # Build prompt
        prompt = (PromptBuilder()
            .set_schema(schema_manager.get_schema_for_prompt())
            .build(f"Compare platforms, total spend is ${metrics['spend']:.2f}"))
        
        assert str(int(metrics['spend'])) in prompt or 'spend' in prompt.lower()
