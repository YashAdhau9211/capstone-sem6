"""Middleware for request processing, logging, and monitoring."""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

import logging

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging all API requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details."""
        # Generate request ID
        request_id = request.headers.get("X-Request-ID", f"req-{int(time.time() * 1000)}")

        # Log request
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host if request.client else None,
            },
        )

        # Process request
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        # Add custom headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)

        # Log response
        logger.info(
            f"Request completed: {request.method} {request.url.path} - "
            f"Status: {response.status_code} - Time: {process_time:.3f}s",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "process_time": process_time,
            },
        )

        # Log slow queries
        if process_time > 0.5:
            logger.warning(
                f"Slow query detected: {request.method} {request.url.path} - {process_time:.3f}s",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "process_time": process_time,
                },
            )

        return response


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for monitoring API performance metrics."""

    def __init__(self, app: Callable) -> None:
        """Initialize performance monitoring middleware."""
        super().__init__(app)
        self.request_count = 0
        self.total_time = 0.0
        self.slow_query_count = 0

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect metrics."""
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        # Update metrics
        self.request_count += 1
        self.total_time += process_time

        # Track slow queries (>500ms)
        if process_time > 0.5:
            self.slow_query_count += 1

        return response

    def get_metrics(self) -> dict:
        """Get current performance metrics."""
        avg_time = self.total_time / self.request_count if self.request_count > 0 else 0
        return {
            "total_requests": self.request_count,
            "average_response_time": avg_time,
            "slow_query_count": self.slow_query_count,
            "slow_query_percentage": (
                (self.slow_query_count / self.request_count * 100)
                if self.request_count > 0
                else 0
            ),
        }
