"""
Agent Chain - Collaborative Agent Workflows using SharedContext

This module provides chained workflows that combine multiple agents
for richer analysis. Agents share context to avoid redundant work.

Available Workflows:
1. campaign_health_check - Full diagnostic combining Q&A + Analysis + Pacing
2. deep_analysis - Query data → Analyze → Generate insights
3. quick_insights - Fast analysis of specific metrics

Usage:
    from src.agents.agent_chain import campaign_health_check
    
    result = await campaign_health_check(
        question="How are our campaigns performing?",
        data=campaign_df
    )
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
import pandas as pd
from datetime import datetime

from .shared_context import SharedContext, get_shared_context, reset_shared_context

logger = logging.getLogger(__name__)


# =============================================================================
# Lazy Agent Imports (to avoid circular imports)
# =============================================================================

def _get_nl_to_sql_engine():
    """Lazy import of NL-to-SQL engine"""
    from src.query_engine.nl_to_sql import NaturalLanguageQueryEngine
    import os
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")
    return NaturalLanguageQueryEngine(api_key=api_key)


def _get_media_analytics_expert():
    """Lazy import of MediaAnalyticsExpert"""
    from src.analytics.auto_insights import MediaAnalyticsExpert
    return MediaAnalyticsExpert()



def _get_enhanced_reasoning_agent():
    """Lazy import of EnhancedReasoningAgent"""
    from src.agents.enhanced_reasoning_agent import EnhancedReasoningAgent
    return EnhancedReasoningAgent()


def _get_b2b_specialist_agent():
    """Lazy import of B2BSpecialistAgent"""
    from src.agents.b2b_specialist_agent import B2BSpecialistAgent
    return B2BSpecialistAgent()


# =============================================================================
# Chain 1: Campaign Health Check
# =============================================================================

async def campaign_health_check(
    data: pd.DataFrame,
    question: Optional[str] = None,
    context: Optional[SharedContext] = None
) -> Dict[str, Any]:
    """
    Comprehensive campaign health check combining all agents.
    
    Pipeline:
    1. NL-to-SQL Engine → Get key metrics
    2. MediaAnalyticsExpert → Generate insights
    3. EnhancedReasoningAgent → Detect patterns & anomalies
    4. B2BSpecialistAgent → Apply business context
    5. PacingReportAgent → Check budget pacing (if applicable)
    
    Args:
        data: Campaign data DataFrame
        question: Optional specific question to answer
        context: Optional SharedContext (uses global if not provided)
    
    Returns:
        Combined analysis with metrics, insights, pacing, and recommendations
    """
    start_time = datetime.utcnow()
    ctx = context or get_shared_context()
    
    logger.info("Starting Campaign Health Check workflow")
    
    results = {
        "workflow": "campaign_health_check",
        "started_at": start_time.isoformat(),
        "steps": [],
        "metrics": None,
        "insights": None,
        "pacing": None,
        "recommendations": [],
        "success": True,
        "errors": []
    }
    
    try:
        # Step 1: Cache the data for all agents
        ctx.add_data("campaign_data", data, source="workflow")
        
        # Step 2: Query key metrics using NL-to-SQL
        logger.info("Step 1: Querying key metrics")
        try:
            engine = _get_nl_to_sql_engine()
            engine.load_data(data, "campaigns")
            
            # Default question if none provided
            q = question or "Give me total spend, impressions, clicks, conversions, and ROAS by platform"
            
            query_result = engine.ask(q)
            
            # Cache the result
            ctx.add_data("query_result", query_result, source="NL-to-SQL")
            ctx.add_query(q, query_result)
            
            results["metrics"] = {
                "question": q,
                "sql": query_result.get("sql_query"),
                "answer": query_result.get("answer"),
                "success": query_result.get("success", False)
            }
            results["steps"].append({"step": "nl_to_sql", "status": "success"})
            
            # Add insight from query
            if query_result.get("answer"):
                ctx.add_insight(
                    "NL-to-SQL",
                    query_result["answer"][:500],
                    category="metrics"
                )
                
        except Exception as e:
            logger.warning(f"NL-to-SQL step failed: {e}")
            results["steps"].append({"step": "nl_to_sql", "status": "failed", "error": str(e)})
            results["errors"].append(f"Query step: {e}")
        
        # Step 3: Generate insights using MediaAnalyticsExpert
        logger.info("Step 2: Generating analysis insights")
        try:
            analyst = _get_media_analytics_expert()
            
            # Use await if async, otherwise call directly
            if asyncio.iscoroutinefunction(analyst.get_rag_summary):
                analysis = await analyst.get_rag_summary(data)
            else:
                analysis = analyst.get_rag_summary(data)
            
            # Cache the result
            ctx.add_data("analysis_result", analysis, source="MediaAnalyticsExpert")
            
            results["insights"] = {
                "executive_summary": analysis.get("executive_summary"),
                "key_findings": analysis.get("key_findings", []),
                "recommendations": analysis.get("recommendations", [])
            }
            results["steps"].append({"step": "media_analytics", "status": "success"})
            
            # Add insights to context
            if analysis.get("executive_summary"):
                ctx.add_insight(
                    "MediaAnalyticsExpert",
                    analysis["executive_summary"],
                    category="analysis"
                )
            
            # Add recommendations to context
            for rec in analysis.get("recommendations", []):
                ctx.add_recommendation(
                    "MediaAnalyticsExpert",
                    rec if isinstance(rec, str) else str(rec),
                    priority="medium"
                )
                results["recommendations"].append(rec)
                
        except Exception as e:
            import traceback
            logger.error(f"MediaAnalyticsExpert step failed: {traceback.format_exc()}")
            results["steps"].append({"step": "media_analytics", "status": "failed", "error": str(e)})
            results["errors"].append(f"Analysis step: {e}")
        
        # Step 4: Enhanced Reasoning (Patterns & Anomalies)
        logger.info("Step 3: Enhanced Reasoning Analysis")
        try:
            reasoner = _get_enhanced_reasoning_agent()
            reasoning_result = reasoner.analyze(data)
            
            ctx.add_data("reasoning_result", reasoning_result, source="EnhancedReasoningAgent")
            
            if reasoning_result.get("patterns"):
                results["patterns"] = reasoning_result["patterns"]
                results["steps"].append({"step": "enhanced_reasoning", "status": "success"})
                
                # Add pattern insights
                for pattern in reasoning_result.get("insights", {}).get("pattern_insights", []):
                    ctx.add_insight(
                        "EnhancedReasoningAgent",
                        pattern,
                        category="pattern"
                    )
            
            # Step 5: B2B/Contextual Analysis
            logger.info("Step 4: Business Context Analysis")
            specialist = _get_b2b_specialist_agent()
            
            # Combine base insights with reasoning
            base_insights = {
                "metrics": results["metrics"],
                "analysis": results["insights"],
                "patterns": reasoning_result.get("patterns")
            }
            
            contextual_result = specialist.enhance_analysis(base_insights, campaign_data=data)
            
            ctx.add_data("contextual_result", contextual_result, source="B2BSpecialistAgent")
            results["business_context"] = contextual_result.get("business_model_analysis")
            results["steps"].append({"step": "b2b_specialist", "status": "success"})
            
            # Add specialist recommendations
            for rec in contextual_result.get("recommendations", []):
                if isinstance(rec, dict) and rec not in results["recommendations"]:
                    rec_str = f"[{rec.get('category', 'General')}] {rec.get('recommendation')}"
                    ctx.add_recommendation("B2BSpecialistAgent", rec_str, priority=rec.get("priority", "medium"))
                    results["recommendations"].append(rec)

        except Exception as e:
            logger.warning(f"Advanced reasoning steps failed: {e}")
            results["steps"].append({"step": "advanced_reasoning", "status": "failed", "error": str(e)})
            results["errors"].append(f"Reasoning step: {e}")

        # Step 6: Budget pacing check (simplified - no agent)
        logger.info("Step 5: Checking budget pacing")
        try:
            if "Total Spent" in data.columns or "Spend" in data.columns:
                total_spend = data["Total Spent"].sum() if "Total Spent" in data.columns else data["Spend"].sum()
                
                pacing_info = {
                    "total_spend": float(total_spend),
                    "status": "on_track" if total_spend > 0 else "no_spend"
                }
                
                results["pacing"] = pacing_info
                results["steps"].append({"step": "pacing_check", "status": "success"})
                
                ctx.add_insight(
                    "PacingCheck",
                    f"Total spend: ${total_spend:,.2f}",
                    category="pacing"
                )
            else:
                results["steps"].append({"step": "pacing_check", "status": "skipped", "reason": "No spend column"})
                
        except Exception as e:
            logger.warning(f"Pacing step failed: {e}")
            results["steps"].append({"step": "pacing_check", "status": "failed", "error": str(e)})
            results["errors"].append(f"Pacing step: {e}")
        
        # Step 5: Synthesize final output
        results["completed_at"] = datetime.utcnow().isoformat()
        results["duration_seconds"] = (datetime.utcnow() - start_time).total_seconds()
        results["context_summary"] = ctx.get_summary()
        
        # Collect all recommendations
        all_recs = ctx.get_recommendations()
        results["all_recommendations"] = [r["recommendation"] for r in all_recs]
        
        # Set success based on at least one step succeeding
        successful_steps = [s for s in results["steps"] if s["status"] == "success"]
        results["success"] = len(successful_steps) > 0
        
        logger.info(f"Campaign Health Check completed in {results['duration_seconds']:.2f}s")
        
    except Exception as e:
        logger.error(f"Campaign Health Check workflow failed: {e}")
        results["success"] = False
        results["errors"].append(str(e))
    
    return results


# =============================================================================
# Chain 2: Deep Analysis (Query + Multi-dimensional Analysis)
# =============================================================================

async def deep_analysis(
    data: pd.DataFrame,
    questions: List[str],
    context: Optional[SharedContext] = None
) -> Dict[str, Any]:
    """
    Deep analysis answering multiple questions.
    
    Args:
        data: Campaign data DataFrame
        questions: List of questions to answer
        context: Optional SharedContext
    
    Returns:
        Answers to all questions with combined insights
    """
    ctx = context or get_shared_context()
    
    results = {
        "workflow": "deep_analysis",
        "questions_answered": [],
        "all_insights": [],
        "success": True
    }
    
    try:
        engine = _get_nl_to_sql_engine()
        engine.load_data(data, "campaigns")
        ctx.add_data("campaign_data", data, source="workflow")
        
        for question in questions:
            try:
                answer = engine.ask(question)
                
                results["questions_answered"].append({
                    "question": question,
                    "answer": answer.get("answer"),
                    "sql": answer.get("sql_query"),
                    "success": answer.get("success", False)
                })
                
                ctx.add_query(question, answer)
                
                if answer.get("answer"):
                    ctx.add_insight("DeepAnalysis", answer["answer"][:300], category="query")
                    results["all_insights"].append(answer["answer"][:300])
                    
            except Exception as e:
                results["questions_answered"].append({
                    "question": question,
                    "error": str(e),
                    "success": False
                })
        
        results["context_summary"] = ctx.get_summary()
        
    except Exception as e:
        results["success"] = False
        results["error"] = str(e)
    
    return results


# =============================================================================
# Chain 3: Quick Insights (Fast single-metric analysis)
# =============================================================================

async def quick_insights(
    data: pd.DataFrame,
    metric: str = "spend",
    context: Optional[SharedContext] = None
) -> Dict[str, Any]:
    """
    Quick insights for a specific metric.
    
    Args:
        data: Campaign data DataFrame
        metric: Metric to analyze (spend, roas, ctr, cpa, conversions)
        context: Optional SharedContext
    
    Returns:
        Quick analysis of the specified metric
    """
    ctx = context or get_shared_context()
    
    metric_questions = {
        "spend": "What is the total spend by platform and what's the trend?",
        "roas": "What is the ROAS by platform and which has the best return?",
        "ctr": "What is the CTR by platform and creative type?",
        "cpa": "What is the CPA by platform and which is most efficient?",
        "conversions": "What are total conversions by platform and funnel stage?"
    }
    
    question = metric_questions.get(metric.lower(), f"Analyze {metric} by platform")
    
    try:
        engine = _get_nl_to_sql_engine()
        engine.load_data(data, "campaigns")
        
        result = engine.ask(question)
        
        ctx.add_query(question, result)
        ctx.add_insight("QuickInsights", result.get("answer", "")[:500], category=metric)
        
        return {
            "workflow": "quick_insights",
            "metric": metric,
            "question": question,
            "answer": result.get("answer"),
            "sql": result.get("sql_query"),
            "success": result.get("success", False)
        }
        
    except Exception as e:
        return {
            "workflow": "quick_insights",
            "metric": metric,
            "success": False,
            "error": str(e)
        }


# =============================================================================
# Convenience Functions
# =============================================================================

def get_workflow_status(context: Optional[SharedContext] = None) -> Dict[str, Any]:
    """Get current workflow status from context"""
    ctx = context or get_shared_context()
    return {
        "context": ctx.get_summary(),
        "insights": ctx.get_insights(),
        "recommendations": ctx.get_recommendations(),
        "anomalies": ctx.get_anomalies(),
        "recent_queries": ctx.get_query_history(limit=5)
    }


def clear_workflow_state() -> None:
    """Clear all workflow state"""
    reset_shared_context()
    
    # Clear semantic cache to ensure fresh RAG retrievals
    try:
        from src.utils.performance import get_optimizer
        get_optimizer().cache.clear()
        logger.info("Semantic cache cleared")
    except Exception as e:
        logger.warning(f"Failed to clear semantic cache: {e}")
        
    logger.info("Workflow state cleared")
