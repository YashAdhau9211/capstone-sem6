"""WebSocket endpoints for real-time updates."""

import asyncio
import logging
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manage WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: Dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, station_id: str):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        if station_id not in self.active_connections:
            self.active_connections[station_id] = []
        self.active_connections[station_id].append(websocket)
        logger.info(f"WebSocket connected for station {station_id}")

    def disconnect(self, websocket: WebSocket, station_id: str):
        """Remove a WebSocket connection."""
        if station_id in self.active_connections:
            self.active_connections[station_id].remove(websocket)
            if not self.active_connections[station_id]:
                del self.active_connections[station_id]
        logger.info(f"WebSocket disconnected for station {station_id}")

    async def send_message(self, message: dict, station_id: str):
        """Send a message to all connections for a station."""
        if station_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[station_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message: {e}")
                    disconnected.append(connection)
            
            # Clean up disconnected connections
            for conn in disconnected:
                self.disconnect(conn, station_id)


manager = ConnectionManager()


@router.websocket("/ws/simulation/{station_id}")
async def simulation_websocket(websocket: WebSocket, station_id: str):
    """
    WebSocket endpoint for real-time counterfactual simulation updates.
    
    Clients connect to this endpoint to receive real-time updates when
    counterfactual simulations are computed. This enables <500ms latency
    for interactive what-if analysis.
    
    **Requirements:** 10.5, 11.1, 11.2
    """
    await manager.connect(websocket, station_id)
    
    try:
        while True:
            # Keep connection alive and listen for client messages
            data = await websocket.receive_json()
            
            # Echo back for testing (in production, this would trigger simulation)
            if data.get("type") == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, station_id)
        logger.info(f"Client disconnected from station {station_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        manager.disconnect(websocket, station_id)


async def broadcast_counterfactual_update(
    station_id: str,
    result: dict,
    latency_ms: float
):
    """
    Broadcast counterfactual simulation results to all connected clients.
    
    This function is called after computing counterfactual predictions
    to push updates to connected WebSocket clients in real-time.
    """
    message = {
        "type": "counterfactual_update",
        "data": {
            "result": result,
            "latency_ms": latency_ms,
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    await manager.send_message(message, station_id)
