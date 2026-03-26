"""Rate limiting middleware and utilities."""

import time
from collections import defaultdict
from typing import Callable, Dict, Tuple

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.exceptions import RateLimitExceededError


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, rate: int = 1000, per: int = 60) -> None:
        """
        Initialize rate limiter.

        Args:
            rate: Maximum number of requests allowed
            per: Time period in seconds
        """
        self.rate = rate
        self.per = per
        self.allowance: Dict[str, float] = defaultdict(lambda: float(rate))
        self.last_check: Dict[str, float] = defaultdict(lambda: time.time())

    def is_allowed(self, client_id: str) -> Tuple[bool, int]:
        """
        Check if request is allowed for client.

        Uses token bucket algorithm for rate limiting.

        Args:
            client_id: Client identifier (IP address or API key)

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        current = time.time()
        time_passed = current - self.last_check[client_id]
        self.last_check[client_id] = current

        # Refill tokens based on time passed
        self.allowance[client_id] += time_passed * (self.rate / self.per)

        # Cap at maximum rate
        if self.allowance[client_id] > self.rate:
            self.allowance[client_id] = self.rate

        # Check if request is allowed
        if self.allowance[client_id] < 1.0:
            # Calculate retry after time
            retry_after = int((1.0 - self.allowance[client_id]) / (self.rate / self.per))
            return False, retry_after
        else:
            # Consume one token
            self.allowance[client_id] -= 1.0
            return True, 0

    def reset(self, client_id: str) -> None:
        """Reset rate limit for client."""
        self.allowance[client_id] = float(self.rate)
        self.last_check[client_id] = time.time()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting API requests."""

    def __init__(self, app: Callable, rate: int = 1000, per: int = 60) -> None:
        """
        Initialize rate limit middleware.

        Args:
            app: FastAPI application
            rate: Maximum requests per time period (default: 1000)
            per: Time period in seconds (default: 60)
        """
        super().__init__(app)
        self.rate_limiter = RateLimiter(rate=rate, per=per)

    def get_client_id(self, request: Request) -> str:
        """
        Get client identifier from request.

        Uses API key if available, otherwise falls back to IP address.

        Args:
            request: FastAPI request

        Returns:
            Client identifier string
        """
        # Try to get API key from header
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api_key:{api_key}"

        # Try to get bearer token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            return f"token:{token}"

        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with rate limiting.

        Args:
            request: FastAPI request
            call_next: Next middleware in chain

        Returns:
            Response

        Raises:
            RateLimitExceededError: If rate limit exceeded
        """
        # Skip rate limiting for health check endpoints
        if request.url.path in ["/health", "/", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # Get client identifier
        client_id = self.get_client_id(request)

        # Check rate limit
        is_allowed, retry_after = self.rate_limiter.is_allowed(client_id)

        if not is_allowed:
            raise RateLimitExceededError(retry_after=retry_after)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.rate_limiter.rate)
        response.headers["X-RateLimit-Remaining"] = str(int(self.rate_limiter.allowance[client_id]))
        response.headers["X-RateLimit-Reset"] = str(
            int(self.rate_limiter.last_check[client_id] + self.rate_limiter.per)
        )

        return response
