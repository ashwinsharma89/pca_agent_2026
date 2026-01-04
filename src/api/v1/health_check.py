"""
Health Check API Endpoint

Provides comprehensive campaign analysis using agent chains.
Combines NL-to-SQL, MediaAnalyticsExpert, and PacingReportAgent
for a full diagnostic view.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import pandas as pd
import logging

from src.agents.agent_chain import (
    campaign_health_check,
    deep_analysis,
    quick_insights,
    get_workflow_status,
    clear_workflow_state
)
from src.agents.shared_context import get_shared_context, reset_shared_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyze", tags=["Analysis Workflows"])

# =============================================================================
# Request/Response Models
# =============================================================================

class HealthCheckRequest(BaseModel):
    """Request for campaign health check"""
    question: Optional[str] = Field(
        default=None,
        description="Specific question to answer (optional). Default: overall metrics by platform"
    )
    start_date: Optional[str] = Field(None, description="Filter start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="Filter end date (YYYY-MM-DD)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "How are our Google campaigns performing?"
            }
        }


class QuickInsightRequest(BaseModel):
    """Request for quick insight on a specific metric"""
    metric: str = Field(
        default="spend",
        description="Metric to analyze: spend, roas, ctr, cpa, conversions"
    )


class DeepAnalysisRequest(BaseModel):
    """Request for deep analysis with multiple questions"""
    questions: List[str] = Field(
        ...,
        description="List of questions to answer"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "questions": [
                    "What is total spend by platform?",
                    "Which platform has best ROAS?",
                    "What are top 5 campaigns by conversions?"
                ]
            }
        }


class WorkflowStep(BaseModel):
    """A single step in the workflow"""
    step: str
    status: str
    error: Optional[str] = None
    reason: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Response from health check"""
    success: bool
    workflow: str
    started_at: str
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    steps: List[WorkflowStep]
    metrics: Optional[Dict[str, Any]] = None
    insights: Optional[Dict[str, Any]] = None
    patterns: Optional[Dict[str, Any]] = None
    business_context: Optional[Dict[str, Any]] = None
    pacing: Optional[Dict[str, Any]] = None
    recommendations: List[str] = []
    all_recommendations: List[str] = []
    errors: List[str] = []
    context_summary: Optional[Dict[str, Any]] = None


class QuickInsightResponse(BaseModel):
    """Response from quick insight"""
    success: bool
    workflow: str
    metric: str
    question: str
    answer: Optional[str] = None
    sql: Optional[str] = None
    error: Optional[str] = None


class WorkflowStatusResponse(BaseModel):
    """Current workflow status"""
    context: Dict[str, Any]
    insights: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    anomalies: List[Dict[str, Any]]
    recent_queries: List[Dict[str, Any]]


# =============================================================================
# Helper to get campaign data
# =============================================================================

async def get_campaign_data(start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
    """
    Get campaign data from DuckDB with smart date filtering.
    Defaults to 'Latest 30 Days' (based on data max date) if no dates provided.
    """
    import duckdb
    from pathlib import Path
    from datetime import datetime, timedelta
    
    db_path = Path(__file__).parent.parent.parent.parent / "data" / "analytics.duckdb"
    
    if not db_path.exists():
        raise HTTPException(status_code=404, detail="Database not found. Upload data first.")
    
    try:
        conn = duckdb.connect(str(db_path), read_only=True)
        
        # Base query
        query = "SELECT * FROM campaigns"
        params = []
        where_clauses = []
        
        # Check max date first for defaults
        if not start_date and not end_date:
            try:
                # Get max date from data to properly default (handle historical data)
                max_date_res = conn.execute("SELECT MAX(\"Date\") FROM campaigns").fetchone()
                if max_date_res and max_date_res[0]:
                    max_date_dt = max_date_res[0]
                    # DuckDB returns Timestamp, convert to standard usage
                    if hasattr(max_date_dt, 'date'):
                         max_date_val = max_date_dt.date()
                    else:
                         max_date_val = max_date_dt # Fallback
                    
                    # Default: Last 30 days ending at max_date
                    default_end = max_date_val
                    default_start = default_end - timedelta(days=30)
                    
                    logger.info(f"Applying default Analysis Window: {default_start} to {default_end}")
                    
                    where_clauses.append('"Date" >= ?')
                    params.append(default_start)
                    where_clauses.append('"Date" <= ?')
                    params.append(default_end)
            except Exception as e:
                logger.warning(f"Failed to determine max date: {e}")

        # Explicit filters override defaults
        if start_date:
            where_clauses.append('"Date" >= ?')
            params.append(start_date)
        
        if end_date:
            where_clauses.append('"Date" <= ?')
            params.append(end_date)
            
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
            
        df = conn.execute(query, params).fetchdf()
        conn.close()
        
        # Ensure proper datetime format for Pandas
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            
        return df
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load data: {e}")


# =============================================================================
# API Endpoints
# =============================================================================

@router.post("/health-check", response_model=HealthCheckResponse)
async def run_health_check(request: HealthCheckRequest):
    """
    Run comprehensive campaign health check.
    
    Chains multiple agents:
    1. NL-to-SQL Engine - Gets key metrics
    2. MediaAnalyticsExpert - Generates insights
    3. PacingReportAgent - Checks budget pacing
    
    Returns combined analysis with metrics, insights, and recommendations.
    """
    logger.info(f"Health check requested. Question: {request.question}")
    
    try:
        # Get campaign data with filters
        data = await get_campaign_data(
            start_date=request.start_date,
            end_date=request.end_date
        )
        logger.info(f"Loaded {len(data)} rows from database")
        
        # Run health check workflow
        result = await campaign_health_check(
            data=data,
            question=request.question
        )
        
        return HealthCheckResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick-insight", response_model=QuickInsightResponse)
async def run_quick_insight(request: QuickInsightRequest):
    """
    Get quick insight for a specific metric.
    
    Available metrics: spend, roas, ctr, cpa, conversions
    """
    logger.info(f"Quick insight requested for: {request.metric}")
    
    try:
        data = await get_campaign_data()
        
        result = await quick_insights(
            data=data,
            metric=request.metric
        )
        
        return QuickInsightResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quick insight failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deep-analysis")
async def run_deep_analysis(request: DeepAnalysisRequest):
    """
    Run deep analysis answering multiple questions.
    
    Useful for comprehensive multi-question analysis.
    """
    logger.info(f"Deep analysis requested. {len(request.questions)} questions")
    
    try:
        data = await get_campaign_data()
        
        result = await deep_analysis(
            data=data,
            questions=request.questions
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Deep analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflow-status", response_model=WorkflowStatusResponse)
async def get_status():
    """
    Get current workflow status.
    
    Shows accumulated insights, recommendations, anomalies,
    and recent queries from the current session.
    """
    status = get_workflow_status()
    return WorkflowStatusResponse(**status)


@router.post("/reset")
async def reset_workflow():
    """
    Reset workflow state.
    
    Clears all cached data, insights, and recommendations.
    Use before starting a new analysis session.
    """
    clear_workflow_state()
    return {"status": "reset", "message": "Workflow state cleared"}
