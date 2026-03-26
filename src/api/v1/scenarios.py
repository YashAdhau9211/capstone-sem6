"""Scenario management API endpoints."""

import logging
from datetime import datetime
from typing import List
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Path, Query, status

from src.api.exceptions import ResourceNotFoundError, ValidationError
from src.models.timeseries import SimulationScenario

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory storage for scenarios (in production, use database)
_scenarios_store: dict[str, SimulationScenario] = {}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def save_scenario(request: dict) -> dict:
    """
    Save a simulation scenario for later comparison.
    
    **Requirements:** 10.6
    """
    try:
        scenario_id = str(uuid4())
        
        scenario = SimulationScenario(
            scenario_id=scenario_id,
            station_id=request["station_id"],
            interventions=request["interventions"],
            factual_outcomes=request["factual_outcomes"],
            counterfactual_outcomes=request["counterfactual_outcomes"],
            differences=request["differences"],
            confidence_intervals=request["confidence_intervals"],
            timestamp=datetime.utcnow(),
            description=request.get("description", ""),
            metadata={"created_by": request.get("created_by", "unknown"), "name": request.get("name", "Unnamed")}
        )
        
        _scenarios_store[scenario_id] = scenario
        
        logger.info(f"Saved scenario {scenario_id} for station {request['station_id']}")
        
        return {
            "scenario_id": scenario_id,
            "station_id": scenario.station_id,
            "name": scenario.metadata.get("name", "Unnamed"),
            "description": scenario.description,
            "interventions": scenario.interventions,
            "factual_outcomes": scenario.factual_outcomes,
            "counterfactual_outcomes": scenario.counterfactual_outcomes,
            "differences": scenario.differences,
            "confidence_intervals": scenario.confidence_intervals,
            "created_by": scenario.metadata.get("created_by", "unknown"),
            "created_at": scenario.timestamp.isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Error saving scenario: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save scenario: {str(e)}"
        )


@router.get("/")
async def list_scenarios(station_id: str | None = Query(None)) -> List[dict]:
    """
    List all saved scenarios, optionally filtered by station.
    
    **Requirements:** 10.6
    """
    try:
        scenarios = list(_scenarios_store.values())
        
        if station_id:
            scenarios = [s for s in scenarios if s.station_id == station_id]
        
        return [
            {
                "scenario_id": s.scenario_id,
                "station_id": s.station_id,
                "name": s.metadata.get("name", "Unnamed"),
                "description": s.description,
                "interventions": s.interventions,
                "factual_outcomes": s.factual_outcomes,
                "counterfactual_outcomes": s.counterfactual_outcomes,
                "differences": s.differences,
                "confidence_intervals": s.confidence_intervals,
                "created_by": s.metadata.get("created_by", "unknown"),
                "created_at": s.timestamp.isoformat() if s.timestamp else None,
            }
            for s in scenarios
        ]
        
    except Exception as e:
        logger.error(f"Error listing scenarios: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list scenarios: {str(e)}"
        )


@router.get("/{scenario_id}")
async def get_scenario(scenario_id: str = Path(...)) -> dict:
    """
    Get a specific scenario by ID.
    
    **Requirements:** 10.6
    """
    if scenario_id not in _scenarios_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario {scenario_id} not found"
        )
    
    s = _scenarios_store[scenario_id]
    return {
        "scenario_id": s.scenario_id,
        "station_id": s.station_id,
        "name": s.metadata.get("name", "Unnamed"),
        "description": s.description,
        "interventions": s.interventions,
        "factual_outcomes": s.factual_outcomes,
        "counterfactual_outcomes": s.counterfactual_outcomes,
        "differences": s.differences,
        "confidence_intervals": s.confidence_intervals,
        "created_by": s.metadata.get("created_by", "unknown"),
        "created_at": s.timestamp.isoformat() if s.timestamp else None,
    }


@router.delete("/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scenario(scenario_id: str = Path(...)):
    """
    Delete a saved scenario.
    
    **Requirements:** 10.6
    """
    if scenario_id not in _scenarios_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario {scenario_id} not found"
        )
    
    del _scenarios_store[scenario_id]
    logger.info(f"Deleted scenario {scenario_id}")


@router.post("/compare")
async def compare_scenarios(request: dict) -> dict:
    """
    Compare multiple scenarios side-by-side.
    
    **Requirements:** 10.7
    """
    scenario_ids = request.get("scenario_ids", [])
    
    if len(scenario_ids) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 scenarios required for comparison"
        )
    
    scenarios = []
    for scenario_id in scenario_ids:
        if scenario_id not in _scenarios_store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scenario {scenario_id} not found"
            )
        scenarios.append(_scenarios_store[scenario_id])
    
    # Build comparison data
    comparison = {
        "scenarios": [
            {
                "scenario_id": s.scenario_id,
                "name": s.metadata.get("name", "Unnamed"),
                "description": s.description,
                "interventions": s.interventions,
                "counterfactual_outcomes": s.counterfactual_outcomes,
                "differences": s.differences,
            }
            for s in scenarios
        ],
        "trade_offs": _analyze_trade_offs(scenarios),
    }
    
    return comparison


def _analyze_trade_offs(scenarios: List[SimulationScenario]) -> dict:
    """Analyze trade-offs between scenarios."""
    # Get all variables
    all_vars = set()
    for s in scenarios:
        all_vars.update(s.differences.keys())
    
    trade_offs = {}
    for var in all_vars:
        values = []
        for s in scenarios:
            if var in s.differences:
                values.append(s.differences[var])
        
        if values:
            trade_offs[var] = {
                "min": min(values),
                "max": max(values),
                "range": max(values) - min(values),
            }
    
    return trade_offs
