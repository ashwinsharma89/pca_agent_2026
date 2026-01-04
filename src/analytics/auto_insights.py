
"""
Automated Analytics Engine with Media Domain Expertise
Generates insights and recommendations automatically from campaign data.

REFACTORED: This module now acts as a compatibility adapter for the new 
modular architecture (AnalyticsOrchestrator).
"""
import pandas as pd
from typing import Dict, Any, Optional
from loguru import logger
from .orchestrator import AnalyticsOrchestrator

class MediaAnalyticsExpert:
    """
    AI-powered media analytics expert that generates insights automatically.
    
    ADAPTER: Proxies calls to AnalyticsOrchestrator.
    """
    
    def __init__(self, api_key: Optional[str] = None, use_anthropic: Optional[bool] = None):
        """Initialize the analytics expert (Wrapper)."""
        logger.info("Initializing MediaAnalyticsExpert (Refactored Adapter)")
        self.orchestrator = AnalyticsOrchestrator(api_key=api_key)
    
    def analyze_all(self, df: pd.DataFrame, 
                    progress_callback: Optional[callable] = None,
                    use_parallel: bool = True,
                    **kwargs) -> Dict[str, Any]:
        """
        Run complete automated analysis on campaign data.
        Delegates to the modular Orchestrator.
        """
        logger.info("Delegating analysis to AnalyticsOrchestrator")
        
        # Call the new orchestrator
        result = self.orchestrator.analyze_campaigns(df)
        
        # ADAPTER LOGIC: Map new output structure to old structure
        # The Orchestrator returns: metrics, status, recommendations, narrative
        # Ideally, we should update the Orchestrator to match, but here we fill gaps.
        
        adapted_result = {
            "metrics": result.get("metrics", {}),
            "status": result.get("status", {}),
            "recommendations": result.get("recommendations", []),
            "executive_summary": result.get("narrative", ""),
            "insights": [], # Placeholder
            "opportunities": [], # Placeholder
            "risks": [], # Placeholder
            
            # Legacy fields required by UI (returning empty for now to test stability)
            "funnel_analysis": {},
            "roas_analysis": {},
            "audience_analysis": {},
            "tactics_analysis": {},
            "budget_optimization": {},
            
            "performance_stats": {
                "total_time_seconds": result.get("execution_time", 0),
                "engine": "polars-orchestrator"
            }
        }
        
        return adapted_result
