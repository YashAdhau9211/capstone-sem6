"""API v1 router initialization."""

from fastapi import APIRouter

from src.api.v1 import causal, dags, discovery, models, rca, scenarios, simulation, websocket

# Create v1 API router
api_router = APIRouter(prefix="/api/v1")

# Include sub-routers
api_router.include_router(causal.router, prefix="/causal", tags=["causal"])
api_router.include_router(simulation.router, prefix="/simulation", tags=["simulation"])
api_router.include_router(scenarios.router, prefix="/scenarios", tags=["scenarios"])
api_router.include_router(rca.router, prefix="/rca", tags=["rca"])
api_router.include_router(models.router, prefix="/models", tags=["models"])
api_router.include_router(dags.router, prefix="/dags", tags=["dags"])
api_router.include_router(discovery.router, prefix="/discovery", tags=["discovery"])

# WebSocket router (no prefix needed as it's defined in the router itself)
api_router.include_router(websocket.router, tags=["websocket"])

__all__ = ["api_router"]
