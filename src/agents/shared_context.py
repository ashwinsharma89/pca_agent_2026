"""
SharedContext - Shared State for Agent Collaboration

This module provides a shared context that allows agents to:
- Share data between each other (avoid redundant queries)
- Store insights from one agent for use by another
- Track anomalies and recommendations across the session
- Maintain conversation history for follow-up questions

Usage:
    context = SharedContext()
    
    # Agent 1 stores query results
    context.add_data("campaign_metrics", df)
    
    # Agent 2 reads the data
    data = context.get_data("campaign_metrics")
    
    # Agent 2 adds insights
    context.add_insight("MediaAnalyticsExpert", "ROAS is declining 15% WoW")
    
    # Agent 3 reads all insights
    all_insights = context.get_insights()
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
import logging

logger = logging.getLogger(__name__)


@dataclass
class ContextEntry:
    """A single entry in the shared context"""
    source: str  # Which agent/component added this
    content: Any  # The actual content
    entry_type: str  # 'data', 'insight', 'anomaly', 'recommendation', 'query'
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SharedContext:
    """
    Shared context for agent collaboration.
    
    Enables agents to:
    - Share query results (avoid repeated DB calls)
    - Accumulate insights from multiple agents
    - Track anomalies detected by any agent
    - Store recommendations for synthesis
    - Remember conversation history
    """
    
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self.created_at = datetime.utcnow()
        
        # Core storage
        self._data_cache: Dict[str, ContextEntry] = {}
        self._insights: List[ContextEntry] = []
        self._anomalies: List[ContextEntry] = []
        self._recommendations: List[ContextEntry] = []
        self._query_history: List[ContextEntry] = []
        
        # Conversation state
        self._current_focus: Optional[str] = None  # e.g., "Google campaigns"
        self._last_query: Optional[str] = None
        self._last_result: Optional[Any] = None
        
        logger.info(f"SharedContext initialized: session={self.session_id}")
    
    # =========================================================================
    # Data Cache (for query results, dataframes)
    # =========================================================================
    
    def add_data(
        self, 
        key: str, 
        data: Any, 
        source: str = "unknown",
        metadata: Dict[str, Any] = None
    ) -> None:
        """
        Cache data for reuse by other agents.
        
        Args:
            key: Unique identifier for this data
            data: The data to cache (DataFrame, dict, list, etc.)
            source: Which agent/component added this
            metadata: Additional context about the data
        """
        entry = ContextEntry(
            source=source,
            content=data,
            entry_type="data",
            metadata=metadata or {}
        )
        self._data_cache[key] = entry
        logger.debug(f"Data cached: key={key}, source={source}")
    
    def get_data(self, key: str) -> Optional[Any]:
        """Get cached data by key"""
        entry = self._data_cache.get(key)
        return entry.content if entry else None
    
    def has_data(self, key: str) -> bool:
        """Check if data exists in cache"""
        return key in self._data_cache
    
    def get_data_keys(self) -> List[str]:
        """List all cached data keys"""
        return list(self._data_cache.keys())
    
    # =========================================================================
    # Insights (from analysis agents)
    # =========================================================================
    
    def add_insight(
        self, 
        source: str, 
        insight: str,
        category: str = "general",
        confidence: float = 1.0,
        metadata: Dict[str, Any] = None
    ) -> None:
        """
        Add an insight from an agent.
        
        Args:
            source: Agent name (e.g., "MediaAnalyticsExpert")
            insight: The insight text
            category: Type of insight (e.g., "performance", "trend", "anomaly")
            confidence: Confidence score 0-1
            metadata: Additional context
        """
        meta = metadata or {}
        meta["category"] = category
        meta["confidence"] = confidence
        
        entry = ContextEntry(
            source=source,
            content=insight,
            entry_type="insight",
            metadata=meta
        )
        self._insights.append(entry)
        if isinstance(insight, str):
            logger.debug(f"Insight added from {source}: {insight[:50]}...")
        else:
            logger.debug(f"Insight added from {source}: {str(insight)[:50]}...")
    
    def get_insights(self, source: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all insights, optionally filtered by source.
        
        Returns:
            List of insight dicts with source, content, timestamp, metadata
        """
        insights = self._insights
        if source:
            insights = [i for i in insights if i.source == source]
        
        return [
            {
                "source": i.source,
                "content": i.content,
                "timestamp": i.timestamp.isoformat(),
                "category": i.metadata.get("category", "general"),
                "confidence": i.metadata.get("confidence", 1.0)
            }
            for i in insights
        ]
    
    # =========================================================================
    # Anomalies (from detection agents)
    # =========================================================================
    
    def add_anomaly(
        self,
        source: str,
        description: str,
        severity: str = "medium",  # low, medium, high, critical
        affected_metric: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> None:
        """
        Record a detected anomaly.
        
        Args:
            source: Agent that detected the anomaly
            description: What was detected
            severity: How serious (low/medium/high/critical)
            affected_metric: Which metric is affected
            metadata: Additional context
        """
        meta = metadata or {}
        meta["severity"] = severity
        meta["affected_metric"] = affected_metric
        
        entry = ContextEntry(
            source=source,
            content=description,
            entry_type="anomaly",
            metadata=meta
        )
        self._anomalies.append(entry)
        logger.info(f"Anomaly detected by {source}: {description}")
    
    def get_anomalies(self, min_severity: str = None) -> List[Dict[str, Any]]:
        """Get all detected anomalies"""
        severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        
        anomalies = self._anomalies
        if min_severity:
            min_level = severity_order.get(min_severity, 0)
            anomalies = [
                a for a in anomalies 
                if severity_order.get(a.metadata.get("severity", "medium"), 1) >= min_level
            ]
        
        return [
            {
                "source": a.source,
                "description": a.content,
                "severity": a.metadata.get("severity", "medium"),
                "affected_metric": a.metadata.get("affected_metric"),
                "timestamp": a.timestamp.isoformat()
            }
            for a in anomalies
        ]
    
    # =========================================================================
    # Recommendations (from recommendation agents)
    # =========================================================================
    
    def add_recommendation(
        self,
        source: str,
        recommendation: str,
        priority: str = "medium",  # low, medium, high
        action_type: str = "optimize",  # optimize, investigate, scale, cut
        metadata: Dict[str, Any] = None
    ) -> None:
        """
        Add a recommendation from an agent.
        
        Args:
            source: Agent providing the recommendation
            recommendation: The recommended action
            priority: Urgency (low/medium/high)
            action_type: Type of action (optimize/investigate/scale/cut)
            metadata: Additional context
        """
        meta = metadata or {}
        meta["priority"] = priority
        meta["action_type"] = action_type
        
        entry = ContextEntry(
            source=source,
            content=recommendation,
            entry_type="recommendation",
            metadata=meta
        )
        self._recommendations.append(entry)
        logger.debug(f"Recommendation from {source}: {recommendation[:50]}...")
    
    def get_recommendations(self, priority: str = None) -> List[Dict[str, Any]]:
        """Get all recommendations"""
        recs = self._recommendations
        if priority:
            recs = [r for r in recs if r.metadata.get("priority") == priority]
        
        return [
            {
                "source": r.source,
                "recommendation": r.content,
                "priority": r.metadata.get("priority", "medium"),
                "action_type": r.metadata.get("action_type", "optimize"),
                "timestamp": r.timestamp.isoformat()
            }
            for r in recs
        ]
    
    # =========================================================================
    # Query History (for conversation context)
    # =========================================================================
    
    def add_query(
        self,
        question: str,
        result: Any,
        source: str = "user"
    ) -> None:
        """Record a query and its result"""
        entry = ContextEntry(
            source=source,
            content={"question": question, "result": result},
            entry_type="query"
        )
        self._query_history.append(entry)
        self._last_query = question
        self._last_result = result
        
        # Update focus based on query
        self._update_focus(question)
    
    def _update_focus(self, question: str) -> None:
        """Infer current focus from question"""
        q_lower = question.lower()
        
        # Platform focus
        platforms = ["google", "meta", "facebook", "linkedin", "tiktok", "snapchat"]
        for platform in platforms:
            if platform in q_lower:
                self._current_focus = f"{platform.title()} campaigns"
                return
        
        # Metric focus
        metrics = ["spend", "roas", "cpa", "ctr", "conversions"]
        for metric in metrics:
            if metric in q_lower:
                self._current_focus = f"{metric.upper()} analysis"
                return
    
    def get_query_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent query history"""
        recent = self._query_history[-limit:]
        return [
            {
                "question": q.content["question"],
                "timestamp": q.timestamp.isoformat()
            }
            for q in recent
        ]
    
    def get_current_focus(self) -> Optional[str]:
        """Get the current conversation focus"""
        return self._current_focus
    
    def get_last_query(self) -> Optional[str]:
        """Get the last question asked"""
        return self._last_query
    
    def get_last_result(self) -> Optional[Any]:
        """Get the last query result"""
        return self._last_result
    
    # =========================================================================
    # Summary & Status
    # =========================================================================
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the current context state"""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "current_focus": self._current_focus,
            "data_cached": len(self._data_cache),
            "insights_count": len(self._insights),
            "anomalies_count": len(self._anomalies),
            "recommendations_count": len(self._recommendations),
            "queries_count": len(self._query_history),
            "data_keys": self.get_data_keys()
        }
    
    def clear(self) -> None:
        """Clear all context (start fresh)"""
        self._data_cache.clear()
        self._insights.clear()
        self._anomalies.clear()
        self._recommendations.clear()
        self._query_history.clear()
        self._current_focus = None
        self._last_query = None
        self._last_result = None
        logger.info(f"SharedContext cleared: session={self.session_id}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Export full context as dictionary"""
        return {
            "summary": self.get_summary(),
            "insights": self.get_insights(),
            "anomalies": self.get_anomalies(),
            "recommendations": self.get_recommendations(),
            "query_history": self.get_query_history(limit=50)
        }


# =============================================================================
# Global Context Instance (session-scoped)
# =============================================================================

_global_context: Optional[SharedContext] = None


def get_shared_context() -> SharedContext:
    """Get or create the global shared context"""
    global _global_context
    if _global_context is None:
        _global_context = SharedContext()
    return _global_context


def reset_shared_context() -> SharedContext:
    """Reset and get a fresh shared context"""
    global _global_context
    _global_context = SharedContext()
    return _global_context
