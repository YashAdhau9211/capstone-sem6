"""Pydantic models for API request/response validation."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# Base response models
class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(..., description="API version")


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    detail: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Causal effect estimation models
class CausalEffectRequest(BaseModel):
    """Request model for causal effect estimation."""

    station_id: str = Field(..., description="Manufacturing station identifier")
    treatment: str = Field(..., description="Treatment variable name")
    outcome: str = Field(..., description="Outcome variable name")
    method: str = Field(
        default="linear_regression",
        description="Estimation method: linear_regression, psm, or ipw",
    )

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        """Validate estimation method."""
        allowed = ["linear_regression", "psm", "ipw"]
        if v not in allowed:
            raise ValueError(f"Method must be one of {allowed}")
        return v


class CausalEffectResponse(BaseModel):
    """Response model for causal effect estimation."""

    treatment: str = Field(..., description="Treatment variable name")
    outcome: str = Field(..., description="Outcome variable name")
    ate: float = Field(..., description="Average Treatment Effect")
    confidence_interval: Tuple[float, float] = Field(..., description="95% confidence interval")
    method: str = Field(..., description="Estimation method used")
    adjustment_set: List[str] = Field(..., description="Variables adjusted for")
    sample_size: int = Field(..., description="Number of observations used")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Counterfactual simulation models
class CounterfactualRequest(BaseModel):
    """Request model for counterfactual simulation."""

    station_id: str = Field(..., description="Manufacturing station identifier")
    interventions: Dict[str, float] = Field(
        ..., description="Variable interventions as {variable: value}"
    )
    time_range: Optional[Dict[str, str]] = Field(
        None, description="Optional time range for historical simulation"
    )


class CounterfactualResponse(BaseModel):
    """Response model for counterfactual simulation."""

    factual: Dict[str, float] = Field(..., description="Factual outcomes")
    counterfactual: Dict[str, float] = Field(..., description="Counterfactual outcomes")
    difference: Dict[str, float] = Field(..., description="Difference between outcomes")
    confidence_intervals: Dict[str, Tuple[float, float]] = Field(
        ..., description="95% confidence intervals for predictions"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# RCA models
class RootCauseInfo(BaseModel):
    """Root cause information."""

    variable: str = Field(..., description="Root cause variable name")
    attribution_score: float = Field(..., description="Causal attribution score")
    confidence_interval: Tuple[float, float] = Field(..., description="95% confidence interval")
    causal_path: List[str] = Field(..., description="Causal path from root cause to anomaly")


class RCAResponse(BaseModel):
    """Response model for RCA results."""

    anomaly_id: str = Field(..., description="Anomaly identifier")
    root_causes: List[RootCauseInfo] = Field(..., description="Top root causes ranked by score")
    suppressed_alerts: List[str] = Field(..., description="Suppressed descendant anomaly alerts")
    generation_time: datetime = Field(..., description="RCA report generation timestamp")


# Model status models
class ModelStatusResponse(BaseModel):
    """Response model for station model status."""

    model_id: UUID = Field(..., description="Station model identifier")
    station_id: str = Field(..., description="Manufacturing station identifier")
    status: str = Field(..., description="Model status: active, drifted, or training")
    baseline_accuracy: float = Field(..., description="Baseline prediction accuracy")
    current_accuracy: Optional[float] = Field(None, description="Current prediction accuracy")
    last_evaluated: Optional[datetime] = Field(None, description="Last evaluation timestamp")
    drift_detected: bool = Field(..., description="Whether model drift was detected")
    drift_magnitude: Optional[float] = Field(None, description="Drift magnitude if detected")


# DAG models
class DAGVersionInfo(BaseModel):
    """DAG version information."""

    dag_id: UUID = Field(..., description="DAG identifier")
    version: int = Field(..., description="Version number")
    algorithm: str = Field(..., description="Discovery algorithm or 'expert_edited'")
    created_at: datetime = Field(..., description="Creation timestamp")
    created_by: str = Field(..., description="User who created this version")


class DAGResponse(BaseModel):
    """Response model for DAG retrieval."""

    dag_id: UUID = Field(..., description="DAG identifier")
    station_id: str = Field(..., description="Manufacturing station identifier")
    version: int = Field(..., description="Version number")
    nodes: List[str] = Field(..., description="Variable names in the DAG")
    edges: List[Dict[str, Any]] = Field(..., description="Causal edges with coefficients")
    algorithm: str = Field(..., description="Discovery algorithm or 'expert_edited'")
    created_at: datetime = Field(..., description="Creation timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class DAGVersionListResponse(BaseModel):
    """Response model for DAG version history."""

    station_id: str = Field(..., description="Manufacturing station identifier")
    versions: List[DAGVersionInfo] = Field(..., description="List of DAG versions")
    total_count: int = Field(..., description="Total number of versions")


# Discovery job models
class DiscoveryJobRequest(BaseModel):
    """Request model for triggering causal discovery."""

    station_id: str = Field(..., description="Manufacturing station identifier")
    algorithm: str = Field(..., description="Discovery algorithm: linear or nonlinear")
    data_source: Optional[str] = Field(None, description="Optional data source identifier")
    time_range: Optional[Dict[str, str]] = Field(
        None, description="Optional time range for data"
    )

    @field_validator("algorithm")
    @classmethod
    def validate_algorithm(cls, v: str) -> str:
        """Validate discovery algorithm."""
        allowed = ["linear", "nonlinear"]
        if v not in allowed:
            raise ValueError(f"Algorithm must be one of {allowed}")
        return v


class DiscoveryJobResponse(BaseModel):
    """Response model for discovery job submission."""

    job_id: UUID = Field(..., description="Discovery job identifier")
    station_id: str = Field(..., description="Manufacturing station identifier")
    algorithm: str = Field(..., description="Discovery algorithm")
    status: str = Field(..., description="Job status: pending, running, completed, or failed")
    submitted_at: datetime = Field(default_factory=datetime.utcnow)


class DiscoveryJobStatusResponse(BaseModel):
    """Response model for discovery job status."""

    job_id: UUID = Field(..., description="Discovery job identifier")
    status: str = Field(..., description="Job status: pending, running, completed, or failed")
    progress: Optional[float] = Field(None, description="Progress percentage (0-100)")
    result_dag_id: Optional[UUID] = Field(None, description="Result DAG ID if completed")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    started_at: Optional[datetime] = Field(None, description="Job start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")


# DAG modification models
class DAGSaveRequest(BaseModel):
    """Request model for saving a new DAG version."""

    nodes: List[str] = Field(..., description="Variable names in the DAG")
    edges: List[Dict[str, Any]] = Field(..., description="Causal edges with coefficients")
    algorithm: str = Field(default="expert_edited", description="Algorithm or 'expert_edited'")
    created_by: str = Field(..., description="User identifier")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class EdgeOperation(BaseModel):
    """Edge operation for DAG modification."""

    operation: str = Field(..., description="Operation: add, delete, or reverse")
    source: str = Field(..., description="Source node")
    target: str = Field(..., description="Target node")
    coefficient: Optional[float] = Field(None, description="Causal coefficient (for add)")
    confidence: Optional[float] = Field(None, description="Confidence score (for add)")
    edge_type: Optional[str] = Field(default="linear", description="Edge type: linear or nonlinear")

    @field_validator("operation")
    @classmethod
    def validate_operation(cls, v: str) -> str:
        """Validate edge operation."""
        allowed = ["add", "delete", "reverse"]
        if v not in allowed:
            raise ValueError(f"Operation must be one of {allowed}")
        return v

    @field_validator("edge_type")
    @classmethod
    def validate_edge_type(cls, v: str) -> str:
        """Validate edge type."""
        allowed = ["linear", "nonlinear"]
        if v not in allowed:
            raise ValueError(f"Edge type must be one of {allowed}")
        return v


class DAGModificationRequest(BaseModel):
    """Request model for DAG edge modifications."""

    operations: List[EdgeOperation] = Field(..., description="List of edge operations to perform")
    created_by: str = Field(..., description="User identifier")


class DAGModificationResponse(BaseModel):
    """Response model for DAG modification."""

    dag_id: UUID = Field(..., description="New DAG identifier")
    station_id: str = Field(..., description="Manufacturing station identifier")
    version: int = Field(..., description="New version number")
    operations_applied: int = Field(..., description="Number of operations successfully applied")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
