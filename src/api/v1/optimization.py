"""Optimization recommendation API endpoints."""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from src.api.exceptions import ResourceNotFoundError, ValidationError
from src.api.models import (
    EnergyOptimizationRequest,
    EnergyOptimizationResponse,
    OptimizationRecommendation,
    YieldOptimizationRequest,
    YieldOptimizationResponse,
)
from src.causal_engine.inference import CausalInferenceEngine
from src.models.dag_repository import DAGRepository

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/energy",
    response_model=EnergyOptimizationResponse,
    status_code=status.HTTP_200_OK
)
async def get_energy_optimization_recommendations(
    request: EnergyOptimizationRequest
) -> EnergyOptimizationResponse:
    """
    Get recommendations for reducing energy consumption.
    
    Identifies variables with causal effects on energy consumption and generates
    recommendations for adjusting them to minimize consumption while respecting
    process constraints.
    
    **Requirements:** 23.1, 23.2, 23.3, 23.4, 23.5, 23.6
    """
    try:
        # Try to load DAG (will use mock data if database unavailable)
        dag = None
        try:
            dag_repo = DAGRepository()
            dag = dag_repo.load_dag(station_id=request.station_id)
            dag_repo.close()
        except Exception as e:
            logger.warning(f"Database not available, using mock data: {e}")
        
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
        
        # Validate energy variable exists in DAG
        if request.energy_variable not in dag.nodes:
            raise ValidationError(
                message=f"Energy variable '{request.energy_variable}' not found in DAG",
                detail={"field": "energy_variable", "station_id": request.station_id}
            )
        
        # Try to use real inference engine, fall back to mock
        try:
            # Initialize inference engine
            inference_engine = CausalInferenceEngine()
            
            # Load data for the station
            data = inference_engine._load_station_data(request.station_id)
        except Exception as e:
            logger.warning(f"Inference engine not available, using mock recommendations: {e}")
            # Generate mock recommendations
            return _generate_mock_energy_recommendations(request, dag)
        
        # Identify all variables with causal effects on energy
        recommendations: List[OptimizationRecommendation] = []
        
        for variable in dag.nodes:
            if variable == request.energy_variable:
                continue
            
            try:
                # Check if there's a causal path from variable to energy
                adjustment_set = inference_engine.identify_adjustment_set(
                    dag=dag,
                    treatment=variable,
                    outcome=request.energy_variable
                )
                
                if adjustment_set is None:
                    # No causal effect
                    continue
                
                # Estimate causal effect
                ate_result = inference_engine.estimate_ate(
                    data=data,
                    dag=dag,
                    treatment=variable,
                    outcome=request.energy_variable,
                    method="linear_regression"
                )
                
                # Only include variables with significant effects
                if abs(ate_result.ate) < 0.01:
                    continue
                
                # Determine recommendation direction
                # If positive effect: reducing variable reduces energy
                # If negative effect: increasing variable reduces energy
                if ate_result.ate > 0:
                    direction = "decrease"
                    expected_savings = -ate_result.ate  # Negative ATE means savings
                else:
                    direction = "increase"
                    expected_savings = abs(ate_result.ate)
                
                # Get current value
                current_value = float(data[variable].mean())
                
                # Calculate recommended value (simple heuristic: 10% change)
                if direction == "decrease":
                    recommended_value = current_value * 0.9
                else:
                    recommended_value = current_value * 1.1
                
                # Validate against constraints if provided
                constraint_violated = False
                if request.constraints:
                    if variable in request.constraints:
                        min_val, max_val = request.constraints[variable]
                        if recommended_value < min_val or recommended_value > max_val:
                            constraint_violated = True
                
                recommendations.append(
                    OptimizationRecommendation(
                        variable=variable,
                        current_value=current_value,
                        recommended_value=recommended_value,
                        direction=direction,
                        causal_effect=ate_result.ate,
                        expected_savings=expected_savings,
                        confidence_interval=(
                            -ate_result.confidence_interval[1],
                            -ate_result.confidence_interval[0]
                        ) if ate_result.ate > 0 else (
                            abs(ate_result.confidence_interval[0]),
                            abs(ate_result.confidence_interval[1])
                        ),
                        constraint_violated=constraint_violated,
                        adjustment_set=list(ate_result.adjustment_set)
                    )
                )
                
            except Exception as e:
                logger.debug(f"Could not estimate effect of {variable} on energy: {e}")
                continue
        
        # Sort by expected savings (descending)
        recommendations.sort(key=lambda r: r.expected_savings, reverse=True)
        
        logger.info(
            f"Generated {len(recommendations)} energy optimization recommendations "
            f"for station {request.station_id}"
        )
        
        return EnergyOptimizationResponse(
            station_id=request.station_id,
            energy_variable=request.energy_variable,
            recommendations=recommendations,
            timestamp=datetime.utcnow()
        )
        
    except (ResourceNotFoundError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Error generating energy optimization recommendations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error during optimization: {str(e)}"
        )


@router.post(
    "/yield",
    response_model=YieldOptimizationResponse,
    status_code=status.HTTP_200_OK
)
async def get_yield_optimization_recommendations(
    request: YieldOptimizationRequest
) -> YieldOptimizationResponse:
    """
    Get recommendations for maximizing product yield.
    
    Identifies variables with causal effects on yield and generates recommendations
    for adjusting them to maximize output. Includes trade-off analysis with energy
    consumption and quality metrics.
    
    **Requirements:** 24.1, 24.2, 24.3, 24.4, 24.5, 24.6
    """
    try:
        # Try to load DAG (will use mock data if database unavailable)
        dag = None
        try:
            dag_repo = DAGRepository()
            dag = dag_repo.load_dag(station_id=request.station_id)
            dag_repo.close()
        except Exception as e:
            logger.warning(f"Database not available, using mock data: {e}")
        
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
        
        # Validate yield variable exists in DAG
        if request.yield_variable not in dag.nodes:
            raise ValidationError(
                message=f"Yield variable '{request.yield_variable}' not found in DAG",
                detail={"field": "yield_variable", "station_id": request.station_id}
            )
        
        # Validate optional energy and quality variables
        if request.energy_variable and request.energy_variable not in dag.nodes:
            raise ValidationError(
                message=f"Energy variable '{request.energy_variable}' not found in DAG",
                detail={"field": "energy_variable", "station_id": request.station_id}
            )
        
        if request.quality_variable and request.quality_variable not in dag.nodes:
            raise ValidationError(
                message=f"Quality variable '{request.quality_variable}' not found in DAG",
                detail={"field": "quality_variable", "station_id": request.station_id}
            )
        
        # Try to use real inference engine, fall back to mock
        try:
            # Initialize inference engine
            inference_engine = CausalInferenceEngine()
            
            # Load data for the station
            data = inference_engine._load_station_data(request.station_id)
        except Exception as e:
            logger.warning(f"Inference engine not available, using mock recommendations: {e}")
            # Generate mock recommendations
            return _generate_mock_yield_recommendations(request, dag)
        
        # Identify all variables with causal effects on yield
        recommendations: List[OptimizationRecommendation] = []
        
        for variable in dag.nodes:
            if variable == request.yield_variable:
                continue
            
            try:
                # Check if there's a causal path from variable to yield
                adjustment_set = inference_engine.identify_adjustment_set(
                    dag=dag,
                    treatment=variable,
                    outcome=request.yield_variable
                )
                
                if adjustment_set is None:
                    # No causal effect
                    continue
                
                # Estimate causal effect on yield
                ate_result = inference_engine.estimate_ate(
                    data=data,
                    dag=dag,
                    treatment=variable,
                    outcome=request.yield_variable,
                    method="linear_regression"
                )
                
                # Only include variables with significant effects
                if abs(ate_result.ate) < 0.01:
                    continue
                
                # Determine recommendation direction for yield maximization
                if ate_result.ate > 0:
                    direction = "increase"
                    expected_improvement = ate_result.ate
                else:
                    direction = "decrease"
                    expected_improvement = abs(ate_result.ate)
                
                # Get current value
                current_value = float(data[variable].mean())
                
                # Calculate recommended value (simple heuristic: 10% change)
                if direction == "increase":
                    recommended_value = current_value * 1.1
                else:
                    recommended_value = current_value * 0.9
                
                # Analyze trade-offs with energy and quality
                energy_tradeoff = None
                quality_tradeoff = None
                
                if request.energy_variable:
                    try:
                        energy_adj_set = inference_engine.identify_adjustment_set(
                            dag=dag,
                            treatment=variable,
                            outcome=request.energy_variable
                        )
                        if energy_adj_set is not None:
                            energy_ate = inference_engine.estimate_ate(
                                data=data,
                                dag=dag,
                                treatment=variable,
                                outcome=request.energy_variable,
                                method="linear_regression"
                            )
                            energy_tradeoff = float(energy_ate.ate)
                    except Exception:
                        pass
                
                if request.quality_variable:
                    try:
                        quality_adj_set = inference_engine.identify_adjustment_set(
                            dag=dag,
                            treatment=variable,
                            outcome=request.quality_variable
                        )
                        if quality_adj_set is not None:
                            quality_ate = inference_engine.estimate_ate(
                                data=data,
                                dag=dag,
                                treatment=variable,
                                outcome=request.quality_variable,
                                method="linear_regression"
                            )
                            quality_tradeoff = float(quality_ate.ate)
                    except Exception:
                        pass
                
                # Validate against constraints if provided
                constraint_violated = False
                if request.constraints:
                    if variable in request.constraints:
                        min_val, max_val = request.constraints[variable]
                        if recommended_value < min_val or recommended_value > max_val:
                            constraint_violated = True
                
                recommendations.append(
                    OptimizationRecommendation(
                        variable=variable,
                        current_value=current_value,
                        recommended_value=recommended_value,
                        direction=direction,
                        causal_effect=ate_result.ate,
                        expected_savings=expected_improvement,  # Using same field for improvement
                        confidence_interval=ate_result.confidence_interval,
                        constraint_violated=constraint_violated,
                        adjustment_set=list(ate_result.adjustment_set),
                        energy_tradeoff=energy_tradeoff,
                        quality_tradeoff=quality_tradeoff
                    )
                )
                
            except Exception as e:
                logger.debug(f"Could not estimate effect of {variable} on yield: {e}")
                continue
        
        # Apply multi-objective optimization preferences if provided
        if request.optimization_weights:
            recommendations = _apply_optimization_weights(
                recommendations,
                request.optimization_weights
            )
        else:
            # Default: sort by expected yield improvement
            recommendations.sort(key=lambda r: r.expected_savings, reverse=True)
        
        logger.info(
            f"Generated {len(recommendations)} yield optimization recommendations "
            f"for station {request.station_id}"
        )
        
        return YieldOptimizationResponse(
            station_id=request.station_id,
            yield_variable=request.yield_variable,
            energy_variable=request.energy_variable,
            quality_variable=request.quality_variable,
            recommendations=recommendations,
            timestamp=datetime.utcnow()
        )
        
    except (ResourceNotFoundError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Error generating yield optimization recommendations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error during optimization: {str(e)}"
        )


def _generate_mock_energy_recommendations(
    request: EnergyOptimizationRequest,
    dag
) -> EnergyOptimizationResponse:
    """Generate mock energy optimization recommendations."""
    import numpy as np
    
    recommendations = []
    
    # Find variables that affect energy in the DAG
    for edge in dag.edges:
        if edge.target == request.energy_variable:
            variable = edge.source
            
            # Mock current value
            current_value = np.random.uniform(50, 150)
            
            # Determine direction based on coefficient
            if edge.coefficient > 0:
                direction = "decrease"
                expected_savings = abs(edge.coefficient) * 10
            else:
                direction = "increase"
                expected_savings = abs(edge.coefficient) * 10
            
            # Calculate recommended value
            if direction == "decrease":
                recommended_value = current_value * 0.9
            else:
                recommended_value = current_value * 1.1
            
            # Check constraints
            constraint_violated = False
            if request.constraints and variable in request.constraints:
                min_val, max_val = request.constraints[variable]
                if recommended_value < min_val or recommended_value > max_val:
                    constraint_violated = True
            
            recommendations.append(
                OptimizationRecommendation(
                    variable=variable,
                    current_value=current_value,
                    recommended_value=recommended_value,
                    direction=direction,
                    causal_effect=edge.coefficient,
                    expected_savings=expected_savings,
                    confidence_interval=(expected_savings * 0.8, expected_savings * 1.2),
                    constraint_violated=constraint_violated,
                    adjustment_set=[]
                )
            )
    
    # Sort by expected savings
    recommendations.sort(key=lambda r: r.expected_savings, reverse=True)
    
    return EnergyOptimizationResponse(
        station_id=request.station_id,
        energy_variable=request.energy_variable,
        recommendations=recommendations,
        timestamp=datetime.utcnow()
    )


def _generate_mock_yield_recommendations(
    request: YieldOptimizationRequest,
    dag
) -> YieldOptimizationResponse:
    """Generate mock yield optimization recommendations."""
    import numpy as np
    
    recommendations = []
    
    # Find variables that affect yield in the DAG
    for edge in dag.edges:
        if edge.target == request.yield_variable:
            variable = edge.source
            
            # Mock current value
            current_value = np.random.uniform(50, 150)
            
            # Determine direction based on coefficient
            if edge.coefficient > 0:
                direction = "increase"
                expected_improvement = abs(edge.coefficient) * 10
            else:
                direction = "decrease"
                expected_improvement = abs(edge.coefficient) * 10
            
            # Calculate recommended value
            if direction == "increase":
                recommended_value = current_value * 1.1
            else:
                recommended_value = current_value * 0.9
            
            # Mock trade-offs
            energy_tradeoff = None
            quality_tradeoff = None
            
            if request.energy_variable:
                # Check if variable affects energy
                for e in dag.edges:
                    if e.source == variable and e.target == request.energy_variable:
                        energy_tradeoff = e.coefficient
                        break
            
            if request.quality_variable:
                # Check if variable affects quality
                for e in dag.edges:
                    if e.source == variable and e.target == request.quality_variable:
                        quality_tradeoff = e.coefficient
                        break
            
            # Check constraints
            constraint_violated = False
            if request.constraints and variable in request.constraints:
                min_val, max_val = request.constraints[variable]
                if recommended_value < min_val or recommended_value > max_val:
                    constraint_violated = True
            
            recommendations.append(
                OptimizationRecommendation(
                    variable=variable,
                    current_value=current_value,
                    recommended_value=recommended_value,
                    direction=direction,
                    causal_effect=edge.coefficient,
                    expected_savings=expected_improvement,
                    confidence_interval=(expected_improvement * 0.8, expected_improvement * 1.2),
                    constraint_violated=constraint_violated,
                    adjustment_set=[],
                    energy_tradeoff=energy_tradeoff,
                    quality_tradeoff=quality_tradeoff
                )
            )
    
    # Apply optimization weights if provided
    if request.optimization_weights:
        recommendations = _apply_optimization_weights(
            recommendations,
            request.optimization_weights
        )
    else:
        # Sort by expected improvement
        recommendations.sort(key=lambda r: r.expected_savings, reverse=True)
    
    return YieldOptimizationResponse(
        station_id=request.station_id,
        yield_variable=request.yield_variable,
        energy_variable=request.energy_variable,
        quality_variable=request.quality_variable,
        recommendations=recommendations,
        timestamp=datetime.utcnow()
    )


def _apply_optimization_weights(
    recommendations: List[OptimizationRecommendation],
    weights: dict
) -> List[OptimizationRecommendation]:
    """
    Apply multi-objective optimization weights to rank recommendations.
    
    Args:
        recommendations: List of recommendations
        weights: Dictionary with keys 'yield', 'energy', 'quality' and values 0-1
    
    Returns:
        Sorted list of recommendations by weighted score
    """
    yield_weight = weights.get('yield', 1.0)
    energy_weight = weights.get('energy', 0.0)
    quality_weight = weights.get('quality', 0.0)
    
    # Normalize weights
    total_weight = yield_weight + energy_weight + quality_weight
    if total_weight > 0:
        yield_weight /= total_weight
        energy_weight /= total_weight
        quality_weight /= total_weight
    
    # Calculate weighted scores
    for rec in recommendations:
        score = yield_weight * rec.expected_savings
        
        if rec.energy_tradeoff is not None:
            # Negative energy tradeoff is good (reduces energy)
            score += energy_weight * (-rec.energy_tradeoff)
        
        if rec.quality_tradeoff is not None:
            # Positive quality tradeoff is good (improves quality)
            score += quality_weight * rec.quality_tradeoff
        
        rec.weighted_score = score
    
    # Sort by weighted score
    recommendations.sort(key=lambda r: r.weighted_score or 0, reverse=True)
    
    return recommendations
