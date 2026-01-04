"""
Unit Tests for Phase 2 Query Engine Components

Tests for:
- src/query_engine/schema_manager.py
- src/query_engine/prompt_builder.py
- src/query_engine/executor.py
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock

from src.query_engine.schema_manager import (
    SchemaManager,
    get_schema_manager
)

from src.query_engine.prompt_builder import (
    PromptBuilder,
    get_prompt_builder,
    SQL_RULES_TEMPLATE
)

from src.query_engine.executor import (
    QueryExecutor,
    get_query_executor
)


@pytest.fixture
def sample_dataframe():
    """Create sample DataFrame for schema tests."""
    return pd.DataFrame({
        'Date': pd.to_datetime(['2024-01-01', '2024-01-02']),
        'Platform': ['Meta', 'Google'],
        'Channel': ['Social', 'Search'],
        'Spend': [100.0, 200.0],
        'Impressions': [10000, 20000],
        'Clicks': [100, 200],
        'Conversions': [10, 20],
        'Revenue': [500.0, 1000.0]
    })


@pytest.fixture
def mock_connection():
    """Create a mock DuckDB connection."""
    conn = MagicMock()
    return conn


class TestSchemaManager:
    """Tests for SchemaManager."""
    
    def test_extract_schema(self, sample_dataframe):
        """Test schema extraction from DataFrame."""
        manager = SchemaManager()
        schema = manager.extract_schema(sample_dataframe, "campaigns")
        
        assert schema['table_name'] == "campaigns"
        assert 'Date' in schema['columns']
        assert 'Platform' in schema['columns']
        assert 'Spend' in schema['columns']
        assert schema['row_count'] == 2
    
    def test_get_schema_for_prompt(self, sample_dataframe):
        """Test getting formatted schema for prompt."""
        manager = SchemaManager()
        manager.extract_schema(sample_dataframe, "campaigns")
        
        prompt_text = manager.get_schema_for_prompt()
        
        assert "Table: campaigns" in prompt_text
        assert "Columns:" in prompt_text
        assert "Date" in prompt_text
        assert "Platform" in prompt_text
        assert "Spend" in prompt_text
    
    def test_get_schema_without_extraction(self):
        """Test that getting schema before extraction raises error."""
        manager = SchemaManager()
        
        with pytest.raises(ValueError):
            manager.get_schema_for_prompt()
    
    def test_get_date_column(self, sample_dataframe):
        """Test date column detection."""
        manager = SchemaManager()
        manager.extract_schema(sample_dataframe)
        
        date_col = manager.get_date_column()
        assert date_col == 'Date'
    
    def test_get_metric_columns(self, sample_dataframe):
        """Test metric column detection."""
        manager = SchemaManager()
        manager.extract_schema(sample_dataframe)
        
        metrics = manager.get_metric_columns()
        assert 'Spend' in metrics
        assert 'Impressions' in metrics
        assert 'Clicks' in metrics
        assert 'Revenue' in metrics
    
    def test_get_dimension_columns(self, sample_dataframe):
        """Test dimension column detection."""
        manager = SchemaManager()
        manager.extract_schema(sample_dataframe)
        
        dimensions = manager.get_dimension_columns()
        assert 'Platform' in dimensions
        assert 'Channel' in dimensions
    
    def test_validate_column_exists(self, sample_dataframe):
        """Test column validation for existing column."""
        manager = SchemaManager()
        manager.extract_schema(sample_dataframe)
        
        exists, actual = manager.validate_column('Platform')
        assert exists
        assert actual == 'Platform'
    
    def test_validate_column_case_insensitive(self, sample_dataframe):
        """Test case-insensitive column validation."""
        manager = SchemaManager()
        manager.extract_schema(sample_dataframe)
        
        exists, actual = manager.validate_column('platform')
        assert exists
        assert actual == 'Platform'
    
    def test_validate_column_not_exists(self, sample_dataframe):
        """Test column validation for non-existing column."""
        manager = SchemaManager()
        manager.extract_schema(sample_dataframe)
        
        exists, actual = manager.validate_column('NonExistent')
        assert not exists
        assert actual is None


class TestPromptBuilder:
    """Tests for PromptBuilder."""
    
    def test_build_basic_prompt(self):
        """Test building a basic prompt."""
        builder = get_prompt_builder()
        
        prompt = (builder
            .set_schema("Table: campaigns\nColumns: Spend, Clicks")
            .set_marketing_context("Marketing context here")
            .set_sql_context("SQL patterns here")
            .build("What is total spend?"))
        
        assert "What is total spend?" in prompt
        assert "Table: campaigns" in prompt
        assert "Marketing context here" in prompt
        assert "SQL patterns here" in prompt
    
    def test_prompt_includes_sql_rules(self):
        """Test that prompt includes SQL rules template."""
        builder = get_prompt_builder()
        
        prompt = builder.set_schema("Test schema").build("Test question")
        
        # Check for critical rules
        assert "NULLIF" in prompt
        assert "SUM" in prompt
        assert "CTR" in prompt
    
    def test_set_query_analysis(self):
        """Test setting query analysis hints."""
        builder = get_prompt_builder()
        
        # Mock entities object
        entities = Mock()
        entities.group_by = ['platform']
        entities.granularity = 'daily'
        entities.metrics = ['spend', 'clicks']
        entities.time_period = 'last 30 days'
        entities.limit = 10
        entities.order_by = 'spend DESC'
        
        prompt = (builder
            .set_schema("Test schema")
            .set_query_analysis(
                intent="aggregation",
                complexity="medium",
                entities=entities
            )
            .build("Show spend by platform"))
        
        assert "AGGREGATION" in prompt
        assert "MEDIUM" in prompt
        assert "GROUP BY" in prompt
        assert "Platform" in prompt
    
    def test_build_correction_prompt(self):
        """Test building SQL correction prompt."""
        builder = get_prompt_builder()
        
        prompt = builder.build_correction_prompt(
            original_sql="SELECT AVG(CTR) FROM campaigns",
            failed_rules=["Never use AVG() on rate columns"],
            question="What is average CTR?"
        )
        
        assert "SELECT AVG(CTR)" in prompt
        assert "AVG() on rate columns" in prompt
        assert "What is average CTR?" in prompt
    
    def test_build_answer_prompt(self):
        """Test building answer generation prompt."""
        builder = get_prompt_builder()
        
        prompt = builder.build_answer_prompt(
            question="What is total spend by platform?",
            results_summary="Meta: $100, Google: $200",
            sample_context="1000 rows analyzed"
        )
        
        assert "What is total spend by platform?" in prompt
        assert "Meta: $100" in prompt
        assert "1000 rows analyzed" in prompt


class TestQueryExecutor:
    """Tests for QueryExecutor."""
    
    def test_sanitize_sql_removes_markdown(self):
        """Test that sanitizer removes markdown code blocks."""
        executor = get_query_executor()
        
        dirty_sql = """```sql
SELECT * FROM campaigns
```"""
        
        clean_sql = executor._sanitize_sql(dirty_sql)
        
        assert "```" not in clean_sql
        assert "SELECT * FROM campaigns" in clean_sql
    
    def test_sanitize_sql_removes_semicolon(self):
        """Test that sanitizer removes trailing semicolon."""
        executor = get_query_executor()
        
        clean_sql = executor._sanitize_sql("SELECT * FROM campaigns;")
        
        assert not clean_sql.endswith(';')
    
    def test_sanitize_sql_fixes_interval(self):
        """Test that sanitizer fixes interval syntax."""
        executor = get_query_executor()
        
        dirty_sql = "SELECT * FROM t WHERE date >= INTERVAL '30' DAYS"
        clean_sql = executor._sanitize_sql(dirty_sql)
        
        assert "INTERVAL 30 DAY" in clean_sql
    
    def test_sanitize_sql_fixes_getdate(self):
        """Test that sanitizer replaces GETDATE() with CURRENT_DATE."""
        executor = get_query_executor()
        
        clean_sql = executor._sanitize_sql("SELECT GETDATE()")
        
        assert "CURRENT_DATE" in clean_sql
        assert "GETDATE" not in clean_sql
    
    def test_validate_query_structure_select(self):
        """Test query validation allows SELECT."""
        executor = get_query_executor()
        
        assert executor._validate_query_structure("SELECT * FROM t")
        assert executor._validate_query_structure("select * from t")
        assert executor._validate_query_structure("WITH cte AS () SELECT * FROM t")
    
    def test_validate_query_structure_blocks_dangerous(self):
        """Test query validation blocks dangerous queries."""
        executor = get_query_executor()
        
        assert not executor._validate_query_structure("DROP TABLE campaigns")
        assert not executor._validate_query_structure("DELETE FROM campaigns")
        assert not executor._validate_query_structure("TRUNCATE campaigns")
        assert not executor._validate_query_structure("INSERT INTO campaigns")
        assert not executor._validate_query_structure("UPDATE campaigns SET x=1")
    
    def test_format_results_dict(self):
        """Test result formatting as dict."""
        executor = get_query_executor()
        df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
        
        result = executor.format_results(df, "dict")
        
        assert 'a' in result
        assert 'b' in result
    
    def test_format_results_records(self):
        """Test result formatting as records."""
        executor = get_query_executor()
        df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
        
        result = executor.format_results(df, "records")
        
        assert len(result) == 2
        assert result[0] == {'a': 1, 'b': 3}
    
    def test_get_result_summary(self):
        """Test result summary generation."""
        executor = get_query_executor()
        df = pd.DataFrame({
            'spend': [100.0, 200.0, 300.0],
            'clicks': [10, 20, 30]
        })
        
        summary = executor.get_result_summary(df)
        
        assert summary['row_count'] == 3
        assert 'spend' in summary['columns']
        assert 'clicks' in summary['columns']
        assert 'numeric_summary' in summary
        assert summary['numeric_summary']['spend']['sum'] == 600.0
    
    def test_execute_no_connection(self):
        """Test execute fails gracefully without connection."""
        executor = get_query_executor()  # No connection
        
        result, error = executor.execute("SELECT * FROM t")
        
        assert result is None
        assert "No database connection" in error


class TestEdgeCases:
    """Test edge cases for query engine components."""
    
    def test_schema_with_special_column_names(self):
        """Test schema handling of special column names."""
        df = pd.DataFrame({
            'Date Range': ['2024-01-01'],
            'Ad Type': ['Video'],
            'Device Type': ['Mobile']
        })
        
        manager = SchemaManager()
        schema = manager.extract_schema(df)
        
        assert 'Date Range' in schema['columns']
    
    def test_prompt_with_empty_entities(self):
        """Test prompt building with empty entities."""
        builder = get_prompt_builder()
        
        entities = Mock()
        entities.group_by = []
        entities.granularity = None
        entities.metrics = []
        entities.time_period = None
        entities.limit = None
        entities.order_by = None
        
        prompt = (builder
            .set_schema("Test")
            .set_query_analysis("filter", "simple", entities)
            .build("test"))
        
        assert "FILTER" in prompt
        assert "SIMPLE" in prompt
    
    def test_executor_empty_dataframe(self):
        """Test result formatting with empty DataFrame."""
        executor = get_query_executor()
        df = pd.DataFrame()
        
        result = executor.format_results(df, "records")
        assert result is None
        
        summary = executor.get_result_summary(df)
        assert summary['row_count'] == 0
