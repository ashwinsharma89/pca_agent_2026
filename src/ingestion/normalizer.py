"""
Data Normalizer (Layer 2)

Transforms diverse input columns to a Standard Canonical Schema.
Maps varied column names to normalized field names.

Design Pattern: Transformer Pattern
Input: Raw DataFrame chunks from adapters
Output: Normalized DataFrame with canonical schema
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from loguru import logger
from datetime import datetime

from src.utils.column_mapping import METRIC_COLUMN_ALIASES, find_column


# Canonical Schema Definition
CANONICAL_SCHEMA = {
    # Core metrics
    'spend': {'type': 'float64', 'nullable': False, 'default': 0.0},
    'impressions': {'type': 'int64', 'nullable': False, 'default': 0},
    'clicks': {'type': 'int64', 'nullable': False, 'default': 0},
    'conversions': {'type': 'int64', 'nullable': False, 'default': 0},
    'revenue': {'type': 'float64', 'nullable': True, 'default': 0.0},
    
    # Dimensions
    'date': {'type': 'datetime64[ns]', 'nullable': False, 'default': None},
    'platform': {'type': 'string', 'nullable': False, 'default': 'Unknown'},
    'channel': {'type': 'string', 'nullable': True, 'default': 'Unknown'},
    'campaign': {'type': 'string', 'nullable': True, 'default': 'Unknown'},
    
    # Optional dimensions
    'funnel': {'type': 'string', 'nullable': True, 'default': None},
    'device': {'type': 'string', 'nullable': True, 'default': None},
    'region': {'type': 'string', 'nullable': True, 'default': None},
    'objective': {'type': 'string', 'nullable': True, 'default': None},
    'ad_type': {'type': 'string', 'nullable': True, 'default': None},
}


class DataNormalizer:
    """
    Normalizes data to canonical schema.
    
    Responsibilities:
    - Map column names to canonical names
    - Convert data types
    - Apply defaults for missing values
    - Validate required fields
    """
    
    def __init__(
        self,
        strict_mode: bool = False,
        log_mappings: bool = True
    ):
        """
        Initialize normalizer.
        
        Args:
            strict_mode: If True, fail on missing required columns
            log_mappings: If True, log column mappings
        """
        self.strict_mode = strict_mode
        self.log_mappings = log_mappings
        self.column_mappings: Dict[str, str] = {}
    
    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize a DataFrame to canonical schema.
        
        Args:
            df: Input DataFrame with varied column names
        
        Returns:
            Normalized DataFrame with canonical column names
        """
        if df.empty:
            return self._create_empty_canonical_df()
        
        # Step 1: Map columns to canonical names
        mapped_df = self._map_columns(df.copy())
        
        # Step 2: Convert data types
        typed_df = self._convert_types(mapped_df)
        
        # Step 3: Apply defaults for missing columns
        filled_df = self._apply_defaults(typed_df)
        
        # Step 4: Validate required fields
        if self.strict_mode:
            self._validate_required(filled_df)
        
        return filled_df
    
    def _map_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Map input columns to canonical names."""
        rename_map = {}
        found_columns = set()
        
        for canonical_name in CANONICAL_SCHEMA.keys():
            input_col = find_column(df, canonical_name)
            if input_col:
                rename_map[input_col] = canonical_name
                found_columns.add(canonical_name)
                if self.log_mappings:
                    logger.debug(f"Mapped '{input_col}' -> '{canonical_name}'")
        
        # Store mappings for debugging
        self.column_mappings = rename_map
        
        # Rename columns
        df = df.rename(columns=rename_map)
        
        # Keep additional columns that weren't mapped (prefixed with 'extra_')
        unmapped_columns = set(df.columns) - set(CANONICAL_SCHEMA.keys())
        for col in unmapped_columns:
            if col not in rename_map.values():
                new_name = f"extra_{col.lower().replace(' ', '_')}"
                df = df.rename(columns={col: new_name})
        
        return df
    
    def _convert_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert columns to canonical types."""
        for col, schema in CANONICAL_SCHEMA.items():
            if col not in df.columns:
                continue
            
            target_type = schema['type']
            
            try:
                if target_type == 'float64':
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
                
                elif target_type == 'int64':
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype('int64')
                
                elif target_type == 'datetime64[ns]':
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                
                elif target_type == 'string':
                    df[col] = df[col].astype(str).replace('nan', schema.get('default', ''))
                
            except Exception as e:
                logger.warning(f"Type conversion failed for {col}: {e}")
        
        return df
    
    def _apply_defaults(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply default values for missing columns."""
        for col, schema in CANONICAL_SCHEMA.items():
            if col not in df.columns:
                default = schema.get('default')
                if default is not None:
                    df[col] = default
                    logger.debug(f"Added missing column '{col}' with default: {default}")
        
        return df
    
    def _validate_required(self, df: pd.DataFrame) -> None:
        """Validate that required columns are present and non-null."""
        required_cols = [
            name for name, schema in CANONICAL_SCHEMA.items()
            if not schema['nullable']
        ]
        
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Required column '{col}' is missing")
            
            null_count = df[col].isna().sum()
            if null_count > 0:
                logger.warning(f"Column '{col}' has {null_count} null values")
    
    def _create_empty_canonical_df(self) -> pd.DataFrame:
        """Create an empty DataFrame with canonical schema."""
        return pd.DataFrame({
            col: pd.Series(dtype=schema['type'])
            for col, schema in CANONICAL_SCHEMA.items()
        })
    
    def get_mapping_report(self) -> Dict[str, Any]:
        """Get a report of column mappings performed."""
        return {
            "mappings": self.column_mappings,
            "mapped_count": len(self.column_mappings),
            "canonical_columns": list(CANONICAL_SCHEMA.keys())
        }


class SchemaEnforcer:
    """
    Enforces schema constraints more strictly.
    Used for final validation before storage.
    """
    
    @staticmethod
    def enforce_constraints(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """
        Enforce business logic constraints on the data.
        
        Returns:
            Tuple of (cleaned DataFrame, list of constraint violations)
        """
        violations = []
        df = df.copy()
        
        # Constraint 1: spend >= 0
        if 'spend' in df.columns:
            invalid_spend = df['spend'] < 0
            if invalid_spend.any():
                violations.append(f"Negative spend values: {invalid_spend.sum()} rows")
                df.loc[invalid_spend, 'spend'] = 0
        
        # Constraint 2: impressions >= clicks
        if 'impressions' in df.columns and 'clicks' in df.columns:
            invalid = df['clicks'] > df['impressions']
            if invalid.any():
                violations.append(f"Clicks > Impressions: {invalid.sum()} rows")
                # Fix by setting impressions = clicks
                df.loc[invalid, 'impressions'] = df.loc[invalid, 'clicks']
        
        # Constraint 3: clicks >= conversions
        if 'clicks' in df.columns and 'conversions' in df.columns:
            invalid = df['conversions'] > df['clicks']
            if invalid.any():
                violations.append(f"Conversions > Clicks: {invalid.sum()} rows")
                # Fix by setting clicks = conversions
                df.loc[invalid, 'clicks'] = df.loc[invalid, 'conversions']
        
        # Constraint 4: No future dates
        if 'date' in df.columns:
            future = df['date'] > pd.Timestamp.now()
            if future.any():
                violations.append(f"Future dates: {future.sum()} rows")
                df.loc[future, 'date'] = pd.Timestamp.now()
        
        return df, violations


def normalize_dataframe(
    df: pd.DataFrame,
    strict_mode: bool = False
) -> pd.DataFrame:
    """
    Convenience function to normalize a DataFrame.
    
    Args:
        df: Input DataFrame
        strict_mode: If True, fail on missing required columns
    
    Returns:
        Normalized DataFrame
    """
    normalizer = DataNormalizer(strict_mode=strict_mode)
    return normalizer.normalize(df)
