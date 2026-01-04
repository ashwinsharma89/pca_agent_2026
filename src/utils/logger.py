"""
Logging configuration using Loguru with production features.
Features: Log rotation, JSON format, centralized logging support
"""
import sys
import os
import json
from pathlib import Path
from loguru import logger
from datetime import datetime

from ..config.settings import settings


# Environment configuration
LOG_FORMAT = os.getenv("LOG_FORMAT", "text")  # "json" or "text"
LOKI_URL = os.getenv("LOKI_URL", "")


def json_serializer(record):
    """Serialize log record to JSON for ELK/Loki compatibility"""
    subset = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "module": record["module"],
        "function": record["function"],
        "line": record["line"],
    }
    
    # Add exception info
    if record["exception"]:
        subset["exception"] = str(record["exception"])
    
    # Add extra fields
    if record["extra"]:
        subset.update(record["extra"])
    
    return json.dumps(subset, default=str)


def json_sink(message):
    """JSON sink for structured logging"""
    record = message.record
    serialized = json_serializer(record)
    print(serialized)


def setup_logger(name: str = None):
    """
    Configure loguru logger with file rotation and optional JSON format.
    
    Features:
    - Console output (colored text)
    - File rotation (daily, 30 day retention, compressed)
    - Error file (90 day retention)
    - Optional JSON format for ELK/Loki
    - Centralized logging support
    """
    
    logger.remove()
    
    # Console handler configuration
    if LOG_FORMAT == "json":
        logger.add(
            sys.stdout,
            serialize=True,
            level="DEBUG" if settings.debug else "INFO",
        )
    else:
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="DEBUG" if settings.debug else "INFO",
            colorize=True
        )
    
    # Create log directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # File format based on environment
    if LOG_FORMAT == "json":
        file_format = "{message}"
        serialize = True
    else:
        file_format = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
        serialize = False
    
    # File handler - general logs (size rotation)
    logger.add(
        log_dir / "app.log",
        rotation="10 MB",
        retention=10,
        compression="zip",
        format=file_format,
        serialize=serialize,
        level="DEBUG"
    )
    
    # File handler - daily logs (time rotation)
    logger.add(
        log_dir / "pca_agent_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        compression="zip",
        format=file_format,
        serialize=serialize,
        level="DEBUG"
    )
    
    # File handler - errors only
    logger.add(
        log_dir / "errors.log",
        rotation="00:00",
        retention="90 days",
        compression="zip",
        format=file_format,
        serialize=serialize,
        level="ERROR"
    )
    
    # Loki handler (if configured)
    if LOKI_URL:
        try:
            import logging_loki
            handler = logging_loki.LokiHandler(
                url=LOKI_URL,
                tags={"app": "pca-agent"},
                version="1"
            )
            logger.add(handler, level="INFO")
            logger.info(f"Loki logging enabled: {LOKI_URL}")
        except ImportError:
            logger.warning("python-logging-loki not installed, Loki disabled")
    
    logger.info("Logger initialized with production features")
    
    # Return named logger if requested
    if name:
        return logger.bind(name=name)
    return logger


# Convenience function for request context logging
def get_request_logger(request_id: str = None, user_id: str = None):
    """Get logger with request context bound"""
    return logger.bind(request_id=request_id, user_id=user_id)


# Initialize logger on import
setup_logger()
