"""Counterfactual simulation API endpoints."""

import logging
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, HTTPException, status

from src.api.exceptions import ResourceNotFoundError, ValidationError
from src.api.models import CounterfactualRequest, CounterfactualResponse
from src.causal_engine.inference import CausalInferenceEngine
from src.models.dag_repository import DAGRepository

logger = logging.getLogger(__name__)

router = APIRouter()


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
        
        # Load DAG for the station
        dag_repo = DAGRepository()
        dag = dag_repo.load_dag(station_id=request.station_id)
        
        if dag is None:
            raise ResourceNotFoundError(
                resource_type="DAG",
                resource_id=request.station_id
            )
        
        # Validate intervention variables exist in DAG
        for var in request.interventions.keys():
            if var not in dag.nodes:
                raise ValidationError(
                    message=f"Intervention variable '{var}' not found in DAG",
                    detail={"field": "interventions", "variable": var}
                )
        
        # Initialize inference engine
        inference_engine = CausalInferenceEngine()
        
        # Load data for counterfactual computation
        data = inference_engine._load_station_data(request.station_id)
        
        # Compute counterfactual outcomes
        counterfactual_df = inference_engine.compute_counterfactual(
            data=data,
            dag=dag,
            interventions=request.interventions
        )
        
        # Extract factual and counterfactual outcomes
        # Get all downstream variables affected by interventions
        affected_vars = set()
        for intervention_var in request.interventions.keys():
            descendants = dag.get_descendants(intervention_var)
            affected_vars.update(descendants)
        
        # Include intervention variables themselves
        affected_vars.update(request.interventions.keys())
        
        # Compute factual outcomes (mean of original data)
        factual: Dict[str, float] = {}
        counterfactual: Dict[str, float] = {}
        difference: Dict[str, float] = {}
        confidence_intervals: Dict[str, tuple] = {}
        
        for var in affected_vars:
            if var in data.columns and var in counterfactual_df.columns:
                factual[var] = float(data[var].mean())
                counterfactual[var] = float(counterfactual_df[var].mean())
                difference[var] = counterfactual[var] - factual[var]
                
                # Compute 95% confidence intervals using standard error
                std_err = float(counterfactual_df[var].std() / (len(counterfactual_df) ** 0.5))
                ci_margin = 1.96 * std_err
                confidence_intervals[var] = (
                    counterfactual[var] - ci_margin,
                    counterfactual[var] + ci_margin
                )
        
        # Calculate response time
        response_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        logger.info(
            f"Computed counterfactual for station {request.station_id} "
            f"with interventions {request.interventions} in {response_time_ms:.2f}ms"
        )
        
        # Return response
        return CounterfactualResponse(
            factual=factual,
            counterfactual=counterfactual,
            difference=difference,
            confidence_intervals=confidence_intervals,
            timestamp=datetime.utcnow()
        )
        
    except (ResourceNotFoundError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Error computing counterfactual: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error during counterfactual computation: {str(e)}"
        )
    finally:
        if 'dag_repo' in locals():
            dag_repo.close()
