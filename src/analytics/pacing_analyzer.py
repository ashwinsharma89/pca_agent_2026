
import polars as pl
from datetime import datetime
from typing import Dict, Any

class PacingAnalyzer:
    """
    Analyzes campaign budget pacing.
    """
    
    @staticmethod
    def analyze_pacing(df: pl.DataFrame, total_budget: float, days_elapsed: int, total_days: int) -> Dict[str, Any]:
        """
        Calculate pacing metrics.
        """
        if df.is_empty():
            return {}
            
        spend = df.select(pl.col('spend').sum()).item()
        
        if total_days == 0:
            pacing_percent = 0
        else:
            expected_spend = (total_budget / total_days) * days_elapsed
            pacing_percent = (spend / expected_spend * 100) if expected_spend > 0 else 0
            
        return {
            "spend_so_far": spend,
            "budget": total_budget,
            "pacing_percent": pacing_percent,
            "status": "on_track" if 90 <= pacing_percent <= 110 else ("overspending" if pacing_percent > 110 else "underspending")
        }
