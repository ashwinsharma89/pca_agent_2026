"""
Unit Tests for Phase 2 Utility Modules

Tests for:
- src/utils/column_mapping.py
- src/utils/metrics.py
"""

import pytest
import pandas as pd
import numpy as np

from src.utils.column_mapping import (
    find_column,
    consolidate_metric_column,
    get_available_columns,
    normalize_column_names,
    METRIC_COLUMN_ALIASES
)

from src.utils.metrics import (
    safe_divide,
    safe_numeric,
    calculate_ctr,
    calculate_cpc,
    calculate_cpm,
    calculate_cpa,
    calculate_roas,
    calculate_cvr,
    calculate_all_metrics,
    calculate_metrics_from_df,
    calculate_percentage_change,
    format_currency,
    format_number,
    format_percentage
)


class TestColumnMapping:
    """Tests for column_mapping.py"""
    
    def test_find_column_exact_match(self):
        """Test finding column with exact match."""
        df = pd.DataFrame({'Spend': [100], 'Clicks': [10]})
        assert find_column(df, 'spend') == 'Spend'
        assert find_column(df, 'clicks') == 'Clicks'
    
    def test_find_column_alias_match(self):
        """Test finding column with alias."""
        df = pd.DataFrame({'Total Spent': [100], 'Link Clicks': [10]})
        assert find_column(df, 'spend') == 'Total Spent'
        assert find_column(df, 'clicks') == 'Link Clicks'
    
    def test_find_column_case_insensitive(self):
        """Test case-insensitive matching."""
        df = pd.DataFrame({'SPEND': [100], 'clicks': [10]})
        assert find_column(df, 'spend') == 'SPEND'
        assert find_column(df, 'clicks') == 'clicks'
    
    def test_find_column_not_found(self):
        """Test column not found."""
        df = pd.DataFrame({'Revenue': [100]})
        assert find_column(df, 'spend') is None
    
    def test_consolidate_metric_column_single(self):
        """Test consolidation with single matching column."""
        df = pd.DataFrame({'Spend': [100, 200]})
        result = consolidate_metric_column(df, 'spend')
        assert result == 'Spend'
    
    def test_consolidate_metric_column_multiple(self):
        """Test consolidation with multiple matching columns."""
        df = pd.DataFrame({
            'Spend': [100, None],
            'Cost': [None, 200]
        })
        result = consolidate_metric_column(df, 'spend')
        assert result == 'Spend'
        # Should fill NaN with values from 'Cost'
        assert df['Spend'].iloc[1] == 200
    
    def test_get_available_columns(self):
        """Test getting all available columns."""
        df = pd.DataFrame({
            'Spend': [100],
            'Impressions': [1000],
            'Platform': ['Meta']
        })
        available = get_available_columns(df)
        assert available['spend'] == 'Spend'
        assert available['impressions'] == 'Impressions'
        assert available['platform'] == 'Platform'
        assert available['clicks'] is None
    
    def test_normalize_column_names(self):
        """Test column name normalization."""
        df = pd.DataFrame({
            'Total Spent': [100],
            'Impr': [1000],
            'Platform': ['Meta']
        })
        normalized = normalize_column_names(df)
        assert 'spend' in normalized.columns
        assert 'impressions' in normalized.columns


class TestMetrics:
    """Tests for metrics.py"""
    
    def test_safe_divide_normal(self):
        """Test normal division."""
        assert safe_divide(100, 50) == 2.0
        assert safe_divide(100, 4) == 25.0
    
    def test_safe_divide_zero(self):
        """Test division by zero."""
        assert safe_divide(100, 0) == 0.0
        assert safe_divide(100, 0, default=-1) == -1
    
    def test_safe_divide_nan(self):
        """Test division with NaN."""
        assert safe_divide(np.nan, 50) == 0.0
        assert safe_divide(100, np.nan) == 0.0
    
    def test_safe_numeric(self):
        """Test numeric conversion."""
        assert safe_numeric(100) == 100.0
        assert safe_numeric("50.5") == 50.5
        assert safe_numeric(None) == 0.0
        assert safe_numeric("invalid") == 0.0
        assert safe_numeric(np.nan) == 0.0
        assert safe_numeric(np.inf) == 0.0
    
    def test_calculate_ctr(self):
        """Test CTR calculation."""
        assert calculate_ctr(10, 1000) == 1.0  # 1%
        assert calculate_ctr(0, 1000) == 0.0
        assert calculate_ctr(10, 0) == 0.0  # Division by zero
    
    def test_calculate_cpc(self):
        """Test CPC calculation."""
        assert calculate_cpc(100, 50) == 2.0  # $2 per click
        assert calculate_cpc(100, 0) == 0.0
    
    def test_calculate_cpm(self):
        """Test CPM calculation."""
        assert calculate_cpm(100, 10000) == 10.0  # $10 per 1000 impressions
        assert calculate_cpm(100, 0) == 0.0
    
    def test_calculate_cpa(self):
        """Test CPA calculation."""
        assert calculate_cpa(100, 10) == 10.0  # $10 per conversion
        assert calculate_cpa(100, 0) == 0.0
    
    def test_calculate_roas(self):
        """Test ROAS calculation."""
        assert calculate_roas(500, 100) == 5.0  # 5x ROAS
        assert calculate_roas(0, 100) == 0.0
        assert calculate_roas(500, 0) == 0.0
    
    def test_calculate_cvr(self):
        """Test CVR calculation."""
        assert calculate_cvr(10, 100) == 10.0  # 10% conversion rate
        assert calculate_cvr(0, 100) == 0.0
    
    def test_calculate_all_metrics(self):
        """Test calculating all metrics at once."""
        metrics = calculate_all_metrics(
            spend=1000,
            impressions=100000,
            clicks=1000,
            conversions=50,
            revenue=5000
        )
        
        assert metrics['spend'] == 1000
        assert metrics['impressions'] == 100000
        assert metrics['clicks'] == 1000
        assert metrics['conversions'] == 50
        assert metrics['revenue'] == 5000
        
        # Derived metrics
        assert metrics['ctr'] == 1.0  # 1%
        assert metrics['cpc'] == 1.0  # $1
        assert metrics['cpm'] == 10.0  # $10
        assert metrics['cpa'] == 20.0  # $20
        assert metrics['roas'] == 5.0  # 5x
        assert metrics['cvr'] == 5.0  # 5%
    
    def test_calculate_metrics_from_df(self):
        """Test calculating metrics from DataFrame."""
        df = pd.DataFrame({
            'spend': [100, 200, 300],
            'impressions': [10000, 20000, 30000],
            'clicks': [100, 200, 300],
            'conversions': [10, 20, 30],
            'revenue': [500, 1000, 1500]
        })
        
        metrics = calculate_metrics_from_df(df)
        
        assert metrics['spend'] == 600
        assert metrics['impressions'] == 60000
        assert metrics['clicks'] == 600
        assert metrics['conversions'] == 60
        assert metrics['revenue'] == 3000
    
    def test_calculate_percentage_change(self):
        """Test percentage change calculation."""
        assert calculate_percentage_change(110, 100) == 10.0  # 10% increase
        assert calculate_percentage_change(90, 100) == -10.0  # 10% decrease
        assert calculate_percentage_change(100, 0) == 0.0  # Division by zero
    
    def test_format_currency(self):
        """Test currency formatting."""
        assert format_currency(1500000) == "$1.5M"
        assert format_currency(50000) == "$50.0K"
        assert format_currency(99.50) == "$99.50"
    
    def test_format_number(self):
        """Test number formatting."""
        assert format_number(1500000) == "1.5M"
        assert format_number(50000) == "50.0K"
        assert format_number(99) == "99"
    
    def test_format_percentage(self):
        """Test percentage formatting."""
        assert format_percentage(25.5) == "25.50%"
        assert format_percentage(0) == "0.00%"


class TestEdgeCases:
    """Test edge cases for utilities."""
    
    def test_empty_dataframe(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame()
        assert find_column(df, 'spend') is None
        # get_available_columns returns dict with all keys having None values
        available = get_available_columns(df)
        assert all(v is None for v in available.values())
    
    def test_all_nan_values(self):
        """Test with all NaN values."""
        metrics = calculate_all_metrics(
            spend=np.nan,
            impressions=np.nan,
            clicks=np.nan,
            conversions=np.nan,
            revenue=np.nan
        )
        assert metrics['spend'] == 0
        assert metrics['ctr'] == 0
    
    def test_very_large_numbers(self):
        """Test with very large numbers."""
        metrics = calculate_all_metrics(
            spend=1e12,  # 1 trillion
            impressions=1e15,
            clicks=1e10,
            conversions=1e8,
            revenue=5e12
        )
        assert metrics['roas'] == 5.0
