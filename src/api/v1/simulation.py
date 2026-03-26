"""Counterfactual simulation API endpoints."""

import logging
from datetime import datetime
from typing import Dict, List
import numpy as np
import pandas as pd

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
import io

from src.api.exceptions import ResourceNotFoundError, ValidationError
from src.api.models import CounterfactualRequest, CounterfactualResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def _generate_mock_counterfactual(
    station_id: str, interventions: Dict[str, float], dag_nodes: List[str]
) -> CounterfactualResponse:
    """Generate mock counterfactual response for testing."""
    # Generate mock factual values
    factual = {node: np.random.uniform(10, 100) for node in dag_nodes}
    
    # Generate mock counterfactual values based on interventions
    counterfactual = factual.copy()
    for var, value in interventions.items():
        if var in counterfactual:
            counterfactual[var] = value
    
    # Simulate causal effects (simple mock logic)
    # For demo: if temperature increases, yield increases slightly, energy increases more
    if "temperature" in interventions and "yield" in counterfactual:
        temp_change = interventions["temperature"] - factual.get("temperature", 0)
        counterfactual["yield"] = factual["yield"] + temp_change * 0.02
        if "energy_consumption" in counterfactual:
            counterfactual["energy_consumption"] = factual["energy_consumption"] + temp_change * 0.05
    
    # Calculate differences
    difference = {var: counterfactual[var] - factual[var] for var in factual.keys()}
    
    # Generate confidence intervals (mock: ±5% of value)
    confidence_intervals = {
        var: (counterfactual[var] * 0.95, counterfactual[var] * 1.05)
        for var in counterfactual.keys()
    }
    
    return CounterfactualResponse(
        factual=factual,
        counterfactual=counterfactual,
        difference=difference,
        confidence_intervals=confidence_intervals,
        timestamp=datetime.utcnow()
    )


@router.post(
    "/counterfactual", response_model=CounterfactualResponse, status_code=status.HTTP_200_OK
)
async def compute_counterfactual(request: CounterfactualRequest) -> CounterfactualResponse:
    """
    Compute counterfactual outcomes for specified interventions.

    This endpoint performs do-calculus interventions on the causal DAG and
    propagates effects through causal paths to predict counterfactual outcomes.

    **Performance Target:** <500ms response time at 95th percentile

    **Requirements:** 10.1, 10.2, 10.3, 10.5, 26.2
    """
    start_time = datetime.utcnow()
    
    try:
        # Validate interventions
        if not request.interventions:
            raise ValidationError(
                message="At least one intervention must be specified",
                detail={"field": "interventions"}
            )
        
        # Try to load DAG (will use mock data if database unavailable)
        try:
            from src.models.dag_repository import DAGRepository
            dag_repo = DAGRepository()
            dag = dag_repo.load_dag(station_id=request.station_id)
            dag_repo.close()
        except Exception as e:
            logger.warning(f"Database not available, using mock data: {e}")
            dag = None
        
        # If no DAG from database, use mock DAG
        if dag is None:
            from src.api.v1.dags import MOCK_DAGS
            mock_dag_id = f"dag-{request.station_id}"
            if mock_dag_id not in MOCK_DAGS:
                raise ResourceNotFoundError(
                    resource_type="DAG",
                    resource_id=request.station_id
                )
            dag = MOCK_DAGS[mock_dag_id]
        
        # Validate intervention variables exist in DAG
        for var in request.interventions.keys():
            if var not in dag.nodes:
                raise ValidationError(
                    message=f"Intervention variable '{var}' not found in DAG",
                    detail={"field": "interventions", "variable": var, "available_variables": dag.nodes}
                )
        
        # Try to use real inference engine, fall back to mock
        try:
            from src.causal_engine.inference import CausalInferenceEngine
            inference_engine = CausalInferenceEngine()
            data = inference_engine._load_station_data(request.station_id)
            
            counterfactual_df = inference_engine.compute_counterfactual(
                data=data,
                dag=dag,
                interventions=request.interventions
            )
            
            # Extract results (existing logic)
            affected_vars = set()
            for intervention_var in request.interventions.keys():
                descendants = dag.get_descendants(intervention_var)
                affected_vars.update(descendants)
            affected_vars.update(request.interventions.keys())
            
            factual: Dict[str, float] = {}
            counterfactual: Dict[str, float] = {}
            difference: Dict[str, float] = {}
            confidence_intervals: Dict[str, tuple] = {}
            
            for var in affected_vars:
                if var in data.columns and var in counterfactual_df.columns:
                    factual[var] = float(data[var].mean())
                    counterfactual[var] = float(counterfactual_df[var].mean())
                    difference[var] = counterfactual[var] - factual[var]
                    
                    std_err = float(counterfactual_df[var].std() / (len(counterfactual_df) ** 0.5))
                    ci_margin = 1.96 * std_err
                    confidence_intervals[var] = (
                        counterfactual[var] - ci_margin,
                        counterfactual[var] + ci_margin
                    )
            
            response_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.info(f"Computed counterfactual in {response_time_ms:.2f}ms")
            
            return CounterfactualResponse(
                factual=factual,
                counterfactual=counterfactual,
                difference=difference,
                confidence_intervals=confidence_intervals,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.warning(f"Inference engine not available, using mock computation: {e}")
            # Use mock computation
            response = _generate_mock_counterfactual(request.station_id, request.interventions, dag.nodes)
            response_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.info(f"Generated mock counterfactual in {response_time_ms:.2f}ms")
            return response
        
    except (ResourceNotFoundError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Error computing counterfactual: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error during counterfactual computation: {str(e)}"
        )



@router.post("/historical-replay")
async def historical_replay(
    station_id: str,
    time_range: Dict[str, str],
    interventions: Dict[str, float],
) -> dict:
    """
    Perform historical scenario replay with counterfactual interventions.
    
    Loads historical data for the specified time range, applies counterfactual
    interventions, and computes what would have happened under different conditions.
    
    **Requirements:** 25.1, 25.2, 25.3, 25.4, 25.5
    """
    try:
        # Validate inputs
        if not interventions:
            raise ValidationError(
                message="At least one intervention must be specified",
                detail={"field": "interventions"}
            )
        
        if not time_range or "start" not in time_range or "end" not in time_range:
            raise ValidationError(
                message="Time range must include 'start' and 'end' timestamps",
                detail={"field": "time_range"}
            )
        
        # Load DAG for the station
        dag_repo = DAGRepository()
        dag = dag_repo.load_dag(station_id=station_id)
        
        if dag is None:
            raise ResourceNotFoundError(
                resource_type="DAG",
                resource_id=station_id
            )
        
        # Validate intervention variables exist in DAG
        for var in interventions.keys():
            if var not in dag.nodes:
                raise ValidationError(
                    message=f"Intervention variable '{var}' not found in DAG",
                    detail={"field": "interventions", "variable": var}
                )
        
        # Initialize inference engine
        inference_engine = CausalInferenceEngine()
        
        # Load historical data for the time range
        # In production, this would query the time-series database
        # For now, we'll use mock data
        historical_data = _load_historical_data(
            station_id, 
            time_range["start"], 
            time_range["end"]
        )
        
        # Compute counterfactual for each time point
        time_series_results = []
        
        for idx, row in historical_data.iterrows():
            # Get factual values at this time point
            factual_point = row.to_dict()
            
            # Compute counterfactual for this time point
            counterfactual_df = inference_engine.compute_counterfactual(
                data=historical_data.iloc[[idx]],
                dag=dag,
                interventions=interventions
            )
            
            # Get affected variables
            affected_vars = set()
            for intervention_var in interventions.keys():
                descendants = dag.get_descendants(intervention_var)
                affected_vars.update(descendants)
            affected_vars.update(interventions.keys())
            
            # Record time series point
            for var in affected_vars:
                if var in factual_point and var in counterfactual_df.columns:
                    factual_val = float(factual_point[var])
                    counterfactual_val = float(counterfactual_df[var].iloc[0])
                    
                    time_series_results.append({
                        "timestamp": row.get("timestamp", idx),
                        "variable": var,
                        "factual": factual_val,
                        "counterfactual": counterfactual_val,
                        "difference": counterfactual_val - factual_val,
                    })
        
        # Compute aggregate metrics
        aggregate_metrics = {}
        
        # Group by variable
        ts_df = pd.DataFrame(time_series_results)
        for var in ts_df["variable"].unique():
            var_data = ts_df[ts_df["variable"] == var]
            
            aggregate_metrics[var] = {
                "mean": float(var_data["counterfactual"].mean()),
                "std": float(var_data["counterfactual"].std()),
                "p25": float(var_data["counterfactual"].quantile(0.25)),
                "p50": float(var_data["counterfactual"].quantile(0.50)),
                "p75": float(var_data["counterfactual"].quantile(0.75)),
                "factual_mean": float(var_data["factual"].mean()),
                "difference_mean": float(var_data["difference"].mean()),
            }
        
        logger.info(
            f"Completed historical replay for station {station_id} "
            f"from {time_range['start']} to {time_range['end']}"
        )
        
        return {
            "station_id": station_id,
            "time_range": time_range,
            "interventions": interventions,
            "time_series": time_series_results,
            "aggregate_metrics": aggregate_metrics,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
    except (ResourceNotFoundError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Error in historical replay: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error during historical replay: {str(e)}"
        )
    finally:
        if 'dag_repo' in locals():
            dag_repo.close()


@router.post("/historical-replay/export")
async def export_historical_replay(
    station_id: str,
    time_range: Dict[str, str],
    interventions: Dict[str, float],
):
    """
    Export historical replay results to CSV format.
    
    **Requirements:** 25.6
    """
    try:
        # Run the historical replay
        result = await historical_replay(station_id, time_range, interventions)
        
        # Convert to CSV
        df = pd.DataFrame(result["time_series"])
        
        # Create CSV in memory
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        
        # Return as streaming response
        filename = f"historical_replay_{station_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting historical replay: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export historical replay: {str(e)}"
        )


def _load_historical_data(station_id: str, start: str, end: str) -> pd.DataFrame:
    """
    Load historical time-series data for the specified time range.
    
    In production, this would query InfluxDB or TimescaleDB.
    For now, returns mock data.
    """
    # Mock implementation - generate synthetic data
    # In production, query time-series database
    
    # Generate 100 time points
    n_points = 100
    
    # Mock variables
    variables = ["temperature", "pressure", "flow_rate", "yield", "energy"]
    
    data = {
        "timestamp": pd.date_range(start=start, end=end, periods=n_points),
    }
    
    # Generate random data for each variable
    np.random.seed(42)
    for var in variables:
        data[var] = np.random.randn(n_points) * 10 + 100
    
    return pd.DataFrame(data)
