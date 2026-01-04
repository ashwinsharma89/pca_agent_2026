"""
Column Mapping Utilities

Central registry of column name variations and utilities for finding
columns in DataFrames using alias mapping.

This module is used by:
- Campaign Repository (data access)
- Campaign Service (business logic)
- Upload endpoints (data ingestion)
"""

import pandas as pd
from typing import Optional, Dict, List


# ============================================================================
# METRIC COLUMN ALIASES - Central registry of all column name variations
# ============================================================================
METRIC_COLUMN_ALIASES: Dict[str, List[str]] = {
    'spend': [
        'Spend', 'Total Spent', 'Total_Spent', 'spend', 'Cost', 'cost', 
        'Media Cost', 'media_cost', 'Ad Spend', 'ad_spend', 'Amount Spent', 
        'investment', 'Investment'
    ],
    'impressions': [
        'Impressions', 'impressions', 'Impr', 'impr', 'Views', 'views', 
        'Impress', 'impress'
    ],
    'clicks': [
        'Clicks', 'clicks', 'Link Clicks', 'link_clicks', 'Website Clicks', 
        'website_clicks', 'click'
    ],
    'conversions': [
        'Conversions', 'conversions', 'Purchases', 'purchases', 'Leads', 
        'leads', 'Results', 'results', 'Total Conversions', 'total_conversions', 
        'conv', 'Sales', 'sales'
    ],
    'date': [
        'Date', 'date', 'Day', 'day', 'Report Date', 'report_date', 
        'Period', 'period', 'Time', 'time', 'Reporting Date'
    ],
    'platform': [
        'Platform', 'platform', 'Source', 'source', 'Network', 'network', 
        'Data Source', 'data_source', 'Ad Platform', 'ad_platform'
    ],
    'campaign': [
        'Campaign', 'campaign', 'Campaign Name', 'campaign_name', 'Campaign_Name'
    ],
    'funnel': [
        'Funnel', 'funnel', 'Funnel_Stage', 'Funnel Stage', 'Stage', 
        'stage', 'funnel_stage'
    ],
    'placement': [
        'Placement', 'placement', 'Position', 'position', 'Ad Placement', 
        'ad_placement'
    ],
    'channel': [
        'Channel', 'channel', 'Medium', 'medium', 'Marketing Channel', 
        'Traffic Source', 'channel_type', 'Channel Type'
    ],
    'device': [
        'Device', 'device', 'Device Type', 'device_type', 'Device_Type'
    ],
    'region': [
        'Region', 'region', 'Country', 'country', 'Geo', 'geo', 
        'Geography', 'geography', 'Location'
    ],
    'objective': [
        'Objective', 'objective', 'Campaign Objective', 'campaign_objective', 
        'Goal', 'goal'
    ],
    'ad_type': [
        'Ad Type', 'ad_type', 'Ad_Type', 'Format', 'format', 'Creative Type'
    ],
    'age': [
        'Age', 'age', 'Age Group', 'age_group', 'Age_Group', 'Age Range'
    ],
    'targeting': [
        'Targeting', 'targeting', 'Audience', 'audience', 'Target Audience', 
        'Segment'
    ],
    'revenue': [
        'Revenue', 'revenue', 'Total Revenue', 'total_revenue', 'Sales', 
        'sales', 'Purchase Value', 'purchase_value', 'Value', 'value', 
        'Revenue_2024', 'Revenue_2025'
    ]
}

# Dimension aliases for aggregation (subset of metrics)
DIMENSION_ALIASES: Dict[str, List[str]] = {
    key: METRIC_COLUMN_ALIASES[key] 
    for key in ['funnel', 'placement', 'channel', 'device', 'region', 
                'objective', 'ad_type', 'targeting', 'platform', 'campaign']
    if key in METRIC_COLUMN_ALIASES
}


def find_column(df: pd.DataFrame, metric_key: str) -> Optional[str]:
    """
    Find a column in DataFrame using the central alias mapping.
    Case-insensitive matching with comprehensive alias support.
    
    Args:
        df: pandas DataFrame
        metric_key: Key from METRIC_COLUMN_ALIASES (e.g., 'spend', 'impressions')
    
    Returns:
        Actual column name in df or None if not found
        
    Example:
        >>> df = pd.DataFrame({'Total Spent': [100]})
        >>> find_column(df, 'spend')
        'Total Spent'
    """
    if metric_key not in METRIC_COLUMN_ALIASES:
        # Try direct match first
        if metric_key in df.columns:
            return metric_key
        # Case-insensitive direct match
        for col in df.columns:
            if col.lower() == metric_key.lower():
                return col
        return None
    
    aliases = METRIC_COLUMN_ALIASES[metric_key]
    df_cols_lower = {c.lower(): c for c in df.columns}
    
    for alias in aliases:
        if alias.lower() in df_cols_lower:
            return df_cols_lower[alias.lower()]
    
    return None


def consolidate_metric_column(df: pd.DataFrame, metric_key: str) -> Optional[str]:
    """
    Finds all columns matching aliases for a metric and consolidates them.
    Priority is given to the first matching alias, filling NaNs with subsequent matches.
    
    This is useful when data has multiple columns that represent the same metric
    (e.g., 'Revenue_2024' and 'Revenue_2025').
    
    Args:
        df: pandas DataFrame (will be modified in place)
        metric_key: Key from METRIC_COLUMN_ALIASES
    
    Returns:
        Name of the consolidated column, or None if no matches found
        
    Note:
        Modifies the DataFrame in place by filling NaN values.
    """
    if metric_key not in METRIC_COLUMN_ALIASES:
        return None
    
    aliases = METRIC_COLUMN_ALIASES[metric_key]
    df_cols_lower = {c.lower(): c for c in df.columns}
    
    matched_cols = []
    for alias in aliases:
        if alias.lower() in df_cols_lower:
            matched_cols.append(df_cols_lower[alias.lower()])
    
    if not matched_cols:
        return None
    
    # If only one column, return it directly
    if len(matched_cols) == 1:
        return matched_cols[0]
    
    # Multiple columns: consolidate into first one
    primary_col = matched_cols[0]
    for col in matched_cols[1:]:
        df[primary_col] = df[primary_col].fillna(df[col])
    
    return primary_col


def get_available_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """
    Get a mapping of all available metric/dimension columns in a DataFrame.
    
    Returns:
        Dictionary mapping metric_key -> actual_column_name (or None if not found)
    """
    return {
        key: find_column(df, key) 
        for key in METRIC_COLUMN_ALIASES
    }


def normalize_column_names(df: pd.DataFrame, inplace: bool = False) -> pd.DataFrame:
    """
    Normalize column names to standard format (lowercase with underscores).
    
    Args:
        df: pandas DataFrame
        inplace: If True, modify in place. Otherwise return a copy.
    
    Returns:
        DataFrame with normalized column names
    """
    if not inplace:
        df = df.copy()
    
    # Create mapping from original to normalized names
    rename_map = {}
    for col in df.columns:
        # Find if this column matches any known alias
        normalized = None
        for metric_key, aliases in METRIC_COLUMN_ALIASES.items():
            if col.lower() in [a.lower() for a in aliases]:
                normalized = metric_key
                break
        
        if normalized:
            rename_map[col] = normalized
    
    if rename_map:
        df.rename(columns=rename_map, inplace=True)
    
    return df
