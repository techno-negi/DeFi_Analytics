"""
FastAPI middleware for authentication, rate limiting, and logging
"""
import time
import uuid
from typing import Callable
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from collections import defaultdict
from datetime import datetime, timedelta
import logging

from src.config.settings import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests: defaultdict = defaultdict(list)
    
    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed"""
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)
        
        # Clean old requests
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > minute_ago
        ]
        
        # Check limit
        if len(self.requests[client_id]) >= self.requests_per_minute:
            return False
        
        # Add current request
        self.requests[client_id].append(now)
        return True


# Global rate limiter instance
rate_limiter = RateLimiter(requests_per_minute=settings.RATE_LIMIT_PER_MINUTE)


async def rate_limit_middleware(request: Request, call_next: Callable):
    """Rate limiting middleware"""
    
    # Skip rate limiting for health check
    if request.url.path == "/api/health":
        return await call_next(request)
    
    # Get client identifier (IP address or API key)
    client_id = request.client.host
    
    # Check if client has API key
    api_key = request.headers.get("X-API-Key")
    if api_key:
        client_id = f"key_{api_key}"
    
    # Check rate limit
    if not rate_limiter.is_allowed(client_id):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Rate limit exceeded",
                "message": f"Maximum {settings.RATE_LIMIT_PER_MINUTE} requests per minute"
            }
        )
    
    response = await call_next(request)
    
    # Add rate limit headers
    response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_PER_MINUTE)
    response.headers["X-RateLimit-Remaining"] = str(
        settings.RATE_LIMIT_PER_MINUTE - len(rate_limiter.requests[client_id])
    )
    
    return response


async def logging_middleware(request: Request, call_next: Callable):
    """Request/response logging middleware"""
    
    # Generate request ID
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Log request
    start_time = time.time()
    
    logger.info(
        f"Request started",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client": request.client.host
        }
    )
    
    try:
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response
        logger.info(
            f"Request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 2)
            }
        )
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response
        
    except Exception as e:
        duration = time.time() - start_time
        
        logger.error(
            f"Request failed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "duration_ms": round(duration * 1000, 2),
                "error": str(e)
            },
            exc_info=True
        )
        
        raise


async def cors_middleware(request: Request, call_next: Callable):
    """CORS handling middleware (supplemental to FastAPI CORS)"""
    response = await call_next(request)
    
    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    return response


async def error_handling_middleware(request: Request, call_next: Callable):
    """Global error handling middleware"""
    try:
        return await call_next(request)
    except HTTPException:
        # Let FastAPI handle HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "message": "An unexpected error occurred",
                "request_id": getattr(request.state, "request_id", None)
            }
        )


def verify_api_key(api_key: str) -> bool:
    """Verify API key (placeholder - implement actual verification)"""
    # In production, verify against database
    return api_key == settings.SECRET_KEY


async def auth_middleware(request: Request, call_next: Callable):
    """Authentication middleware"""
    
    # Skip auth for public endpoints
    public_paths = ["/api/health", "/api/docs", "/api/redoc", "/api/openapi.json"]
    if any(request.url.path.startswith(path) for path in public_paths):
        return await call_next(request)
    
    # Check for API key or JWT token
    api_key = request.headers.get("X-API-Key")
    auth_header = request.headers.get("Authorization")
    
    if api_key:
        if not verify_api_key(api_key):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "Invalid API key"}
            )
    elif auth_header and auth_header.startswith("Bearer "):
        # JWT token verification (implement as needed)
        pass
    else:
        # For now, allow unauthenticated access
        # In production, uncomment to enforce auth:
        # return JSONResponse(
        #     status_code=status.HTTP_401_UNAUTHORIZED,
        #     content={"error": "Authentication required"}
        # )
        pass
    
    return await call_next(request)
