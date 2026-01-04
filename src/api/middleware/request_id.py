import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from fastapi import Request
from loguru import logger

class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add a unique request ID to every request.
    It binds the request_id to the logger context.
    """
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        # reuse existing request_id or generate new one
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Bind request_id to loguru context
        with info_context(request_id=request_id):
            # Also attach to request state for access in endpoints
            request.state.request_id = request_id
            
            response = await call_next(request)
            
            # Add header to response
            response.headers["X-Request-ID"] = request_id
            
            return response

from contextlib import contextmanager

@contextmanager
def info_context(**kwargs):
    """Context manager for binding context to loguru logger"""
    token = logger.contextualize(**kwargs)
    try:
        yield
    finally:
        logger.reset_context(token)
