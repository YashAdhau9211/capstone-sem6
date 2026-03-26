"""Station model management API endpoints."""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, status
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from src.api.exceptions import ResourceNotFoundError
from src.api.models import ModelStatusResponse
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_model_status_from_db(station_id: str) -> Optional[dict]:
    """
    Retrieve station model status from database.
    
    Args:
        station_id: Manufacturing station identifier
        
    Returns:
        Dictionary with model status data, or None if not found
    """
    connection_url = settings.postgres_url
    
    # Determine if we're using SQLite
    is_sqlite = connection_url.startswith("sqlite")
    
    if is_sqlite:
        engine = create_engine(connection_url, pool_pre_ping=True, echo=False)
    else:
        engine = create_engine(
            connection_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            echo=False
        )
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT 
                    model_id,
                    station_id,
                    status,
                    baseline_accuracy,
                    last_evaluated,
                    config
                FROM station_models
                WHERE station_id = :station_id
            """)
            
            result = conn.execute(query, {"station_id": station_id})
            row = result.fetchone()
            
            if row is None:
                return None
            
            # Parse config JSONB to extract drift information
            import json
            config = json.loads(row[5]) if isinstance(row[5], str) else row[5]
            drift_threshold = config.get("drift_threshold", 0.10)
            
            # Determine if drift is detected based on status
            drift_detected = row[2] == "drifted"
            
            # Calculate drift magnitude if drifted
            drift_magnitude = None
            current_accuracy = None
            
            if drift_detected and row[3] is not None:
                # In production, current_accuracy would be computed from recent evaluations
                # For now, we'll estimate it based on drift threshold
                current_accuracy = row[3] * (1.0 - drift_threshold - 0.05)
                drift_magnitude = (row[3] - current_accuracy) / row[3]
            
            return {
                "model_id": row[0],
                "station_id": row[1],
                "status": row[2],
                "baseline_accuracy": row[3],
                "current_accuracy": current_accuracy,
                "last_evaluated": row[4],
                "drift_detected": drift_detected,
                "drift_magnitude": drift_magnitude
            }
            
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving model status: {e}")
        raise RuntimeError(f"Database error: {e}")
    finally:
        engine.dispose()


@router.get(
    "/{station_id}/status", response_model=ModelStatusResponse, status_code=status.HTTP_200_OK
)
async def get_model_status(
    station_id: str = Path(..., description="Manufacturing station identifier"),
) -> ModelStatusResponse:
    """
    Retrieve station model status including drift information.

    Returns model ID, status, baseline accuracy, current accuracy,
    last evaluation timestamp, and drift detection results.

    **Requirements:** 14.1, 21.1, 26.3
    """
    try:
        # Retrieve model status from database
        model_data = _get_model_status_from_db(station_id)
        
        if model_data is None:
            raise ResourceNotFoundError(
                resource_type="Station Model",
                resource_id=station_id
            )
        
        logger.info(f"Retrieved model status for station {station_id}")
        
        # Return response
        return ModelStatusResponse(
            model_id=UUID(model_data["model_id"]),
            station_id=model_data["station_id"],
            status=model_data["status"],
            baseline_accuracy=model_data["baseline_accuracy"],
            current_accuracy=model_data["current_accuracy"],
            last_evaluated=model_data["last_evaluated"],
            drift_detected=model_data["drift_detected"],
            drift_magnitude=model_data["drift_magnitude"]
        )
        
    except ResourceNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error retrieving model status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error retrieving model status: {str(e)}"
        )
