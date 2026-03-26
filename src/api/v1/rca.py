"""Root cause analysis API endpoints."""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, status

from src.api.exceptions import ResourceNotFoundError
from src.api.models import RCAResponse, RootCauseInfo

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory storage for RCA reports (in production, use database or cache)
_rca_reports_cache = {}

# Mock RCA reports for testing
MOCK_RCA_REPORTS = {
    "anomaly-001": {
        "anomaly_id": "anomaly-001",
        "station_id": "furnace-01",
        "variable": "yield",
        "timestamp": datetime.utcnow().isoformat(),
        "root_causes": [
            {
                "variable": "fuel_flow",
                "attribution_score": 0.68,
                "confidence_interval": (0.62, 0.74),
                "causal_path": ["fuel_flow", "temperature", "yield"]
            },
            {
                "variable": "oxygen_level",
                "attribution_score": 0.42,
                "confidence_interval": (0.35, 0.49),
                "causal_path": ["oxygen_level", "temperature", "yield"]
            },
            {
                "variable": "pressure",
                "attribution_score": 0.28,
                "confidence_interval": (0.22, 0.34),
                "causal_path": ["pressure", "yield"]
            }
        ],
        "suppressed_alerts": ["anomaly-002", "anomaly-003"],
        "generation_time": datetime.utcnow().isoformat()
    },
    "anomaly-002": {
        "anomaly_id": "anomaly-002",
        "station_id": "mill-01",
        "variable": "surface_quality",
        "timestamp": datetime.utcnow().isoformat(),
        "root_causes": [
            {
                "variable": "vibration",
                "attribution_score": 0.55,
                "confidence_interval": (0.48, 0.62),
                "causal_path": ["vibration", "surface_quality"]
            },
            {
                "variable": "speed",
                "attribution_score": 0.48,
                "confidence_interval": (0.41, 0.55),
                "causal_path": ["speed", "vibration", "surface_quality"]
            }
        ],
        "suppressed_alerts": [],
        "generation_time": datetime.utcnow().isoformat()
    }
}


@router.get("/", status_code=status.HTTP_200_OK)
async def list_rca_reports(
    station_id: Optional[str] = Query(None, description="Filter by station identifier"),
) -> list[dict]:
    """
    List all RCA reports, optionally filtered by station.

    **Requirements:** 12.5, 26.3
    """
    try:
        reports = []
        
        # Check mock data
        for anomaly_id, report_data in MOCK_RCA_REPORTS.items():
            if station_id and report_data.get("station_id") != station_id:
                continue
            
            reports.append({
                "anomaly_id": report_data["anomaly_id"],
                "station_id": report_data["station_id"],
                "variable": report_data["variable"],
                "timestamp": report_data["timestamp"],
                "root_cause_count": len(report_data["root_causes"]),
                "suppressed_alert_count": len(report_data["suppressed_alerts"])
            })
        
        return reports
        
    except Exception as e:
        logger.error(f"Error listing RCA reports: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error listing RCA reports: {str(e)}"
        )


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
        # Try to retrieve from cache first
        if anomaly_id in _rca_reports_cache:
            rca_report = _rca_reports_cache[anomaly_id]
            
            logger.info(f"Retrieved RCA report for anomaly {anomaly_id} from cache")
            
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
        
        # Try mock data
        if anomaly_id in MOCK_RCA_REPORTS:
            report_data = MOCK_RCA_REPORTS[anomaly_id]
            
            logger.info(f"Retrieved RCA report for anomaly {anomaly_id} from mock data")
            
            root_causes_info = [
                RootCauseInfo(
                    variable=rc["variable"],
                    attribution_score=rc["attribution_score"],
                    confidence_interval=rc["confidence_interval"],
                    causal_path=rc["causal_path"]
                )
                for rc in report_data["root_causes"]
            ]
            
            return RCAResponse(
                anomaly_id=anomaly_id,
                root_causes=root_causes_info,
                suppressed_alerts=report_data["suppressed_alerts"],
                generation_time=datetime.fromisoformat(report_data["generation_time"])
            )
        
        # If not found anywhere, raise not found error
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
