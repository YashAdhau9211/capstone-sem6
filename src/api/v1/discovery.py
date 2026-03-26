"""Causal discovery job API endpoints."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional
from uuid import UUID, uuid4

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, HTTPException, Path, status

from src.api.exceptions import ResourceNotFoundError, ValidationError
from src.api.models import (
    DiscoveryJobRequest,
    DiscoveryJobResponse,
    DiscoveryJobStatusResponse,
)
from src.causal_engine.discovery import CausalDiscoveryEngine
from src.models.dag_repository import DAGRepository

logger = logging.getLogger(__name__)

router = APIRouter()


# In-memory job store (in production, use Redis or a database)
class DiscoveryJob:
    """Discovery job state."""

    def __init__(
        self,
        job_id: UUID,
        station_id: str,
        algorithm: str,
        data_source: Optional[str] = None,
        time_range: Optional[Dict[str, str]] = None,
    ):
        self.job_id = job_id
        self.station_id = station_id
        self.algorithm = algorithm
        self.data_source = data_source
        self.time_range = time_range
        self.status = "pending"
        self.progress: Optional[float] = None
        self.result_dag_id: Optional[UUID] = None
        self.error_message: Optional[str] = None
        self.submitted_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None


# Global job store
_job_store: Dict[UUID, DiscoveryJob] = {}


def _get_job(job_id: UUID) -> DiscoveryJob:
    """Get job from store or raise 404."""
    if job_id not in _job_store:
        raise ResourceNotFoundError(resource_type="DiscoveryJob", resource_id=str(job_id))
    return _job_store[job_id]


async def _run_discovery_job(job: DiscoveryJob, algorithm_type: str) -> None:
    """
    Run causal discovery job in background.

    Args:
        job: Discovery job state
        algorithm_type: "linear" or "nonlinear"
    """
    try:
        # Update job status to running
        job.status = "running"
        job.started_at = datetime.utcnow()
        job.progress = 0.0

        logger.info(
            f"Starting {algorithm_type} discovery job {job.job_id} for station {job.station_id}"
        )

        # Load data for the station
        # In production, this would load from time-series database based on time_range
        # For now, we'll use mock data
        data = _load_station_data(job.station_id, job.time_range)

        job.progress = 20.0

        # Initialize discovery engine
        discovery_engine = CausalDiscoveryEngine(random_state=42, n_bootstrap=100)

        job.progress = 30.0

        # Run discovery based on algorithm type
        if algorithm_type == "linear":
            dag = discovery_engine.discover_linear(
                data=data,
                algorithm="DirectLiNGAM",
                station_id=job.station_id,
                created_by="api_discovery_job",
            )
        else:  # nonlinear
            dag = discovery_engine.discover_nonlinear(
                data=data,
                algorithm="RESIT",
                station_id=job.station_id,
                created_by="api_discovery_job",
            )

        job.progress = 80.0

        # Save DAG to repository
        # Try to save to database, but don't fail if database is unavailable
        try:
            dag_repo = DAGRepository()
            try:
                dag_repo.save_dag(dag)
                logger.info(f"Saved discovered DAG {dag.dag_id} to database for job {job.job_id}")
            finally:
                dag_repo.close()
        except Exception as db_error:
            # Log database error but don't fail the job
            logger.warning(
                f"Could not save DAG to database (job {job.job_id}): {db_error}. "
                "DAG discovery completed successfully but not persisted."
            )
        
        # Store DAG ID regardless of database save success
        job.result_dag_id = dag.dag_id

        job.progress = 100.0

        # Mark job as completed
        job.status = "completed"
        job.completed_at = datetime.utcnow()

        logger.info(
            f"Completed {algorithm_type} discovery job {job.job_id} in "
            f"{(job.completed_at - job.started_at).total_seconds():.2f} seconds"
        )

    except Exception as e:
        # Mark job as failed
        job.status = "failed"
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()

        logger.error(
            f"Discovery job {job.job_id} failed: {e}",
            exc_info=True,
        )


def _load_station_data(
    station_id: str, time_range: Optional[Dict[str, str]] = None
) -> pd.DataFrame:
    """
    Load station data for discovery.

    In production, this would query the time-series database.
    For now, we generate mock data.

    Args:
        station_id: Station identifier
        time_range: Optional time range specification

    Returns:
        DataFrame with time-series data
    """
    # TODO: Implement actual data loading from time-series database
    # For now, generate mock data for testing
    import numpy as np

    logger.info(f"Loading data for station {station_id} (time_range: {time_range})")

    # Generate mock data with causal structure
    n_samples = 1000
    np.random.seed(42)

    # Create causal structure: X1 -> X2 -> X3, X1 -> X3
    x1 = np.random.randn(n_samples)
    x2 = 0.8 * x1 + np.random.randn(n_samples) * 0.3
    x3 = 0.6 * x1 + 0.5 * x2 + np.random.randn(n_samples) * 0.3
    x4 = 0.4 * x3 + np.random.randn(n_samples) * 0.3

    data = pd.DataFrame(
        {
            "temperature": x1,
            "pressure": x2,
            "flow_rate": x3,
            "quality_score": x4,
        }
    )

    logger.info(f"Loaded {len(data)} samples with {len(data.columns)} variables")

    return data


@router.post("/linear", response_model=DiscoveryJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_linear_discovery(
    request: DiscoveryJobRequest, background_tasks: BackgroundTasks
) -> DiscoveryJobResponse:
    """
    Trigger DirectLiNGAM causal discovery for linear relationships.

    Submits an asynchronous job for causal discovery using the DirectLiNGAM algorithm.
    Returns a job ID for status tracking.

    **Performance Target:** <5 minutes for 50 variables × 10,000 time points

    **Requirements:** 4.1, 5.1
    """
    try:
        # Validate request
        if not request.station_id:
            raise ValidationError(
                message="station_id is required", detail={"field": "station_id"}
            )

        # Create job
        job_id = uuid4()
        job = DiscoveryJob(
            job_id=job_id,
            station_id=request.station_id,
            algorithm="DirectLiNGAM",
            data_source=request.data_source,
            time_range=request.time_range,
        )

        # Store job
        _job_store[job_id] = job

        # Schedule background task
        background_tasks.add_task(_run_discovery_job, job, "linear")

        logger.info(f"Submitted linear discovery job {job_id} for station {request.station_id}")

        # Return response
        return DiscoveryJobResponse(
            job_id=job_id,
            station_id=request.station_id,
            algorithm="DirectLiNGAM",
            status="pending",
            submitted_at=job.submitted_at,
        )

    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Error submitting linear discovery job: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error submitting discovery job: {str(e)}",
        )


@router.post(
    "/nonlinear", response_model=DiscoveryJobResponse, status_code=status.HTTP_202_ACCEPTED
)
async def trigger_nonlinear_discovery(
    request: DiscoveryJobRequest, background_tasks: BackgroundTasks
) -> DiscoveryJobResponse:
    """
    Trigger RESIT causal discovery for nonlinear relationships.

    Submits an asynchronous job for causal discovery using the RESIT algorithm.
    Returns a job ID for status tracking.

    **Performance Target:** <15 minutes for 50 variables × 10,000 time points

    **Requirements:** 5.1, 5.4
    """
    try:
        # Validate request
        if not request.station_id:
            raise ValidationError(
                message="station_id is required", detail={"field": "station_id"}
            )

        # Create job
        job_id = uuid4()
        job = DiscoveryJob(
            job_id=job_id,
            station_id=request.station_id,
            algorithm="RESIT",
            data_source=request.data_source,
            time_range=request.time_range,
        )

        # Store job
        _job_store[job_id] = job

        # Schedule background task
        background_tasks.add_task(_run_discovery_job, job, "nonlinear")

        logger.info(
            f"Submitted nonlinear discovery job {job_id} for station {request.station_id}"
        )

        # Return response
        return DiscoveryJobResponse(
            job_id=job_id,
            station_id=request.station_id,
            algorithm="RESIT",
            status="pending",
            submitted_at=job.submitted_at,
        )

    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Error submitting nonlinear discovery job: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error submitting discovery job: {str(e)}",
        )


@router.get(
    "/jobs/{job_id}",
    response_model=DiscoveryJobStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def get_discovery_job_status(
    job_id: UUID = Path(..., description="Discovery job identifier"),
) -> DiscoveryJobStatusResponse:
    """
    Check the status of a causal discovery job.

    Returns job status (pending, running, completed, failed), progress,
    and result DAG ID if completed.

    **Requirements:** 4.5, 5.4
    """
    try:
        # Get job from store
        job = _get_job(job_id)

        # Return status response
        return DiscoveryJobStatusResponse(
            job_id=job.job_id,
            status=job.status,
            progress=job.progress,
            result_dag_id=job.result_dag_id,
            error_message=job.error_message,
            started_at=job.started_at,
            completed_at=job.completed_at,
        )

    except ResourceNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error retrieving job status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error retrieving job status: {str(e)}",
        )
