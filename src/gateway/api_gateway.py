"""
API Gateway - Lightweight Security & Rate Limiting
Optimized for low traffic (3 req/min) and free infrastructure
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List
import time
import logging
from pydantic import ValidationError
from fastapi.exceptions import RequestValidationError

logger = logging.getLogger(__name__)

# In-memory rate limiting (fine for low traffic)
rate_limit_storage: Dict[str, List[datetime]] = defaultdict(list)

class APIGateway:
    """Lightweight API Gateway for security and rate limiting"""
    
    def __init__(self, app):
        self.app = app
        self.rate_limit_per_minute = 100  # Generous for 3 req/min expected
        self.public_paths = ["/health", "/docs", "/openapi.json", "/api/docs"]
        self.setup_middleware()
    
    def setup_middleware(self):
        """Setup gateway middleware"""
        
        @self.app.middleware("http")
        async def gateway_middleware(request: Request, call_next):
            start_time = time.time()
            logger.info(f"Incoming {request.method} {request.url.path} from {request.client.host if request.client else 'unknown'}")
            
            # Skip gateway for public endpoints
            if any(request.url.path.startswith(path) for path in self.public_paths):
                return await call_next(request)
            
            try:
                # 1. Rate Limiting
                if not self._check_rate_limit(request):
                    logger.warning(f"Rate limit exceeded for {request.client.host}")
                    return JSONResponse(
                        status_code=429,
                        content={
                            "error": "Too many requests",
                            "code": "RATE_LIMIT_EXCEEDED",
                            "retry_after": 60
                        }
                    )
                
                # 2. Basic Authentication Check
                if not self._check_auth(request):
                    logger.warning(f"Unauthorized request from {request.client.host}")
                    return JSONResponse(
                        status_code=401,
                        content={
                            "error": "Unauthorized",
                            "code": "AUTH_REQUIRED"
                        }
                    )
                
                # 3. Request Validation
                if not self._validate_request(request):
                    return JSONResponse(
                        status_code=400,
                        content={
                            "error": "Invalid request",
                            "code": "INVALID_REQUEST"
                        }
                    )
                
                # 4. Process request
                response = await call_next(request)
                
                # 5. Add gateway headers
                processing_time = time.time() - start_time
                response.headers["X-Gateway-Time"] = f"{processing_time:.3f}"
                response.headers["X-Gateway-Version"] = "1.0"
                response.headers["X-RateLimit-Remaining"] = str(
                    self.rate_limit_per_minute - len(rate_limit_storage.get(request.client.host, []))
                )
                
                logger.info(f"{request.method} {request.url.path} - {response.status_code} - {processing_time:.3f}s")
                
                return response
                
            except (ValidationError, RequestValidationError) as e:
                logger.warning(f"Validation error: {e}")
                return JSONResponse(
                    status_code=422,
                    content={
                        "error": "Validation Error",
                        "code": "VALIDATION_ERROR",
                        "details": str(e)
                    }
                )
            except Exception as e:
                logger.error(f"Gateway error: {e}", exc_info=True)
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": "Internal gateway error",
                        "code": "GATEWAY_ERROR"
                    }
                )
    
    def _check_rate_limit(self, request: Request) -> bool:
        """Check rate limit (in-memory, fine for low traffic)"""
        client_ip = request.client.host
        now = datetime.now()
        
        # Clean old requests (older than 1 minute)
        rate_limit_storage[client_ip] = [
            req_time for req_time in rate_limit_storage[client_ip]
            if now - req_time < timedelta(minutes=1)
        ]
        
        # Check limit
        if len(rate_limit_storage[client_ip]) >= self.rate_limit_per_minute:
            return False
        
        # Record this request
        rate_limit_storage[client_ip].append(now)
        return True
    
    def _check_auth(self, request: Request) -> bool:
        """Basic authentication check"""
        # For now, just check if Authorization header exists
        # You can enhance this with JWT validation
        auth_header = request.headers.get("Authorization")
        
        # Allow requests without auth for development
        # In production, enforce this strictly
        if not auth_header:
            # Log but allow (for development)
            logger.debug(f"Request without auth header: {request.url.path}")
            return True
        
        # If auth header exists, validate it
        if not auth_header.startswith("Bearer "):
            return False
        
        # Add JWT validation here if needed
        return True
    
    def _validate_request(self, request: Request) -> bool:
        """Validate request"""
        # Add custom validation logic here
        # For now, just basic checks
        
        # Check content-type for POST/PUT
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            if not content_type:
                logger.warning(f"Missing content-type for {request.method} request")
                # Allow for now, but log
        
        return True
    
    def get_stats(self) -> dict:
        """Get gateway statistics"""
        total_clients = len(rate_limit_storage)
        total_requests = sum(len(requests) for requests in rate_limit_storage.values())
        
        return {
            "total_clients": total_clients,
            "total_requests_last_minute": total_requests,
            "rate_limit_per_minute": self.rate_limit_per_minute
        }
