"""Main application entry point."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.exceptions import (
    APIException,
    api_exception_handler,
    generic_exception_handler,
    http_exception_handler,
)
from src.api.middleware import PerformanceMonitoringMiddleware, RequestLoggingMiddleware
from src.api.models import HealthResponse
from src.api.v1 import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def not_found_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle 404 Not Found errors."""
    # Check if this is a ResourceNotFoundError (which is also an HTTPException)
    if isinstance(exc, APIException):
        return await api_exception_handler(request, exc)
    
    return JSONResponse(
        status_code=404,
        content={
            "error": "HTTP404",
            "message": "Not Found",
            "detail": None,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Causal AI Manufacturing Platform API")
    yield
    # Shutdown
    logger.info("Shutting down Causal AI Manufacturing Platform API")


# Create FastAPI application with OpenAPI 3.0 documentation
app = FastAPI(
    title="Causal AI Manufacturing Platform",
    description=(
        "Enterprise-grade decision intelligence system for manufacturing operations. "
        "Provides automated causal discovery, counterfactual simulation, "
        "root cause analysis, and optimization recommendations."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "health",
            "description": "Health check and system status endpoints",
        },
        {
            "name": "causal",
            "description": "Causal effect estimation endpoints",
        },
        {
            "name": "simulation",
            "description": "Counterfactual simulation endpoints",
        },
        {
            "name": "scenarios",
            "description": "Simulation scenario management endpoints",
        },
        {
            "name": "rca",
            "description": "Root cause analysis endpoints",
        },
        {
            "name": "models",
            "description": "Station model management endpoints",
        },
        {
            "name": "dags",
            "description": "Causal DAG management endpoints",
        },
        {
            "name": "discovery",
            "description": "Causal discovery job endpoints",
        },
        {
            "name": "optimization",
            "description": "Energy and yield optimization recommendation endpoints",
        },
        {
            "name": "websocket",
            "description": "WebSocket endpoints for real-time updates",
        },
    ],
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware (1000 requests/minute per client)
from src.api.rate_limit import RateLimitMiddleware

app.add_middleware(RateLimitMiddleware, rate=1000, per=60)

# Add custom middleware
app.add_middleware(RequestLoggingMiddleware)
performance_middleware = PerformanceMonitoringMiddleware(app)
app.add_middleware(PerformanceMonitoringMiddleware)

# Register exception handlers
app.add_exception_handler(APIException, api_exception_handler)
app.add_exception_handler(404, not_found_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Include API v1 router
app.include_router(api_router)


@app.get("/", tags=["health"])
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "name": "Causal AI Manufacturing Platform API",
        "version": "1.0.0",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
    )


@app.get("/metrics", tags=["health"])
async def metrics() -> dict:
    """Get API performance metrics."""
    return performance_middleware.get_metrics()
