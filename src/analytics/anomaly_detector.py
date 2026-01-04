
import polars as pl
import numpy as np
from typing import List, Dict, Any

class AnomalyDetector:
    """
    Detects anomalies in campaign data.
    """
    
    @staticmethod
    def detect_anomalies(df: pl.DataFrame, metric: str = 'cpc') -> List[Dict[str, Any]]:
        """
        Detect anomalies using Z-Score method on Polars DataFrame.
        """
        if df.is_empty() or metric not in df.columns:
            return []
            
        # Calculate Z-Score
        # (val - mean) / std
        anomalies = df.with_columns([
            ((pl.col(metric) - pl.col(metric).mean()) / pl.col(metric).std()).alias("z_score")
        ]).filter(
            pl.col("z_score").abs() > 2.0  # Threshold: 2 Standard Deviations
        )
        
        return anomalies.to_dicts()
