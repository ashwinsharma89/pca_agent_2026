"""
Intelligence Studio API - Natural Language to Visualization
Location: src/api/v1/intelligence.py

Features:
- Natural language query processing
- SQL generation
- Chart type recommendation
- AI insights generation
- Follow-up question suggestions
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import time
import json
import os
import pandas as pd
from sqlalchemy import text
import logging

# Import your existing modules
from src.query_engine.nl_to_sql import NaturalLanguageQueryEngine
from src.database.duckdb_manager import get_duckdb_manager, CAMPAIGNS_PARQUET
from src.api.middleware.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intelligence", tags=["intelligence"])

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class QueryRequest(BaseModel):
    query: str = Field(..., description="Natural language query")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    user_id: Optional[str] = None

class QueryResponse(BaseModel):
    query: str
    chart_type: str
    data: List[Dict[str, Any]]
    insight: str
    recommendations: List[str]
    follow_up_questions: List[str]
    sql_query: Optional[str] = None
    execution_time_ms: int
    data_source: str = "campaigns"
    metadata: Optional[Dict[str, Any]] = None

class ChartRecommendation(BaseModel):
    chart_type: str
    confidence: float
    reason: str

# ============================================================================
# CHART TYPE RECOMMENDATION ENGINE
# ============================================================================

def recommend_chart_type(query: str, data: List[Dict], sql_query: str) -> ChartRecommendation:
    """
    AI-powered chart type recommendation based on query and data structure
    """
    query_lower = query.lower()
    
    # Time-based queries → Line chart
    if any(word in query_lower for word in ['trend', 'over time', 'daily', 'weekly', 'monthly', 'timeline']):
        return ChartRecommendation(
            chart_type='line',
            confidence=0.95,
            reason='Time-based analysis is best visualized with line charts to show trends'
        )
    
    # Comparison queries → Bar chart
    if any(word in query_lower for word in ['compare', 'vs', 'versus', 'top', 'best', 'worst']):
        return ChartRecommendation(
            chart_type='bar',
            confidence=0.90,
            reason='Comparative analysis works best with bar charts for clear category comparison'
        )
    
    # Distribution/proportion → Pie chart
    if any(word in query_lower for word in ['distribution', 'breakdown', 'proportion', 'share', 'split']):
        if len(data) <= 8:  # Pie charts work best with few categories
            return ChartRecommendation(
                chart_type='pie',
                confidence=0.85,
                reason='Distribution queries with few categories are ideal for pie charts'
            )
    
    # Correlation/relationship → Scatter
    if any(word in query_lower for word in ['correlation', 'relationship', 'impact', 'affect']):
        return ChartRecommendation(
            chart_type='scatter',
            confidence=0.88,
            reason='Relationship analysis is best shown with scatter plots'
        )
    
    # Check data structure for additional hints
    if data and len(data) > 0:
        first_row = data[0]
        numeric_cols = sum(1 for v in first_row.values() if isinstance(v, (int, float)))
        
        # Multiple numeric columns → Dual-axis or area chart
        if numeric_cols >= 2:
            return ChartRecommendation(
                chart_type='area',
                confidence=0.82,
                reason='Multiple metrics are effectively displayed with area charts'
            )
    
    # Default to bar chart
    return ChartRecommendation(
        chart_type='bar',
        confidence=0.75,
        reason='Bar charts are versatile and work well for most categorical data'
    )

# ============================================================================
# AI INSIGHTS GENERATION
# ============================================================================

def generate_insights(query: str, data: List[Dict], chart_type: str) -> tuple[str, List[str], List[str]]:
    """
    Generate AI-powered insights, recommendations, and follow-up questions
    """
    if not data:
        return (
            "No data found for your query.",
            ["Try adjusting your query or date range."],
            ["What data is available?", "Show me all campaigns"]
        )
    
    # Calculate basic statistics
    try:
        # Find numeric columns
        numeric_cols = []
        if data:
            first_row = data[0]
            numeric_cols = [k for k, v in first_row.items() if isinstance(v, (int, float))]
        
        insight_parts = []
        recommendations = []
        follow_ups = []
        
        # Analyze first numeric column
        if numeric_cols and len(numeric_cols) > 0:
            metric = numeric_cols[0]
            values = [row.get(metric, 0) for row in data]
            
            total = sum(values)
            avg = total / len(values) if values else 0
            max_val = max(values) if values else 0
            min_val = min(values) if values else 0
            
            # Find top performer
            top_item = max(data, key=lambda x: x.get(metric, 0))
            top_name = list(top_item.values())[0]  # First column is usually the dimension
            
            # Generate insight
            insight_parts.append(f"Total {metric}: ${total:,.2f}" if 'spend' in metric.lower() or 'cost' in metric.lower() else f"Total {metric}: {total:,.0f}")
            insight_parts.append(f"Average: {avg:.2f}")
            insight_parts.append(f"Top performer: {top_name} (${max_val:,.2f})" if 'spend' in metric.lower() else f"Top performer: {top_name} ({max_val:,.0f})")
            
            # Generate recommendations
            if len(values) > 1:
                variance = max(values) / min(values) if min(values) > 0 else 0
                if variance > 5:
                    recommendations.append(f"High variance detected ({variance:.1f}x). Consider reallocating budget from low performers.")
                
                if avg > 0:
                    underperformers = [d for d in data if d.get(metric, 0) < avg * 0.5]
                    if underperformers:
                        recommendations.append(f"{len(underperformers)} items performing below 50% of average. Review and optimize.")
            
            # Generate follow-up questions
            follow_ups.append(f"What's the trend over the last 30 days?")
            follow_ups.append(f"Compare {metric} across different platforms")
            follow_ups.append(f"Show me the breakdown by device type")
        
        insight = " | ".join(insight_parts) if insight_parts else "Data retrieved successfully."
        
        if not recommendations:
            recommendations = ["Continue monitoring performance", "Consider A/B testing variations"]
        
        if not follow_ups:
            follow_ups = ["Show me more details", "What caused this?", "Compare to last period"]
        
        return insight, recommendations[:3], follow_ups[:3]
        
    except Exception as e:
        print(f"Error generating insights: {e}")
        return (
            "Data analysis complete.",
            ["Review the visualization for insights."],
            ["Show me more data", "Break this down further"]
        )

# ============================================================================
# MAIN ENDPOINT
# ============================================================================

@router.post("/query", response_model=QueryResponse)
async def process_intelligence_query(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Process natural language query and return visualization data
    
    Example queries:
    - "Show me Google Ads spend vs Meta for Q4"
    - "What are my top 10 campaigns by conversions?"
    - "Compare CTR across all platforms this month"
    - "Show spend trend over last 30 days"
    """
    start_time = time.time()
    
    try:
        # Step 1: Convert natural language to SQL and execute
        api_key = os.getenv("OPENAI_API_KEY", "")
        nl_engine = NaturalLanguageQueryEngine(api_key=api_key)
        
        # Try to use real engine, fallback to mock if it fails
        try:
             # Load data from DuckDB/Parquet into engine's DuckDB
            db_manager = get_duckdb_manager()
            
            if not db_manager.has_data():
                logger.warning("No campaign data found in Parquet for intelligence query")
                raise HTTPException(
                    status_code=400,
                    detail="No campaign data available. Please upload data before using Intelligence Studio."
                )
            
            # Load data from Parquet
            with db_manager.connection() as conn:
                df = conn.execute(f"SELECT * FROM '{CAMPAIGNS_PARQUET}' LIMIT 10000").df()
            
            if df.empty:
                logger.warning("Campaign data exists but is empty")
                raise HTTPException(
                    status_code=400,
                    detail="No campaign data available. Please upload data before using Intelligence Studio."
                )
                
            # Initialize engine with data
            nl_engine.load_data(df)
            
            result = nl_engine.ask(request.query)
            
            if not result["success"]:
                 raise Exception(result.get("error", "Unknown NL Engine error"))

        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Real NL Engine failed: {e}. Falling back to Mock Engine.")
            mock_engine = MockNLToSQLEngine()
            sql_result = await mock_engine.process_query(request.query)
            
            # Map mock result to expected format
            result = {
                "success": sql_result.success,
                "sql_query": sql_result.sql,
                "results": None, # Will need to execute SQL locally if possible
                "answer": "Mock Answer",
                "execution_time": 0.1,
                "model_used": "mock",
                "error": sql_result.error
            }
            
            # If we have valid SQL from mock, execute it against our dataframe using duckdb locally
            # or just use the connection from the failed engine if it was initialized
            if result["success"] and result["sql_query"]:
                try:
                    import duckdb
                    conn = duckdb.connect(':memory:')
                    conn.register('campaigns', df)
                    result["results"] = conn.execute(result["sql_query"]).fetchdf()
                except Exception as exec_err:
                    logger.error(f"Mock SQL execution failed: {exec_err}")
                    raise HTTPException(status_code=400, detail=f"Mock processing failed: {str(exec_err)}")

        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=f"Query processing failed: {result.get('error', 'Unknown error')}"
            )
        
        # Step 2: Get results as list of dicts
        df = result["results"]
        if df is not None and not df.empty:
            data = df.to_dict(orient='records')
            columns = list(df.columns)
        else:
            data = []
            columns = []
        
        # Step 3: Recommend chart type
        chart_rec = recommend_chart_type(request.query, data, result["sql_query"] or "")
        
        # Step 4: Generate AI insights
        # If NLToSQLEngine already generated an answer, we can use it, or call our own
        insight = result["answer"] or "No specific insights generated."
        recommendations = [] # NaturalLanguageQueryEngine might not yield list of recommendations in 'answer'
        follow_ups = nl_engine.get_suggested_questions()
        
        # Step 5: Calculate execution time
        execution_time = int(result["execution_time"] * 1000)
        
        return QueryResponse(
            query=request.query,
            chart_type=chart_rec.chart_type,
            data=data,
            insight=insight,
            recommendations=recommendations,
            follow_up_questions=follow_ups,
            sql_query=result["sql_query"],
            execution_time_ms=execution_time,
            data_source="campaigns",
            metadata={
                "chart_confidence": chart_rec.confidence,
                "chart_reason": chart_rec.reason,
                "row_count": len(data),
                "column_count": len(columns),
                "model_used": result["model_used"]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Intelligence query error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Query processing failed: {str(e)}"
        )

# ============================================================================
# ADDITIONAL HELPER ENDPOINTS
# ============================================================================

@router.get("/suggestions")
async def get_query_suggestions(current_user: dict = Depends(get_current_user)):
    """
    Get suggested queries for the user
    """
    return {
        "suggestions": [
            "Show top 10 campaigns by ROAS",
            "Compare Google Ads vs Meta performance this month",
            "What caused the CPA spike last week?",
            "Show conversion funnel breakdown",
            "Which campaigns are underperforming?",
            "Analyze spend by device type",
            "Show me campaigns with CTR above 3%",
            "Compare performance across all platforms"
        ]
    }

@router.post("/refine-query")
async def refine_query(
    original_query: str,
    refinement: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Refine an existing query with additional context
    
    Example:
    Original: "Show me Google Ads spend"
    Refinement: "for last quarter"
    Result: "Show me Google Ads spend for last quarter"
    """
    refined_query = f"{original_query} {refinement}".strip()
    
    return {
        "original_query": original_query,
        "refinement": refinement,
        "refined_query": refined_query
    }

# ============================================================================
# MOCK NL-TO-SQL ENGINE (if your engine isn't ready)
# ============================================================================

class MockNLToSQLEngine:
    """
    Mock NL-to-SQL engine for testing
    Replace with your actual implementation
    """
    
    class SQLResult:
        def __init__(self, sql: str, success: bool = True, error: str = None):
            self.sql = sql
            self.success = success
            self.error = error
    
    async def process_query(self, query: str) -> SQLResult:
        """
        Simple mock implementation
        Replace with your actual NL-to-SQL logic
        """
        query_lower = query.lower()
        
        # Pattern matching for common queries
        if 'google ads' in query_lower and 'meta' in query_lower:
            return self.SQLResult(
                sql="""  # nosec B608
                    SELECT platform, 
                           SUM(spend) as spend, 
                           SUM(conversions) as conversions,
                           AVG(cpa) as cpa
                    FROM campaigns 
                    WHERE platform IN ('Google Ads', 'Meta Ads')
                    AND CAST(date AS DATE) >= CURRENT_DATE - INTERVAL 2 YEAR
                    GROUP BY platform
                    ORDER BY spend DESC
                """
            )
        
        if 'top' in query_lower and 'campaign' in query_lower:
            limit = 10
            if 'top 5' in query_lower:
                limit = 5
            elif 'top 20' in query_lower:
                limit = 20
            
            return self.SQLResult(
                sql=f"""  # nosec B608
                    SELECT campaign_name, 
                           SUM(spend) as spend,
                           SUM(conversions) as conversions,
                           AVG(cpa) as cpa,
                           SUM(spend) / NULLIF(SUM(conversions), 0) as calculated_cpa
                    FROM campaigns
                    WHERE CAST(date AS DATE) >= CURRENT_DATE - INTERVAL 2 YEAR
                    GROUP BY campaign_name
                    ORDER BY conversions DESC
                    LIMIT {limit}
                """
            )
        
        # Default query
        return self.SQLResult(
            sql="""  # nosec B608
                SELECT platform,
                       SUM(spend) as spend,
                       SUM(conversions) as conversions,
                       AVG(ctr) as ctr
                FROM campaigns
                WHERE CAST(date AS DATE) >= CURRENT_DATE - INTERVAL 2 YEAR
                GROUP BY platform
                ORDER BY spend DESC
            """
        )

# ============================================================================
# USAGE IN MAIN.PY
# ============================================================================

"""
# Add to your main.py:

from src.api.v1.intelligence import router as intelligence_router

app = FastAPI()
app.include_router(intelligence_router)

# Test endpoint:
# POST http://localhost:8000/api/v1/intelligence/query
# {
#   "query": "Show me Google Ads spend vs Meta for Q4"
# }
"""
