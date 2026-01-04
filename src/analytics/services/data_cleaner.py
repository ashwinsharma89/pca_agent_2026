
import pandas as pd
import pandera as pa
from pandera.typing import Series
from typing import Optional, List, Dict
import re
import numpy as np
from loguru import logger

# =============================================================================
# 1. PANDERA SCHEMA DEFINITION (The Contract)
# =============================================================================
class CampaignSchema(pa.DataFrameModel):
    """
    Standardizes the schema for all marketing data.
    If data passes this, it is safe for the AI to use.
    """
    # Core Dimensions
    date: Series[pd.Timestamp] = pa.Field(coerce=True) # Auto-convert strings to datetime
    platform: Optional[Series[str]] = pa.Field(nullable=True)
    campaign: Optional[Series[str]] = pa.Field(nullable=True)
    
    # Core Metrics (Coerced to float, must be non-negative)
    spend: Series[float] = pa.Field(ge=0, coerce=True, default=0.0)
    impressions: Series[float] = pa.Field(ge=0, coerce=True, default=0.0)
    clicks: Series[float] = pa.Field(ge=0, coerce=True, default=0.0)
    conversions: Series[float] = pa.Field(ge=0, coerce=True, default=0.0)
    revenue: Series[float] = pa.Field(ge=0, coerce=True, default=0.0)

    # Config
    class Config:
        strict = False # Allow extra columns (don't fail if 'ad_group' exists)
        coerce = True  # Try to convert types automatically

# =============================================================================
# 2. DATA CLEANER SERVICE (The Logic)
# =============================================================================
class DataCleanerService:
    """
    Service responsible for ETL, Validation, and Sanitization.
    Replaces manual cleaning logic in auto_insights.py.
    """
    
    def __init__(self):
        # Mapping for column normalization (Moved from campaigns.py/auto_insights.py)
        self.column_aliases = {
            'spend': ['Cost', 'Total Spent', 'Amount Spent', 'Ad Spend', 'investment'],
            'revenue': ['Sales', 'Total Revenue', 'Conversion Value', 'Purchase Value'],
            'impressions': ['Impr', 'Views'],
            'clicks': ['Link Clicks'],
            'conversions': ['Purchases', 'Leads', 'Results', 'Total Conversions'],
            'date': ['Day', 'Time', 'Period', 'Report Date']
        }

    def clean_and_validate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Main entry point. Takes raw DF, returns validated Schema-compliant DF.
        """
        if df is None or df.empty:
            logger.warning("DataCleaner received empty DataFrame")
            return pd.DataFrame(columns=['date', 'spend', 'impressions', 'clicks', 'conversions', 'revenue'])

        # 1. Normalize Column Names
        df = self._normalize_columns(df)
        
        # 2. Fill Missing Values (NaTs/NaNs)
        df = self._fill_missing_values(df)
        
        # 3. Validate with Pandera (The Bouncer)
        try:
            # Lazy validation allows us to see all errors
            clean_df = CampaignSchema.validate(df, lazy=True)
            return clean_df
        except pa.errors.SchemaErrors as err:
            logger.error(f"Schema Validation Failed: {err.failure_cases}")
            # In production, we might return the partial valid data or raise
            # For now, we try to return what we can
            return err.data # Pandera often returns the coerced data even on fail

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Map synonyms (Cost -> spend) using alias dictionary."""
        df.columns = [c.strip() for c in df.columns] # Strip whitespace
        
        # Invert the alias map for O(1) lookup
        # normalized_map = {'Cost': 'spend', 'Total Spent': 'spend', ...}
        normalized_map = {}
        for canonical, aliases in self.column_aliases.items():
            for alias in aliases:
                normalized_map[alias.lower()] = canonical
        
        # Rename columns
        new_cols = {}
        for col in df.columns:
            lower_col = col.lower().replace(' ', '_')
            # Check exact match first
            if lower_col in self.column_aliases: 
                new_cols[col] = lower_col
            # Check aliases
            elif lower_col in normalized_map:
                new_cols[col] = normalized_map[lower_col]
            # Check loose match (endswith)
            else:
                for canonical in self.column_aliases:
                    if canonical in lower_col:
                        new_cols[col] = canonical
                        break
        
        if new_cols:
            df = df.rename(columns=new_cols)
            
        return df

    def _fill_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle NaN values for metrics."""
        metrics = ['spend', 'impressions', 'clicks', 'conversions', 'revenue']
        for m in metrics:
            if m in df.columns:
                df[m] = df[m].fillna(0.0)
        return df

    @staticmethod
    def sanitize_text(text: str) -> str:
        """
        Utilities for cleaning LLM output (hallucinations, formatting).
        """
        if not isinstance(text, str): return str(text)
        
        # Remove markdown bold/italics
        text = re.sub(r'\*+', '', text)
        text = re.sub(r'_+', '', text)
        
        # Fix spacing between numbers and letters (e.g., "$100Spend")
        text = re.sub(r'(\d)([A-Za-z])', r'\1 \2', text)
        text = re.sub(r'([A-Za-z])(\d)', r'\1 \2', text)
        
        # Fix common concatenations
        text = text.replace('campaignson', 'campaigns on')
        text = text.replace('platformswith', 'platforms with')
        
        return text.strip()
