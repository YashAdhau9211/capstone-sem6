"""Root cause analysis API endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, status

from src.api.exceptions import ResourceNotFoundError
from src.api.models import RCAResponse, RootCauseInfo

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory storage for RCA reports (in production, use database or cache)
_rca_reports_cache = {}


@router.get("/{anomaly_id}", response_model=RCAResponse, status_code=status.HTTP_200_OK)
async def get_rca_report(
    anomaly_id: str = Path(..., description="Anomaly identifier"),
) -> RCAResponse:
    """
    Retrieve root cause analysis report for an anomaly.

    Returns the top root causes ranked by attribution score, along with
    causal paths and suppressed descendant alerts.

    **Requirements:** 12.5, 26.3
    """
    try:
        # Try to retrieve from cache
        if anomaly_id in _rca_reports_cache:
            rca_report = _rca_reports_cache[anomaly_id]
            
            logger.info(f"Retrieved RCA report for anomaly {anomaly_id}")
            
            # Convert RCAReport to RCAResponse
            root_causes_info = [
                RootCauseInfo(
                    variable=rc.variable,
                    attribution_score=rc.attribution_score,
                    confidence_interval=rc.confidence_interval,
                    causal_path=rc.causal_path
                )
                for rc in rca_report.root_causes
            ]
            
            # Get suppressed alert IDs
            suppressed_alert_ids = [
                str(anomaly.anomaly_id) for anomaly in rca_report.suppressed_alerts
            ]
            
            return RCAResponse(
                anomaly_id=anomaly_id,
                root_causes=root_causes_info,
                suppressed_alerts=suppressed_alert_ids,
                generation_time=rca_report.generation_time
            )
        
        # If not in cache, raise not found error
        raise ResourceNotFoundError(
            resource_type="RCA Report",
            resource_id=anomaly_id
        )
        
    except ResourceNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error retrieving RCA report: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error retrieving RCA report: {str(e)}"
        )


def store_rca_report(anomaly_id: str, rca_report):
    """
    Store RCA report in cache for retrieval.
    
    This is a helper function used by the RCA engine to store reports.
    In production, this would store to a database or distributed cache.
    
    Args:
        anomaly_id: Anomaly identifier
        rca_report: RCAReport object to store
    """
    _rca_reports_cache[anomaly_id] = rca_report
    logger.info(f"Stored RCA report for anomaly {anomaly_id}")
