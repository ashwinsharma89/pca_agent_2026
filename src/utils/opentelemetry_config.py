"""
OpenTelemetry Configuration for PCA Agent.

Provides distributed tracing with OpenTelemetry standard.
Supports Jaeger, OTLP, and other exporters.
"""

import os
from typing import Optional

from loguru import logger

# OpenTelemetry imports
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    
    # Exporters
    try:
        from opentelemetry.exporter.jaeger.thrift import JaegerExporter
        JAEGER_AVAILABLE = True
    except ImportError:
        JAEGER_AVAILABLE = False
    
    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        OTLP_AVAILABLE = True
    except ImportError:
        OTLP_AVAILABLE = False
    
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    logger.warning("OpenTelemetry not installed. Distributed tracing disabled.")


class OpenTelemetryConfig:
    """OpenTelemetry configuration and setup."""
    
    def __init__(self):
        """Initialize OpenTelemetry configuration."""
        self.enabled = os.getenv("OPENTELEMETRY_ENABLED", "false").lower() == "true"
        self.service_name = os.getenv("OTEL_SERVICE_NAME", "pca-agent")
        self.exporter_type = os.getenv("OTEL_EXPORTER_TYPE", "jaeger")  # jaeger, otlp, console
        
        # Jaeger configuration
        self.jaeger_host = os.getenv("JAEGER_HOST", "localhost")
        self.jaeger_port = int(os.getenv("JAEGER_PORT", "6831"))
        
        # OTLP configuration
        self.otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        
        # Instrumentation flags
        self.instrument_fastapi = os.getenv("OTEL_INSTRUMENT_FASTAPI", "true").lower() == "true"
        self.instrument_sqlalchemy = os.getenv("OTEL_INSTRUMENT_SQLALCHEMY", "true").lower() == "true"
        self.instrument_redis = os.getenv("OTEL_INSTRUMENT_REDIS", "true").lower() == "true"
        self.instrument_requests = os.getenv("OTEL_INSTRUMENT_REQUESTS", "true").lower() == "true"
        
        self.tracer_provider: Optional[TracerProvider] = None
    
    def setup_tracer_provider(self):
        """Set up the tracer provider with configured exporter."""
        if not OPENTELEMETRY_AVAILABLE:
            logger.warning("OpenTelemetry not available. Skipping tracer setup.")
            return
        
        # Create resource
        resource = Resource(attributes={
            SERVICE_NAME: self.service_name
        })
        
        # Create tracer provider
        self.tracer_provider = TracerProvider(resource=resource)
        
        # Configure exporter
        exporter = self._get_exporter()
        if exporter:
            span_processor = BatchSpanProcessor(exporter)
            self.tracer_provider.add_span_processor(span_processor)
        
        # Set global tracer provider
        trace.set_tracer_provider(self.tracer_provider)
        
        logger.info(f"OpenTelemetry tracer provider configured with {self.exporter_type} exporter")
    
    def _get_exporter(self):
        """Get the configured span exporter."""
        if self.exporter_type == "jaeger":
            if not JAEGER_AVAILABLE:
                logger.error("Jaeger exporter not available. Install: pip install opentelemetry-exporter-jaeger")
                return ConsoleSpanExporter()
            
            try:
                return JaegerExporter(
                    agent_host_name=self.jaeger_host,
                    agent_port=self.jaeger_port,
                )
            except Exception as e:
                logger.error(f"Failed to create Jaeger exporter: {e}")
                return ConsoleSpanExporter()
        
        elif self.exporter_type == "otlp":
            if not OTLP_AVAILABLE:
                logger.error("OTLP exporter not available. Install: pip install opentelemetry-exporter-otlp")
                return ConsoleSpanExporter()
            
            try:
                return OTLPSpanExporter(endpoint=self.otlp_endpoint)
            except Exception as e:
                logger.error(f"Failed to create OTLP exporter: {e}")
                return ConsoleSpanExporter()
        
        elif self.exporter_type == "console":
            return ConsoleSpanExporter()
        
        else:
            logger.warning(f"Unknown exporter type: {self.exporter_type}. Using console exporter.")
            return ConsoleSpanExporter()
    
    def instrument_app(self, app):
        """Instrument FastAPI application."""
        if not OPENTELEMETRY_AVAILABLE or not self.enabled:
            logger.info("OpenTelemetry disabled or not available")
            return
        
        try:
            # Set up tracer provider
            self.setup_tracer_provider()
            
            # Instrument FastAPI
            if self.instrument_fastapi:
                FastAPIInstrumentor.instrument_app(app)
                logger.info("FastAPI instrumented with OpenTelemetry")
            
            # Instrument SQLAlchemy
            if self.instrument_sqlalchemy:
                SQLAlchemyInstrumentor().instrument()
                logger.info("SQLAlchemy instrumented with OpenTelemetry")
            
            # Instrument Redis
            if self.instrument_redis:
                try:
                    RedisInstrumentor().instrument()
                    logger.info("Redis instrumented with OpenTelemetry")
                except Exception as e:
                    logger.warning(f"Failed to instrument Redis: {e}")
            
            # Instrument Requests
            if self.instrument_requests:
                RequestsInstrumentor().instrument()
                logger.info("Requests library instrumented with OpenTelemetry")

            # Instrument LangChain (Manually added for Phase 4)
            # This captures LangGraph execution steps as spans
            try:
                from opentelemetry.instrumentation.langchain import LangChainInstrumentor
                LangChainInstrumentor().instrument()
                logger.info("LangChain/LangGraph instrumented with OpenTelemetry")
            except ImportError:
                logger.warning("opentelemetry-instrumentation-langchain not installed. Agent tracing disabled.")
            except Exception as e:
                logger.warning(f"Failed to instrument LangChain: {e}")
            
            logger.info("OpenTelemetry instrumentation complete")
            
        except Exception as e:
            logger.error(f"Failed to instrument app with OpenTelemetry: {e}")
    
    def get_tracer(self, name: str = __name__):
        """Get a tracer instance."""
        if not OPENTELEMETRY_AVAILABLE or not self.enabled:
            return None
        
        return trace.get_tracer(name)
    
    def shutdown(self):
        """Shutdown tracer provider and flush spans."""
        if self.tracer_provider:
            try:
                self.tracer_provider.shutdown()
                logger.info("OpenTelemetry tracer provider shutdown complete")
            except Exception as e:
                logger.error(f"Error shutting down tracer provider: {e}")


# Global instance
_otel_config: Optional[OpenTelemetryConfig] = None


def get_otel_config() -> OpenTelemetryConfig:
    """Get global OpenTelemetry configuration instance."""
    global _otel_config
    if _otel_config is None:
        _otel_config = OpenTelemetryConfig()
    return _otel_config


def setup_opentelemetry(app):
    """
    Set up OpenTelemetry for FastAPI application.
    
    Args:
        app: FastAPI application instance
    
    Environment Variables:
        OPENTELEMETRY_ENABLED: Enable OpenTelemetry (default: false)
        OTEL_SERVICE_NAME: Service name (default: pca-agent)
        OTEL_EXPORTER_TYPE: Exporter type - jaeger, otlp, console (default: jaeger)
        JAEGER_HOST: Jaeger agent host (default: localhost)
        JAEGER_PORT: Jaeger agent port (default: 6831)
        OTEL_EXPORTER_OTLP_ENDPOINT: OTLP endpoint (default: http://localhost:4317)
    
    Example:
        from src.utils.opentelemetry_config import setup_opentelemetry
        
        app = FastAPI()
        setup_opentelemetry(app)
    """
    config = get_otel_config()
    config.instrument_app(app)


def get_tracer(name: str = __name__):
    """
    Get a tracer instance for manual instrumentation.
    
    Args:
        name: Tracer name (usually __name__)
    
    Returns:
        Tracer instance or None if OpenTelemetry disabled
    
    Example:
        from src.utils.opentelemetry_config import get_tracer
        
        tracer = get_tracer(__name__)
        
        if tracer:
            with tracer.start_as_current_span("my_operation"):
                # Your code here
                pass
    """
    config = get_otel_config()
    return config.get_tracer(name)


def shutdown_opentelemetry():
    """Shutdown OpenTelemetry and flush spans."""
    config = get_otel_config()
    config.shutdown()


# Alias for main.py compatibility
instrument_app = setup_opentelemetry
