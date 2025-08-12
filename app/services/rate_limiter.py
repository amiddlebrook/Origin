"""
Rate limiting service for API endpoints.
"""
import time
from typing import Tuple
import asyncio
from collections import defaultdict
from functools import wraps

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.database import get_db
from app.auth.router import get_current_user

class RateLimiter:
    """Rate limiter for API endpoints."""
    
    def __init__(self, app: ASGIApp):
        """Initialize the rate limiter."""
        self.app = app
        # In-memory storage for rate limiting (for development)
        # In production, consider using Redis or similar
        self.rate_limits = defaultdict(list)
        self.lock = asyncio.Lock()
        
        # Default rate limits (requests per minute)
        self.default_limits = {
            "default": (60, 60),  # 60 requests per minute
            "auth": (10, 60),     # 10 requests per minute for auth endpoints
            "search": (30, 60),   # 30 requests per minute for search
            "upload": (10, 60),   # 10 requests per minute for uploads
        }
        
        # Custom rate limits for specific endpoints
        self.endpoint_limits = {
            # Format: "path:method": (requests, seconds)
            "POST:/auth/register": (5, 60 * 60),  # 5 per hour
            "POST:/auth/login": (10, 60),         # 10 per minute
            "POST:/auth/forgot-password": (3, 60 * 60),  # 3 per hour
            "POST:/auth/reset-password": (5, 60 * 60),   # 5 per hour
            "POST:/stories/": (30, 60),            # 30 per minute
            "POST:/oral/upload": (10, 60),         # 10 per minute
            "POST:/media/upload": (20, 60),        # 20 per minute
        }
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI middleware to handle rate limiting."""
        if scope["type"] != "http":  # pragma: no cover
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        
        # Skip rate limiting for certain paths
        if self._should_skip_rate_limiting(request):
            await self.app(scope, receive, send)
            return
        
        # Get the client identifier (IP or user ID)
        client_id = await self._get_client_identifier(request)
        
        # Get the rate limit for this endpoint
        limit_key, (max_requests, time_window) = self._get_rate_limit(request)
        
        # Check if the client has exceeded the rate limit
        async with self.lock:
            current_time = time.time()
            
            # Clean up old requests outside the time window
            self.rate_limits[client_id] = [
                t for t in self.rate_limits[client_id] 
                if current_time - t < time_window
            ]
            
            # Check if the client has exceeded the rate limit
            if len(self.rate_limits[client_id]) >= max_requests:
                # Calculate when the client can make the next request
                retry_after = int(time_window - (current_time - self.rate_limits[client_id][0]))
                
                # Return a 429 Too Many Requests response
                response = JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": f"Rate limit exceeded. Try again in {retry_after} seconds.",
                        "retry_after": retry_after,
                        "limit": max_requests,
                        "window_seconds": time_window,
                    },
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(max_requests),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(current_time + retry_after)),
                        "X-RateLimit-Reset-After": str(retry_after),
                    }
                )
                
                await response(scope, receive, send)
                return
            
            # Add the current request to the rate limit counter
            self.rate_limits[client_id].append(current_time)
        
        # Continue processing the request
        await self.app(scope, receive, send)
    
    async def _get_client_identifier(self, request: Request) -> str:
        """
        Get a unique identifier for the client.
        
        Tries to use the authenticated user ID if available, otherwise falls back to IP.
        """
        try:
            # First try to get the current user
            db = next(get_db())
            current_user = await get_current_user(request, db)
            if current_user:
                return f"user:{current_user.id}"
        except Exception:
            pass
        
        # Fall back to IP address
        if request.client and request.client.host:
            return f"ip:{request.client.host}"
        
        # Fallback to a random string (shouldn't happen in normal operation)
        return "anonymous"
    
    def _get_rate_limit(self, request: Request) -> Tuple[str, Tuple[int, int]]:
        """
        Get the rate limit for the current request.
        
        Returns a tuple of (limit_key, (max_requests, time_window_seconds))
        """
        # Check for endpoint-specific rate limits
        path = request.url.path
        method = request.method.upper()
        endpoint_key = f"{method}:{path}"
        
        # Check for exact match first
        for key, limit in self.endpoint_limits.items():
            if endpoint_key == key:
                return key, limit
        
        # Check for prefix match (e.g., "POST:/auth/")
        for key, limit in self.endpoint_limits.items():
            if endpoint_key.startswith(key.rstrip('*')):
                return key, limit
        
        # Check for category-based limits
        if path.startswith("/auth/"):
            return "auth", self.default_limits["auth"]
        elif path.startswith("/search") or "/search" in path:
            return "search", self.default_limits["search"]
        elif "/upload" in path or "/media" in path:
            return "upload", self.default_limits["upload"]
        
        # Default rate limit
        return "default", self.default_limits["default"]
    
    def _should_skip_rate_limiting(self, request: Request) -> bool:
        """
        Check if rate limiting should be skipped for this request.
        """
        # Skip rate limiting for certain paths
        skip_paths = [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/favicon.ico",
        ]
        
        if any(request.url.path.startswith(path) for path in skip_paths):
            return True
        
        # Skip rate limiting for OPTIONS requests (preflight)
        if request.method.upper() == "OPTIONS":
            return True
        
        # Add more conditions here if needed
        
        return False

def rate_limit(
    max_requests: int = 60,
    time_window: int = 60,
    key_func = None,
    scope: str = None
):
    """
    Decorator to apply rate limiting to a specific endpoint.
    
    Args:
        max_requests: Maximum number of requests allowed in the time window
        time_window: Time window in seconds
        key_func: Optional function to generate a custom rate limit key
        scope: Optional scope for the rate limit (e.g., "user", "ip")
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = None
            
            # Find the request parameter
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                for value in kwargs.values():
                    if isinstance(value, Request):
                        request = value
                        break
            
            if not request:
                # If we can't find the request, just call the function
                return await func(*args, **kwargs)
            
            # Get the rate limiter from the app state
            rate_limiter = request.app.state.rate_limiter
            
            # Generate a rate limit key
            if key_func:
                rate_limit_key = await key_func(request)
            elif scope == "user":
                try:
                    current_user = await get_current_user(request, next(get_db()))
                    rate_limit_key = f"user:{current_user.id}" if current_user else "anonymous"
                except Exception:
                    rate_limit_key = "anonymous"
            elif scope == "ip":
                client = request.client
                rate_limit_key = f"ip:{client.host}" if client and client.host else "unknown"
            else:
                # Default to using the endpoint path as the key
                rate_limit_key = f"endpoint:{request.url.path}"
            
            # Check the rate limit
            async with rate_limiter.lock:
                current_time = time.time()
                
                # Initialize the rate limit data if it doesn't exist
                if rate_limit_key not in rate_limiter.rate_limits:
                    rate_limiter.rate_limits[rate_limit_key] = []
                
                # Clean up old requests outside the time window
                rate_limiter.rate_limits[rate_limit_key] = [
                    t for t in rate_limiter.rate_limits[rate_limit_key] 
                    if current_time - t < time_window
                ]
                
                # Check if the rate limit has been exceeded
                if len(rate_limiter.rate_limits[rate_limit_key]) >= max_requests:
                    # Calculate when the client can make the next request
                    retry_after = int(time_window - (current_time - rate_limiter.rate_limits[rate_limit_key][0]))
                    
                    # Return a 429 Too Many Requests response
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={
                            "detail": f"Rate limit exceeded. Try again in {retry_after} seconds.",
                            "retry_after": retry_after,
                            "limit": max_requests,
                            "window_seconds": time_window,
                        },
                        headers={
                            "Retry-After": str(retry_after),
                            "X-RateLimit-Limit": str(max_requests),
                            "X-RateLimit-Remaining": "0",
                            "X-RateLimit-Reset": str(int(current_time + retry_after)),
                            "X-RateLimit-Reset-After": str(retry_after),
                        }
                    )
                
                # Add the current request to the rate limit counter
                rate_limiter.rate_limits[rate_limit_key].append(current_time)
            
            # Call the original function
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator
