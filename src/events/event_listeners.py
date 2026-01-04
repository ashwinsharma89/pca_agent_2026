"""
Event listeners for monitoring, logging, and metrics.

Provides pre-built listeners for common use cases:
- Logging all events
- Prometheus metrics
- Performance monitoring
- Error tracking
"""

from typing import Dict, Any
from datetime import datetime
from collections import defaultdict
import threading

from src.events.event_types import (
    BaseEvent,
    AgentAnalysisCompleted,
    AgentAnalysisFailed,
    PatternDetected,
    AnomalyDetected,
    RecommendationGenerated,
    SystemError
)
from loguru import logger


# ============================================================================
# Logging Listener
# ============================================================================

class LoggingListener:
    """
    Logs all events to the logger.
    
    Example:
        listener = LoggingListener()
        event_bus.subscribe('*', listener.on_event)
    """
    
    def __init__(self, log_level: str = "INFO"):
        """
        Initialize logging listener.
        
        Args:
            log_level: Log level for events (DEBUG, INFO, WARNING, ERROR)
        """
        self.log_level = log_level.upper()
    
    def on_event(self, event: BaseEvent) -> None:
        """Handle any event by logging it."""
        log_data = {
            'event_type': event.event_type,
            'event_id': event.event_id,
            'timestamp': event.timestamp.isoformat(),
            'priority': event.priority.value
        }
        
        message = f"Event: {event.event_type}"
        
        if self.log_level == "DEBUG":
            logger.debug(message, extra=log_data)
        elif self.log_level == "INFO":
            logger.info(message, extra=log_data)
        elif self.log_level == "WARNING":
            logger.warning(message, extra=log_data)
        elif self.log_level == "ERROR":
            logger.error(message, extra=log_data)


# ============================================================================
# Metrics Listener
# ============================================================================

class MetricsListener:
    """
    Tracks metrics from events.
    
    Maintains counters and histograms for:
    - Event counts by type
    - Agent execution times
    - Pattern detection counts
    - Error rates
    
    Example:
        listener = MetricsListener()
        event_bus.subscribe('*', listener.on_event)
        
        # Get metrics
        stats = listener.get_stats()
    """
    
    def __init__(self):
        """Initialize metrics listener."""
        self._event_counts = defaultdict(int)
        self._execution_times = defaultdict(list)
        self._error_counts = defaultdict(int)
        self._pattern_counts = defaultdict(int)
        self._lock = threading.Lock()
    
    def on_event(self, event: BaseEvent) -> None:
        """Handle event and update metrics."""
        with self._lock:
            # Count event
            self._event_counts[event.event_type] += 1
            
            # Track execution times
            if isinstance(event, AgentAnalysisCompleted):
                self._execution_times[event.agent_name].append(event.execution_time_ms)
            
            # Track errors
            if isinstance(event, (AgentAnalysisFailed, SystemError)):
                self._error_counts[event.event_type] += 1
            
            # Track patterns
            if isinstance(event, PatternDetected):
                self._pattern_counts[event.pattern_type] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get current metrics.
        
        Returns:
            Dictionary with metrics
        """
        with self._lock:
            # Calculate execution time stats
            execution_stats = {}
            for agent_name, times in self._execution_times.items():
                if times:
                    execution_stats[agent_name] = {
                        'count': len(times),
                        'avg_ms': sum(times) / len(times),
                        'min_ms': min(times),
                        'max_ms': max(times)
                    }
            
            return {
                'event_counts': dict(self._event_counts),
                'total_events': sum(self._event_counts.values()),
                'execution_times': execution_stats,
                'error_counts': dict(self._error_counts),
                'total_errors': sum(self._error_counts.values()),
                'pattern_counts': dict(self._pattern_counts),
                'total_patterns': sum(self._pattern_counts.values())
            }
    
    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._event_counts.clear()
            self._execution_times.clear()
            self._error_counts.clear()
            self._pattern_counts.clear()


# ============================================================================
# Prometheus Metrics Listener
# ============================================================================

class PrometheusMetricsListener:
    """
    Updates Prometheus metrics from events.
    
    Example:
        listener = PrometheusMetricsListener()
        event_bus.subscribe('*', listener.on_event)
    """
    
    def __init__(self):
        """Initialize Prometheus metrics listener."""
        try:
            from src.monitoring.prometheus_metrics import (
                record_agent_execution,
                record_agent_confidence,
                record_pattern_detection
            )
            self._record_execution = record_agent_execution
            self._record_confidence = record_agent_confidence
            self._record_pattern = record_pattern_detection
            self._enabled = True
        except ImportError:
            logger.warning("Prometheus metrics not available")
            self._enabled = False
    
    def on_event(self, event: BaseEvent) -> None:
        """Handle event and update Prometheus metrics."""
        if not self._enabled:
            return
        
        try:
            # Agent execution metrics
            if isinstance(event, AgentAnalysisCompleted):
                self._record_execution(
                    agent_name=event.agent_name,
                    duration_ms=event.execution_time_ms,
                    success=True
                )
                self._record_confidence(
                    agent_name=event.agent_name,
                    confidence=event.confidence
                )
            
            elif isinstance(event, AgentAnalysisFailed):
                self._record_execution(
                    agent_name=event.agent_name,
                    duration_ms=0,
                    success=False
                )
            
            # Pattern detection metrics
            elif isinstance(event, PatternDetected):
                self._record_pattern(
                    pattern_type=event.pattern_type,
                    confidence=event.confidence
                )
        
        except Exception as e:
            logger.warning(f"Failed to update Prometheus metrics: {e}")


# ============================================================================
# Alert Listener
# ============================================================================

class AlertListener:
    """
    Sends alerts for critical events.
    
    Example:
        def send_alert(message):
            # Send to Slack, email, etc.
            print(f"ALERT: {message}")
        
        listener = AlertListener(alert_callback=send_alert)
        event_bus.subscribe('*', listener.on_event)
    """
    
    def __init__(self, alert_callback=None):
        """
        Initialize alert listener.
        
        Args:
            alert_callback: Function to call with alert message
        """
        self._alert_callback = alert_callback or self._default_alert
    
    def _default_alert(self, message: str) -> None:
        """Default alert handler (just logs)."""
        logger.warning(f"ALERT: {message}")
    
    def on_event(self, event: BaseEvent) -> None:
        """Handle event and send alerts if needed."""
        # Alert on anomalies
        if isinstance(event, AnomalyDetected):
            message = (
                f"Anomaly detected in {event.metric_name}: "
                f"expected {event.expected_value:.2f}, "
                f"got {event.actual_value:.2f} "
                f"({event.deviation_percentage:.1f}% deviation)"
            )
            self._alert_callback(message)
        
        # Alert on system errors
        elif isinstance(event, SystemError):
            message = (
                f"System error in {event.component}: "
                f"{event.error_type} - {event.error_message}"
            )
            self._alert_callback(message)
        
        # Alert on agent failures
        elif isinstance(event, AgentAnalysisFailed):
            message = (
                f"Agent {event.agent_name} failed: "
                f"{event.error_type} - {event.error_message}"
            )
            self._alert_callback(message)


# ============================================================================
# Event History Listener
# ============================================================================

class EventHistoryListener:
    """
    Stores event history for debugging and analysis.
    
    Example:
        listener = EventHistoryListener(max_events=1000)
        event_bus.subscribe('*', listener.on_event)
        
        # Query history
        recent_errors = listener.get_events_by_type('agent.analysis.failed')
    """
    
    def __init__(self, max_events: int = 10000):
        """
        Initialize event history listener.
        
        Args:
            max_events: Maximum events to store
        """
        self._events = []
        self._max_events = max_events
        self._lock = threading.Lock()
    
    def on_event(self, event: BaseEvent) -> None:
        """Store event in history."""
        with self._lock:
            self._events.append(event)
            if len(self._events) > self._max_events:
                self._events.pop(0)
    
    def get_events_by_type(self, event_type: str) -> list:
        """Get all events of a specific type."""
        with self._lock:
            return [e for e in self._events if e.event_type == event_type]
    
    def get_recent_events(self, limit: int = 100) -> list:
        """Get most recent events."""
        with self._lock:
            return self._events[-limit:]
    
    def clear(self) -> None:
        """Clear event history."""
        with self._lock:
            self._events.clear()


# ============================================================================
# Missing Listeners (Added for DI compatibility)
# ============================================================================

class AnalyticsEventListener(LoggingListener):
    """Listener for analytics-specific events."""
    pass

class MonitoringEventListener(MetricsListener):
    """Listener for monitoring and performance events."""
    pass

class AuditEventListener(LoggingListener):
    """Listener for audit trail events."""
    pass
