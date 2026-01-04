
import polars as pl
import numpy as np
from typing import Dict, List, Optional, Union
from loguru import logger

class MetricsCalculator:
    """
    High-performance metrics calculator using Polars.
    Replaces eager Pandas operations with lazy Polars expressions.
    """
    
    @staticmethod
    def calculate_core_metrics(df: Union[pl.DataFrame, pl.LazyFrame]) -> pl.DataFrame:
        """
        Calculate standard marketing KPIs (CTR, CPC, CPM, ROAS, CPA, CVR).
        Handles division by zero gracefully.
        """
        # Convert to LazyFrame if not already
        if isinstance(df, pl.DataFrame):
            lf = df.lazy()
        else:
            lf = df

        # Define safe division helper
        def safe_div(a, b, default=0.0):
            return pl.when(b != 0).then(a / b).otherwise(default)

        # Standardize column names if needed (assuming lowercase 'spend', 'clicks', etc.)
        # Ideally, normalization happens before this stage.
        
        return lf.with_columns([
            # CTR = Clicks / Impressions * 100
            safe_div(pl.col("clicks") * 100, pl.col("impressions")).alias("ctr"),
            
            # CPC = Spend / Clicks
            safe_div(pl.col("spend"), pl.col("clicks")).alias("cpc"),
            
            # CPM = Spend / Impressions * 1000
            safe_div(pl.col("spend") * 1000, pl.col("impressions")).alias("cpm"),
            
            # ROAS = Revenue / Spend
            safe_div(pl.col("revenue"), pl.col("spend")).alias("roas"),
            
            # CPA = Spend / Conversions
            safe_div(pl.col("spend"), pl.col("conversions")).alias("cpa"),
            
            # CVR = Conversions / Clicks * 100
            safe_div(pl.col("conversions") * 100, pl.col("clicks")).alias("cvr")
        ]).collect()

    @staticmethod
    def calculate_aggregated_metrics(df: pl.DataFrame, group_by: List[str]) -> pl.DataFrame:
        """
        Aggregate metrics by dimensions (e.g., Campaign, Platform).
        Recalculates rates (CTR, CPC) after summing base metrics.
        """
        agg_exprs = [
            pl.col("spend").sum(),
            pl.col("impressions").sum(),
            pl.col("clicks").sum(),
            pl.col("conversions").sum(),
            pl.col("revenue").sum()
        ]
        
        grouped = df.lazy().group_by(group_by).agg(agg_exprs)
        
        # Reuse core metric calculation on aggregated data
        return MetricsCalculator.calculate_core_metrics(grouped)
