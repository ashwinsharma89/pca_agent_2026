"""
Metrics Calculation Utilities

Provides safe, reusable functions for calculating marketing metrics:
- CTR (Click-Through Rate)
- CPC (Cost Per Click)
- CPM (Cost Per Mille)
- CPA (Cost Per Acquisition)
- ROAS (Return On Ad Spend)
- CVR (Conversion Rate)

All functions handle NaN, Inf, and division by zero gracefully.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Union


def safe_divide(
    numerator: Union[float, int], 
    denominator: Union[float, int], 
    default: float = 0.0
) -> float:
    """
    Safe division that handles division by zero, NaN, and Inf.
    
    Args:
        numerator: The numerator
        denominator: The denominator
        default: Value to return if division is invalid
    
    Returns:
        Result of division or default value
        
    Example:
        >>> safe_divide(100, 0)
        0.0
        >>> safe_divide(100, 50)
        2.0
    """
    if denominator == 0 or pd.isna(denominator) or pd.isna(numerator):
        return default
    
    result = numerator / denominator
    
    if np.isinf(result) or np.isnan(result):
        return default
    
    return float(result)


def safe_numeric(val: Any, default: float = 0.0) -> float:
    """
    Convert value to float, handling NaN/Inf/None.
    
    Args:
        val: Value to convert
        default: Default value if conversion fails
    
    Returns:
        Float value or default
    """
    if val is None:
        return default
    
    try:
        result = float(val)
        if np.isnan(result) or np.isinf(result):
            return default
        return result
    except (ValueError, TypeError):
        return default


def calculate_ctr(clicks: float, impressions: float) -> float:
    """
    Calculate Click-Through Rate.
    
    CTR = (Clicks / Impressions) * 100
    
    Returns:
        CTR as percentage (e.g., 2.5 for 2.5%)
    """
    return safe_divide(clicks, impressions) * 100


def calculate_cpc(spend: float, clicks: float) -> float:
    """
    Calculate Cost Per Click.
    
    CPC = Spend / Clicks
    
    Returns:
        CPC in currency units
    """
    return safe_divide(spend, clicks)


def calculate_cpm(spend: float, impressions: float) -> float:
    """
    Calculate Cost Per Mille (per 1000 impressions).
    
    CPM = (Spend / Impressions) * 1000
    
    Returns:
        CPM in currency units
    """
    return safe_divide(spend, impressions) * 1000


def calculate_cpa(spend: float, conversions: float) -> float:
    """
    Calculate Cost Per Acquisition.
    
    CPA = Spend / Conversions
    
    Returns:
        CPA in currency units
    """
    return safe_divide(spend, conversions)


def calculate_roas(revenue: float, spend: float) -> float:
    """
    Calculate Return On Ad Spend.
    
    ROAS = Revenue / Spend
    
    Returns:
        ROAS ratio (e.g., 3.5 means $3.50 revenue per $1 spent)
    """
    return safe_divide(revenue, spend)


def calculate_cvr(conversions: float, clicks: float) -> float:
    """
    Calculate Conversion Rate.
    
    CVR = (Conversions / Clicks) * 100
    
    Returns:
        CVR as percentage
    """
    return safe_divide(conversions, clicks) * 100


def calculate_all_metrics(
    spend: float = 0,
    impressions: float = 0,
    clicks: float = 0,
    conversions: float = 0,
    revenue: float = 0
) -> Dict[str, float]:
    """
    Calculate all derived metrics from base metrics.
    
    Args:
        spend: Total ad spend
        impressions: Total impressions
        clicks: Total clicks
        conversions: Total conversions
        revenue: Total revenue
    
    Returns:
        Dictionary with all metrics (base + derived)
    """
    return {
        # Base metrics
        'spend': safe_numeric(spend),
        'impressions': safe_numeric(impressions),
        'clicks': safe_numeric(clicks),
        'conversions': safe_numeric(conversions),
        'revenue': safe_numeric(revenue),
        # Derived metrics
        'ctr': round(calculate_ctr(clicks, impressions), 2),
        'cpc': round(calculate_cpc(spend, clicks), 2),
        'cpm': round(calculate_cpm(spend, impressions), 2),
        'cpa': round(calculate_cpa(spend, conversions), 2),
        'roas': round(calculate_roas(revenue, spend), 2),
        'cvr': round(calculate_cvr(conversions, clicks), 2),
    }


def calculate_metrics_from_df(
    df: pd.DataFrame,
    spend_col: str = 'spend',
    impressions_col: str = 'impressions',
    clicks_col: str = 'clicks',
    conversions_col: str = 'conversions',
    revenue_col: str = 'revenue'
) -> Dict[str, float]:
    """
    Calculate all metrics from a DataFrame by summing columns.
    
    Args:
        df: pandas DataFrame
        *_col: Column names for each metric
    
    Returns:
        Dictionary with all metrics
    """
    def get_sum(col: str) -> float:
        if col in df.columns:
            return float(df[col].sum())
        return 0.0
    
    return calculate_all_metrics(
        spend=get_sum(spend_col),
        impressions=get_sum(impressions_col),
        clicks=get_sum(clicks_col),
        conversions=get_sum(conversions_col),
        revenue=get_sum(revenue_col)
    )


def calculate_percentage_change(current: float, previous: float) -> float:
    """
    Calculate percentage change between two values.
    
    Args:
        current: Current period value
        previous: Previous period value
    
    Returns:
        Percentage change (e.g., 25.0 for 25% increase)
    """
    return safe_divide(current - previous, abs(previous)) * 100


def format_currency(value: float, decimals: int = 2) -> str:
    """
    Format value as currency string.
    
    Args:
        value: Numeric value
        decimals: Decimal places to show
    
    Returns:
        Formatted string (e.g., "$1.5M", "$500K", "$99.50")
    """
    if value >= 1_000_000:
        return f"${value/1_000_000:.{max(0, decimals-1)}f}M"
    elif value >= 1_000:
        return f"${value/1_000:.{max(0, decimals-1)}f}K"
    return f"${value:.{decimals}f}"


def format_number(value: float, decimals: int = 1) -> str:
    """
    Format large numbers with K/M suffix.
    
    Args:
        value: Numeric value
        decimals: Decimal places to show
    
    Returns:
        Formatted string (e.g., "1.5M", "500K", "99")
    """
    if value >= 1_000_000:
        return f"{value/1_000_000:.{decimals}f}M"
    elif value >= 1_000:
        return f"{value/1_000:.{decimals}f}K"
    return f"{value:.0f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    Format value as percentage string.
    
    Args:
        value: Percentage value (e.g., 25.5 for 25.5%)
        decimals: Decimal places to show
    
    Returns:
        Formatted string (e.g., "25.50%")
    """
    return f"{value:.{decimals}f}%"
