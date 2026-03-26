"""Custom exceptions and exception handlers for the API."""

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse


class APIException(HTTPException):
    """Base API exception."""

    def __init__(
        self,
        status_code: int,
        error: str,
        message: str,
        detail: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize API exception."""
        super().__init__(status_code=status_code, detail=message)
        self.error = error
        self.message = message
        self.detail = detail


class ResourceNotFoundError(APIException):
    """Resource not found exception."""

    def __init__(self, resource_type: str, resource_id: str) -> None:
        """Initialize resource not found exception."""
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error="ResourceNotFound",
            message=f"{resource_type} with ID '{resource_id}' not found",
            detail={"resource_type": resource_type, "resource_id": resource_id},
        )


class ValidationError(APIException):
    """Validation error exception."""

    def __init__(self, message: str, detail: Optional[Dict[str, Any]] = None) -> None:
        """Initialize validation error exception."""
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error="ValidationError",
            message=message,
            detail=detail,
        )


class UnauthorizedError(APIException):
    """Unauthorized access exception."""

    def __init__(self, message: str = "Unauthorized access") -> None:
        """Initialize unauthorized error exception."""
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error="Unauthorized",
            message=message,
        )


class ForbiddenError(APIException):
    """Forbidden access exception."""

    def __init__(self, message: str = "Forbidden: insufficient permissions") -> None:
        """Initialize forbidden error exception."""
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error="Forbidden",
            message=message,
        )


class RateLimitExceededError(APIException):
    """Rate limit exceeded exception."""

    def __init__(self, retry_after: int = 60) -> None:
        """Initialize rate limit exceeded exception."""
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error="RateLimitExceeded",
            message="Rate limit exceeded. Please try again later.",
            detail={"retry_after_seconds": retry_after},
        )


class InternalServerError(APIException):
    """Internal server error exception."""

    def __init__(self, message: str = "Internal server error occurred") -> None:
        """Initialize internal server error exception."""
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error="InternalServerError",
            message=message,
        )


class ServiceUnavailableError(APIException):
    """Service unavailable exception."""

    def __init__(self, message: str = "Service temporarily unavailable") -> None:
        """Initialize service unavailable exception."""
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error="ServiceUnavailable",
            message=message,
        )


async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """Handle API exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error,
            "message": exc.message,
            "detail": exc.detail,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle generic exceptions."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "detail": {"exception_type": type(exc).__name__},
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions."""
    # Don't handle APIException here - let the APIException handler deal with it
    if isinstance(exc, APIException):
        return await api_exception_handler(request, exc)
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": f"HTTP{exc.status_code}",
            "message": str(exc.detail),
            "detail": None,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )
