
import pandas as pd
import time
from typing import Dict, Any, List, Optional
from loguru import logger
import polars as pl

# Import new modular components
from .metrics_calculator import MetricsCalculator
from .business_rules import BusinessRules
from .recommendations import RecommendationEngine
from .text_cleaner import TextCleaner
from .llm_service import LLMService

class AnalyticsOrchestrator:
    """
    Manager class that coordinates the entire analytics pipeline.
    Replaces the monolithic MediaAnalyticsExpert.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.llm_service = LLMService(api_key=api_key)
        self.text_cleaner = TextCleaner()
        self.metrics_engine = MetricsCalculator()
        
    def analyze_campaigns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Main entry point for analysis.
        """
        start_time = time.time()
        logger.info(f"Starting modular analysis on {len(df)} rows")
        
        # 1. Convert to Polars for Heavy Math
        # Handle empty DataFrames
        if df.empty:
            return {"error": "No data provided"}

        # Normalize columns to lowercase for consistent access
        df.columns = df.columns.str.lower()

        pdf = pl.from_pandas(df)
        
        # 2. Calculate Token-Efficient Metrics (Vectorized)
        # Global metrics
        global_metrics = MetricsCalculator.calculate_core_metrics(pdf).to_dicts()[0]
        
        # Calculate Breakdowns (Platform, Campaign)
        breakdowns = self._calculate_breakdowns(pdf)
        
        # Merge breakdowns into metrics
        metrics_output = {
            "overview": global_metrics,
            **breakdowns
        }
        
        # 3. Apply Business Rules (Logic)
        status = BusinessRules.evaluate_performance(global_metrics)
        
        # 4. Generate Recommendations (Advisor)
        recommendations = RecommendationEngine.generate_recommendations(global_metrics, status)
        
        # 5. Generate LLM Narrative (Creative)
        # We construct a highly optimized prompt with just the necessary data
        prompt = self._construct_prompt(global_metrics, status, recommendations)
        
        try:
            narrative = self.llm_service.generate_completion(
                prompt=prompt,
                system_prompt="You are a senior media buyer. Be concise and actionable."
            )
            # 6. Clean Output (Janitor)
            narrative = self.text_cleaner.strip_italics(narrative)
        except Exception as e:
            logger.error(f"LLM Generation failed: {e}")
            narrative = "Analysis could not be generated due to a service error."
            
        return {
            "metrics": metrics_output,
            "status": status,
            "recommendations": recommendations,
            "narrative": narrative,
            "execution_time": time.time() - start_time
        }
    
    def _calculate_breakdowns(self, df: pl.DataFrame) -> Dict[str, Any]:
        """Calculate breakdowns by common dimensions using Polars."""
        breakdowns = {}
        
        # Platform Breakdown
        if "platform" in df.columns or "Platform" in df.columns:
            col = "platform" if "platform" in df.columns else "Platform"
            # Normalize column name for calculation
            # We assume MetricsCalculator handles standard names like 'spend', 'clicks'
            # If input df has 'Platform', we group by it.
            
            # Map columns if needed (Polars case sensitivity)
            # This is a simplified mapping. Real world needs robust mapping.
            # Assuming input DF is already normalized or we do it here.
            
            try:
                platform_metrics = MetricsCalculator.calculate_aggregated_metrics(df, [col])
                breakdowns["by_platform"] = platform_metrics.to_dicts()
            except Exception as e:
                logger.warning(f"Platform breakdown failed: {e}")
                breakdowns["by_platform"] = []

        # Campaign Breakdown
        if "campaign" in df.columns or "Campaign" in df.columns:
            col = "campaign" if "campaign" in df.columns else "Campaign"
            try:
                camp_metrics = MetricsCalculator.calculate_aggregated_metrics(df, [col])
                breakdowns["by_campaign"] = camp_metrics.to_dicts()
            except Exception as e:
                logger.warning(f"Campaign breakdown failed: {e}")
                breakdowns["by_campaign"] = []
                
        return breakdowns
    
    def _construct_prompt(self, metrics: Dict, status: Dict, recs: List) -> str:
        """Construct a data-rich prompt for the LLM."""
        return f"""
        Analyze this campaign performance:
        
        DATA:
        - Spend: ${metrics.get('spend', 0):.2f}
        - ROAS: {metrics.get('roas', 0):.2f}x
        - CTR: {metrics.get('ctr', 0):.2f}%
        
        STATUS:
        {status}
        
        RECOMMENDATIONS:
        {RecommendationEngine._format_for_llm(recs)}
        
        Provide a 3-bullet executive summary focusing on the most critical issues.
        """
