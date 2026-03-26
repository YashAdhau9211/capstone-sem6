"""Causal effect estimation API endpoints."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.exceptions import ResourceNotFoundError, ValidationError
from src.api.models import CausalEffectRequest, CausalEffectResponse
from src.api.rbac import require_run_simulation
from src.causal_engine.inference import CausalInferenceEngine
from src.models.dag_repository import DAGRepository

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/estimate", response_model=CausalEffectResponse, status_code=status.HTTP_200_OK)
async def estimate_causal_effect(
    request: CausalEffectRequest,
    user: dict = Depends(require_run_simulation),
) -> CausalEffectResponse:
    """
    Estimate the average treatment effect (ATE) for a treatment-outcome pair.

    This endpoint uses the backdoor criterion to identify valid adjustment sets
    and estimates the causal effect using the specified method.

    **Methods:**
    - `linear_regression`: Fast, assumes linearity
    - `psm`: Propensity Score Matching, handles confounding
    - `ipw`: Inverse Propensity Weighting, handles selection bias

    **Requirements:** 8.1, 8.2, 8.3, 26.1
    """
    try:
        # Load DAG for the station
        dag_repo = DAGRepository()
        dag = dag_repo.load_dag(station_id=request.station_id)
        
        if dag is None:
            raise ResourceNotFoundError(
                resource_type="DAG",
                resource_id=request.station_id
            )
        
        # Validate treatment and outcome variables exist in DAG
        if request.treatment not in dag.nodes:
            raise ValidationError(
                message=f"Treatment variable '{request.treatment}' not found in DAG",
                detail={"field": "treatment", "station_id": request.station_id}
            )
        
        if request.outcome not in dag.nodes:
            raise ValidationError(
                message=f"Outcome variable '{request.outcome}' not found in DAG",
                detail={"field": "outcome", "station_id": request.station_id}
            )
        
        # Initialize inference engine
        inference_engine = CausalInferenceEngine()
        
        # Identify adjustment set
        adjustment_set = inference_engine.identify_adjustment_set(
            dag=dag,
            treatment=request.treatment,
            outcome=request.outcome
        )
        
        if adjustment_set is None:
            raise ValidationError(
                message=f"Causal effect not identifiable: no valid adjustment set found for treatment '{request.treatment}' and outcome '{request.outcome}'",
                detail={"treatment": request.treatment, "outcome": request.outcome}
            )
        
        # Load data for estimation (placeholder - in production, load from time-series DB)
        # For now, we'll use mock data from the inference engine
        data = inference_engine._load_station_data(request.station_id)
        
        # Estimate ATE
        ate_result = inference_engine.estimate_ate(
            data=data,
            dag=dag,
            treatment=request.treatment,
            outcome=request.outcome,
            method=request.method
        )
        
        logger.info(
            f"Estimated ATE for station {request.station_id}: "
            f"{request.treatment} -> {request.outcome} = {ate_result.ate:.4f}"
        )
        
        # Return response
        return CausalEffectResponse(
            treatment=ate_result.treatment,
            outcome=ate_result.outcome,
            ate=ate_result.ate,
            confidence_interval=ate_result.confidence_interval,
            method=ate_result.method,
            adjustment_set=list(ate_result.adjustment_set),
            sample_size=ate_result.sample_size,
            timestamp=datetime.utcnow()
        )
        
    except (ResourceNotFoundError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Error estimating causal effect: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error during causal effect estimation: {str(e)}"
        )
    finally:
        if 'dag_repo' in locals():
            dag_repo.close()
