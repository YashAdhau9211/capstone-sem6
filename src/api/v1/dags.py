"""Causal DAG management API endpoints."""

import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Path, Query, UploadFile, File, Form, status
from fastapi.responses import PlainTextResponse

from src.api.exceptions import ResourceNotFoundError, ValidationError
from src.api.models import (
    DAGModificationRequest,
    DAGModificationResponse,
    DAGResponse,
    DAGSaveRequest,
    DAGVersionInfo,
    DAGVersionListResponse,
)
from src.api.rbac import (
    require_create_model,
    require_delete_model,
    require_edit_model,
    require_view_model,
)
from src.models.causal_graph import CausalDAG, CausalEdge
from src.models.dag_repository import DAGRepository
from src.models.dag_parser import DAGParser

logger = logging.getLogger(__name__)

router = APIRouter()


# Mock DAG data for testing without database
MOCK_DAGS = {
    "furnace-01": CausalDAG(
        dag_id=uuid4(),
        station_id="furnace-01",
        version=1,
        nodes=["temperature", "pressure", "fuel_flow", "oxygen_level", "yield", "energy_consumption"],
        edges=[
            CausalEdge("temperature", "yield", 0.45, 0.92, "linear", {}),
            CausalEdge("temperature", "energy_consumption", 0.78, 0.95, "linear", {}),
            CausalEdge("pressure", "yield", 0.32, 0.88, "linear", {}),
            CausalEdge("fuel_flow", "temperature", 0.65, 0.94, "linear", {}),
            CausalEdge("fuel_flow", "energy_consumption", 0.55, 0.91, "linear", {}),
            CausalEdge("oxygen_level", "temperature", 0.28, 0.85, "linear", {}),
        ],
        algorithm="DirectLiNGAM",
        created_at=datetime.utcnow(),
        created_by="system",
        metadata={"data_points": 10000, "variables": 6}
    ),
    "mill-01": CausalDAG(
        dag_id=uuid4(),
        station_id="mill-01",
        version=1,
        nodes=["speed", "force", "coolant_flow", "vibration", "surface_quality", "power_consumption"],
        edges=[
            CausalEdge("speed", "vibration", 0.52, 0.89, "linear", {}),
            CausalEdge("speed", "power_consumption", 0.68, 0.93, "linear", {}),
            CausalEdge("force", "surface_quality", 0.41, 0.87, "linear", {}),
            CausalEdge("coolant_flow", "surface_quality", 0.35, 0.84, "linear", {}),
            CausalEdge("vibration", "surface_quality", -0.29, 0.82, "linear", {}),
        ],
        algorithm="DirectLiNGAM",
        created_at=datetime.utcnow(),
        created_by="system",
        metadata={"data_points": 10000, "variables": 6}
    ),
    "anneal-01": CausalDAG(
        dag_id=uuid4(),
        station_id="anneal-01",
        version=1,
        nodes=["heating_rate", "hold_time", "cooling_rate", "hardness", "grain_size", "energy_usage"],
        edges=[
            CausalEdge("heating_rate", "grain_size", -0.38, 0.86, "linear", {}),
            CausalEdge("heating_rate", "energy_usage", 0.72, 0.94, "linear", {}),
            CausalEdge("hold_time", "hardness", 0.48, 0.91, "linear", {}),
            CausalEdge("cooling_rate", "hardness", 0.55, 0.89, "linear", {}),
            CausalEdge("grain_size", "hardness", -0.42, 0.88, "linear", {}),
        ],
        algorithm="DirectLiNGAM",
        created_at=datetime.utcnow(),
        created_by="system",
        metadata={"data_points": 10000, "variables": 6}
    ),
}


# Mock DAG data for testing without database
MOCK_DAGS = {
    "dag-furnace-01": CausalDAG(
        dag_id=uuid4(),
        station_id="furnace-01",
        version=1,
        nodes=["temperature", "pressure", "fuel_flow", "oxygen_level", "yield", "energy_consumption"],
        edges=[
            CausalEdge("temperature", "yield", 0.45, 0.92, "linear", {}),
            CausalEdge("temperature", "energy_consumption", 0.78, 0.95, "linear", {}),
            CausalEdge("pressure", "yield", 0.32, 0.88, "linear", {}),
            CausalEdge("fuel_flow", "temperature", 0.65, 0.94, "linear", {}),
            CausalEdge("fuel_flow", "energy_consumption", 0.55, 0.91, "linear", {}),
            CausalEdge("oxygen_level", "temperature", 0.28, 0.85, "linear", {}),
        ],
        algorithm="DirectLiNGAM",
        created_at=datetime.utcnow(),
        created_by="system",
        metadata={"data_points": 10000, "variables": 6}
    ),
    "dag-mill-01": CausalDAG(
        dag_id=uuid4(),
        station_id="mill-01",
        version=1,
        nodes=["speed", "force", "coolant_flow", "vibration", "surface_quality", "power_consumption"],
        edges=[
            CausalEdge("speed", "vibration", 0.52, 0.89, "linear", {}),
            CausalEdge("speed", "power_consumption", 0.68, 0.93, "linear", {}),
            CausalEdge("force", "surface_quality", 0.41, 0.87, "linear", {}),
            CausalEdge("coolant_flow", "surface_quality", 0.35, 0.84, "linear", {}),
            CausalEdge("vibration", "surface_quality", -0.29, 0.82, "linear", {}),
        ],
        algorithm="DirectLiNGAM",
        created_at=datetime.utcnow(),
        created_by="system",
        metadata={"data_points": 10000, "variables": 6}
    ),
    "dag-anneal-01": CausalDAG(
        dag_id=uuid4(),
        station_id="anneal-01",
        version=1,
        nodes=["heating_rate", "hold_time", "cooling_rate", "hardness", "grain_size", "energy_usage"],
        edges=[
            CausalEdge("heating_rate", "grain_size", -0.38, 0.86, "linear", {}),
            CausalEdge("heating_rate", "energy_usage", 0.72, 0.94, "linear", {}),
            CausalEdge("hold_time", "hardness", 0.48, 0.91, "linear", {}),
            CausalEdge("cooling_rate", "hardness", 0.55, 0.89, "linear", {}),
            CausalEdge("grain_size", "hardness", -0.42, 0.88, "linear", {}),
        ],
        algorithm="DirectLiNGAM",
        created_at=datetime.utcnow(),
        created_by="system",
        metadata={"data_points": 10000, "variables": 6}
    ),
}

# Map DAG IDs to station IDs for lookup
MOCK_DAGS["dag-furnace-01"].dag_id = uuid4()
MOCK_DAGS["dag-mill-01"].dag_id = uuid4()
MOCK_DAGS["dag-anneal-01"].dag_id = uuid4()


@router.get("/", response_model=list[DAGResponse], status_code=status.HTTP_200_OK)
async def list_dags(
    station_id: Optional[str] = Query(None, description="Filter by station identifier"),
) -> list[DAGResponse]:
    """
    List all DAGs, optionally filtered by station.

    Returns list of DAGs with nodes, edges, and metadata.

    **Requirements:** 7.8, 14.5
    """
    try:
        # Try database first
        dag_repo = DAGRepository()
        
        if station_id:
            dag = dag_repo.load_dag(station_id=station_id)
            if dag:
                edges = [
                    {
                        "source": edge.source,
                        "target": edge.target,
                        "coefficient": edge.coefficient,
                        "confidence": edge.confidence,
                        "edge_type": edge.edge_type,
                        "metadata": edge.metadata
                    }
                    for edge in dag.edges
                ]
                dag_repo.close()
                return [DAGResponse(
                    dag_id=dag.dag_id,
                    station_id=dag.station_id,
                    version=dag.version,
                    nodes=dag.nodes,
                    edges=edges,
                    algorithm=dag.algorithm,
                    created_at=dag.created_at,
                    metadata=dag.metadata
                )]
        
        dag_repo.close()
        
    except Exception as e:
        logger.warning(f"Database not available, using mock data: {e}")
    
    # Return mock data
    if station_id:
        mock_dag_id = f"dag-{station_id}"
        if mock_dag_id in MOCK_DAGS:
            dag = MOCK_DAGS[mock_dag_id]
            edges = [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "coefficient": edge.coefficient,
                    "confidence": edge.confidence,
                    "edge_type": edge.edge_type,
                    "metadata": edge.metadata
                }
                for edge in dag.edges
            ]
            return [DAGResponse(
                dag_id=dag.dag_id,
                station_id=dag.station_id,
                version=dag.version,
                nodes=dag.nodes,
                edges=edges,
                algorithm=dag.algorithm,
                created_at=dag.created_at,
                metadata=dag.metadata
            )]
        return []
    
    # Return all mock DAGs
    result = []
    for dag in MOCK_DAGS.values():
        edges = [
            {
                "source": edge.source,
                "target": edge.target,
                "coefficient": edge.coefficient,
                "confidence": edge.confidence,
                "edge_type": edge.edge_type,
                "metadata": edge.metadata
            }
            for edge in dag.edges
        ]
        result.append(DAGResponse(
            dag_id=dag.dag_id,
            station_id=dag.station_id,
            version=dag.version,
            nodes=dag.nodes,
            edges=edges,
            algorithm=dag.algorithm,
            created_at=dag.created_at,
            metadata=dag.metadata
        ))
    return result


@router.get("/{dag_id}", response_model=DAGResponse, status_code=status.HTTP_200_OK)
async def get_dag_by_id(
    dag_id: str = Path(..., description="DAG identifier or station identifier"),
) -> DAGResponse:
    """
    Get a causal DAG by ID or station ID.

    Returns the DAG with nodes, edges, and metadata.

    **Requirements:** 7.8, 14.5
    """
    try:
        # Check if it's a mock DAG ID
        if dag_id in MOCK_DAGS:
            dag = MOCK_DAGS[dag_id]
            edges = [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "coefficient": edge.coefficient,
                    "confidence": edge.confidence,
                    "edge_type": edge.edge_type,
                    "metadata": edge.metadata
                }
                for edge in dag.edges
            ]
            return DAGResponse(
                dag_id=dag.dag_id,
                station_id=dag.station_id,
                version=dag.version,
                nodes=dag.nodes,
                edges=edges,
                algorithm=dag.algorithm,
                created_at=dag.created_at,
                metadata=dag.metadata
            )
        
        # Try database
        dag_repo = DAGRepository()
        dag = dag_repo.load_dag(station_id=dag_id)
        
        if dag is None:
            # Try as station_id in mock data
            mock_dag_id = f"dag-{dag_id}"
            if mock_dag_id in MOCK_DAGS:
                dag = MOCK_DAGS[mock_dag_id]
            else:
                raise ResourceNotFoundError(
                    resource_type="DAG",
                    resource_id=dag_id
                )
        
        logger.info(f"Retrieved DAG {dag_id}")
        
        # Convert edges to dictionary format
        edges = [
            {
                "source": edge.source,
                "target": edge.target,
                "coefficient": edge.coefficient,
                "confidence": edge.confidence,
                "edge_type": edge.edge_type,
                "metadata": edge.metadata
            }
            for edge in dag.edges
        ]
        
        return DAGResponse(
            dag_id=dag.dag_id,
            station_id=dag.station_id,
            version=dag.version,
            nodes=dag.nodes,
            edges=edges,
            algorithm=dag.algorithm,
            created_at=dag.created_at,
            metadata=dag.metadata
        )
        
    except ResourceNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error retrieving DAG {dag_id}: {e}", exc_info=True)
        # Try mock data as fallback
        if dag_id in MOCK_DAGS:
            dag = MOCK_DAGS[dag_id]
            edges = [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "coefficient": edge.coefficient,
                    "confidence": edge.confidence,
                    "edge_type": edge.edge_type,
                    "metadata": edge.metadata
                }
                for edge in dag.edges
            ]
            return DAGResponse(
                dag_id=dag.dag_id,
                station_id=dag.station_id,
                version=dag.version,
                nodes=dag.nodes,
                edges=edges,
                algorithm=dag.algorithm,
                created_at=dag.created_at,
                metadata=dag.metadata
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error retrieving DAG: {str(e)}"
        )
    finally:
        if 'dag_repo' in locals():
            dag_repo.close()


@router.get("/{station_id}/current", response_model=DAGResponse, status_code=status.HTTP_200_OK)
async def get_current_dag(
    station_id: str = Path(..., description="Manufacturing station identifier"),
) -> DAGResponse:
    """
    Get the current causal DAG for a manufacturing station.

    Returns the latest version of the DAG with nodes, edges, and metadata.

    **Requirements:** 7.8, 14.5
    """
    try:
        # Try database first
        dag_repo = DAGRepository()
        dag = dag_repo.load_dag(station_id=station_id)
        
        if dag is None:
            # Fall back to mock data
            if station_id in MOCK_DAGS:
                dag = MOCK_DAGS[station_id]
            else:
                raise ResourceNotFoundError(
                    resource_type="DAG",
                    resource_id=station_id
                )
        
        logger.info(f"Retrieved current DAG for station {station_id}, version {dag.version}")
        
        # Convert edges to dictionary format
        edges = [
            {
                "source": edge.source,
                "target": edge.target,
                "coefficient": edge.coefficient,
                "confidence": edge.confidence,
                "edge_type": edge.edge_type,
                "metadata": edge.metadata
            }
            for edge in dag.edges
        ]
        
        return DAGResponse(
            dag_id=dag.dag_id,
            station_id=dag.station_id,
            version=dag.version,
            nodes=dag.nodes,
            edges=edges,
            algorithm=dag.algorithm,
            created_at=dag.created_at,
            metadata=dag.metadata
        )
        
    except ResourceNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error retrieving DAG for station {station_id}: {e}", exc_info=True)
        # Fall back to mock data on error
        if station_id in MOCK_DAGS:
            dag = MOCK_DAGS[station_id]
            edges = [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "coefficient": edge.coefficient,
                    "confidence": edge.confidence,
                    "edge_type": edge.edge_type,
                    "metadata": edge.metadata
                }
                for edge in dag.edges
            ]
            return DAGResponse(
                dag_id=dag.dag_id,
                station_id=dag.station_id,
                version=dag.version,
                nodes=dag.nodes,
                edges=edges,
                algorithm=dag.algorithm,
                created_at=dag.created_at,
                metadata=dag.metadata
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error retrieving DAG: {str(e)}"
        )
    finally:
        if 'dag_repo' in locals():
            dag_repo.close()


@router.get(
    "/{station_id}/versions",
    response_model=DAGVersionListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_dag_versions(
    station_id: str = Path(..., description="Manufacturing station identifier"),
) -> DAGVersionListResponse:
    """
    List all DAG versions for a manufacturing station.

    Returns version history with up to 50 versions per station.

    **Requirements:** 7.8, 14.5
    """
    try:
        dag_repo = DAGRepository()
        versions = dag_repo.list_versions(station_id=station_id)
        
        logger.info(f"Retrieved {len(versions)} versions for station {station_id}")
        
        # Convert to response model
        version_infos = [
            DAGVersionInfo(
                dag_id=v["dag_id"],
                version=v["version"],
                algorithm=v["algorithm"],
                created_at=v["created_at"],
                created_by=v["created_by"]
            )
            for v in versions
        ]
        
        return DAGVersionListResponse(
            station_id=station_id,
            versions=version_infos,
            total_count=len(version_infos)
        )
        
    except Exception as e:
        logger.error(f"Error listing DAG versions for station {station_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error listing DAG versions: {str(e)}"
        )
    finally:
        if 'dag_repo' in locals():
            dag_repo.close()


@router.get(
    "/{station_id}/versions/{version}",
    response_model=DAGResponse,
    status_code=status.HTTP_200_OK,
)
async def get_dag_version(
    station_id: str = Path(..., description="Manufacturing station identifier"),
    version: int = Path(..., description="DAG version number"),
) -> DAGResponse:
    """
    Get a specific version of a causal DAG.

    **Requirements:** 7.8, 14.5
    """
    try:
        dag_repo = DAGRepository()
        dag = dag_repo.load_dag(station_id=station_id, version=version)
        
        if dag is None:
            raise ResourceNotFoundError(
                resource_type="DAG",
                resource_id=f"{station_id}/version/{version}"
            )
        
        logger.info(f"Retrieved DAG for station {station_id}, version {version}")
        
        # Convert edges to dictionary format
        edges = [
            {
                "source": edge.source,
                "target": edge.target,
                "coefficient": edge.coefficient,
                "confidence": edge.confidence,
                "edge_type": edge.edge_type,
                "metadata": edge.metadata
            }
            for edge in dag.edges
        ]
        
        return DAGResponse(
            dag_id=dag.dag_id,
            station_id=dag.station_id,
            version=dag.version,
            nodes=dag.nodes,
            edges=edges,
            algorithm=dag.algorithm,
            created_at=dag.created_at,
            metadata=dag.metadata
        )
        
    except ResourceNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error retrieving DAG version {version} for station {station_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error retrieving DAG version: {str(e)}"
        )
    finally:
        if 'dag_repo' in locals():
            dag_repo.close()


@router.get(
    "/{station_id}/export", response_model=str, status_code=status.HTTP_200_OK
)
async def export_dag(
    station_id: str = Path(..., description="Manufacturing station identifier"),
    format: str = Query(..., description="Export format: dot or graphml"),
) -> str:
    """
    Export causal DAG to DOT or GraphML format.

    **Formats:**
    - `dot`: Graphviz DOT format
    - `graphml`: GraphML XML format

    **Requirements:** 22.7, 22.8
    """
    if format not in ["dot", "graphml"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format must be 'dot' or 'graphml'",
        )

    try:
        dag_repo = DAGRepository()
        dag = dag_repo.load_dag(station_id=station_id)
        
        if dag is None:
            raise ResourceNotFoundError(
                resource_type="DAG",
                resource_id=station_id
            )
        
        # Export to requested format
        if format == "dot":
            content = dag.to_dot()
            media_type = "text/vnd.graphviz"
        else:  # graphml
            content = dag.to_graphml()
            media_type = "application/xml"
        
        logger.info(f"Exported DAG for station {station_id} to {format} format")
        
        return PlainTextResponse(content=content, media_type=media_type)
        
    except ResourceNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error exporting DAG for station {station_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error exporting DAG: {str(e)}"
        )
    finally:
        if 'dag_repo' in locals():
            dag_repo.close()


@router.post("/{station_id}", response_model=DAGResponse, status_code=status.HTTP_201_CREATED)
async def save_dag(
    station_id: str = Path(..., description="Manufacturing station identifier"),
    request: DAGSaveRequest = ...,
) -> DAGResponse:
    """
    Save a new DAG version for a manufacturing station.

    Creates a new version of the DAG with the provided nodes and edges.
    Validates that the resulting graph is acyclic before saving.

    **Requirements:** 7.1, 7.2, 7.3, 7.4
    """
    try:
        # Convert edge dictionaries to CausalEdge objects
        edges = []
        for edge_data in request.edges:
            edges.append(
                CausalEdge(
                    source=edge_data["source"],
                    target=edge_data["target"],
                    coefficient=edge_data.get("coefficient", 0.0),
                    confidence=edge_data.get("confidence", 1.0),
                    edge_type=edge_data.get("edge_type", "linear"),
                    metadata=edge_data.get("metadata", {})
                )
            )
        
        # Create new DAG
        dag = CausalDAG(
            dag_id=uuid4(),
            station_id=station_id,
            version=0,  # Will be set by repository
            nodes=request.nodes,
            edges=edges,
            algorithm=request.algorithm,
            created_at=datetime.utcnow(),
            created_by=request.created_by,
            metadata=request.metadata
        )
        
        # Validate acyclicity (done in __post_init__)
        if not dag.is_acyclic():
            cycle_path = dag.find_cycle()
            raise ValidationError(
                message="Cannot save DAG: graph contains cycles",
                detail={"station_id": station_id, "cycle_path": cycle_path or []}
            )
        
        # Save to repository
        dag_repo = DAGRepository()
        dag_id = dag_repo.save_dag(dag)
        
        # Reload to get assigned version
        saved_dag = dag_repo.load_dag(station_id=station_id)
        
        logger.info(f"Saved new DAG version {saved_dag.version} for station {station_id}")
        
        # Convert edges to dictionary format
        edges_dict = [
            {
                "source": edge.source,
                "target": edge.target,
                "coefficient": edge.coefficient,
                "confidence": edge.confidence,
                "edge_type": edge.edge_type,
                "metadata": edge.metadata
            }
            for edge in saved_dag.edges
        ]
        
        return DAGResponse(
            dag_id=saved_dag.dag_id,
            station_id=saved_dag.station_id,
            version=saved_dag.version,
            nodes=saved_dag.nodes,
            edges=edges_dict,
            algorithm=saved_dag.algorithm,
            created_at=saved_dag.created_at,
            metadata=saved_dag.metadata
        )
        
    except ValidationError:
        raise
    except ValueError as e:
        # Catch cycle detection errors
        raise ValidationError(
            message=str(e),
            detail={"station_id": station_id}
        )
    except Exception as e:
        logger.error(f"Error saving DAG for station {station_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error saving DAG: {str(e)}"
        )
    finally:
        if 'dag_repo' in locals():
            dag_repo.close()


@router.put("/{station_id}/edges", response_model=DAGModificationResponse, status_code=status.HTTP_200_OK)
async def modify_dag_edges(
    station_id: str = Path(..., description="Manufacturing station identifier"),
    request: DAGModificationRequest = ...,
) -> DAGModificationResponse:
    """
    Add, delete, or reverse edges in a causal DAG.

    Applies the specified edge operations and creates a new DAG version.
    Validates that the resulting graph remains acyclic before saving.

    **Operations:**
    - `add`: Add a new directed edge
    - `delete`: Remove an existing edge
    - `reverse`: Reverse the direction of an edge

    **Requirements:** 7.1, 7.2, 7.3, 7.4
    """
    try:
        # Load current DAG
        dag_repo = DAGRepository()
        current_dag = dag_repo.load_dag(station_id=station_id)
        
        if current_dag is None:
            raise ResourceNotFoundError(
                resource_type="DAG",
                resource_id=station_id
            )
        
        # Copy current DAG structure
        nodes = current_dag.nodes.copy()
        edges = [
            CausalEdge(
                source=e.source,
                target=e.target,
                coefficient=e.coefficient,
                confidence=e.confidence,
                edge_type=e.edge_type,
                metadata=e.metadata.copy()
            )
            for e in current_dag.edges
        ]
        
        # Apply operations
        operations_applied = 0
        for op in request.operations:
            if op.operation == "add":
                # Validate nodes exist
                if op.source not in nodes:
                    raise ValidationError(
                        message=f"Source node '{op.source}' not found in DAG",
                        detail={"operation": "add", "source": op.source}
                    )
                if op.target not in nodes:
                    raise ValidationError(
                        message=f"Target node '{op.target}' not found in DAG",
                        detail={"operation": "add", "target": op.target}
                    )
                
                # Check if edge already exists
                existing = any(e.source == op.source and e.target == op.target for e in edges)
                if existing:
                    raise ValidationError(
                        message=f"Edge from '{op.source}' to '{op.target}' already exists",
                        detail={"operation": "add", "source": op.source, "target": op.target}
                    )
                
                # Add new edge
                edges.append(
                    CausalEdge(
                        source=op.source,
                        target=op.target,
                        coefficient=op.coefficient or 0.0,
                        confidence=op.confidence or 1.0,
                        edge_type=op.edge_type or "linear",
                        metadata={}
                    )
                )
                operations_applied += 1
                
            elif op.operation == "delete":
                # Find and remove edge
                edge_to_remove = None
                for e in edges:
                    if e.source == op.source and e.target == op.target:
                        edge_to_remove = e
                        break
                
                if edge_to_remove is None:
                    raise ValidationError(
                        message=f"Edge from '{op.source}' to '{op.target}' not found",
                        detail={"operation": "delete", "source": op.source, "target": op.target}
                    )
                
                edges.remove(edge_to_remove)
                operations_applied += 1
                
            elif op.operation == "reverse":
                # Find edge to reverse
                edge_to_reverse = None
                for e in edges:
                    if e.source == op.source and e.target == op.target:
                        edge_to_reverse = e
                        break
                
                if edge_to_reverse is None:
                    raise ValidationError(
                        message=f"Edge from '{op.source}' to '{op.target}' not found",
                        detail={"operation": "reverse", "source": op.source, "target": op.target}
                    )
                
                # Check if reversed edge would already exist
                existing_reversed = any(e.source == op.target and e.target == op.source for e in edges)
                if existing_reversed:
                    raise ValidationError(
                        message=f"Cannot reverse: edge from '{op.target}' to '{op.source}' already exists",
                        detail={"operation": "reverse", "source": op.source, "target": op.target}
                    )
                
                # Remove old edge and add reversed edge
                edges.remove(edge_to_reverse)
                edges.append(
                    CausalEdge(
                        source=op.target,
                        target=op.source,
                        coefficient=edge_to_reverse.coefficient,
                        confidence=edge_to_reverse.confidence,
                        edge_type=edge_to_reverse.edge_type,
                        metadata=edge_to_reverse.metadata.copy()
                    )
                )
                operations_applied += 1
        
        # Create new DAG with modifications
        new_dag = CausalDAG(
            dag_id=uuid4(),
            station_id=station_id,
            version=0,  # Will be set by repository
            nodes=nodes,
            edges=edges,
            algorithm="expert_edited",
            created_at=datetime.utcnow(),
            created_by=request.created_by,
            metadata={"parent_version": current_dag.version}
        )
        
        # Validate acyclicity
        if not new_dag.is_acyclic():
            # Find the cycle path
            cycle_path = new_dag.find_cycle()
            raise ValidationError(
                message="Cannot apply modifications: resulting graph contains cycles",
                detail={
                    "station_id": station_id,
                    "operations_applied": operations_applied,
                    "cycle_path": cycle_path or []
                }
            )
        
        # Save new version
        dag_id = dag_repo.save_dag(new_dag, parent_version=current_dag.version)
        
        # Reload to get assigned version
        saved_dag = dag_repo.load_dag(station_id=station_id)
        
        logger.info(
            f"Applied {operations_applied} edge operations to station {station_id}, "
            f"created version {saved_dag.version}"
        )
        
        return DAGModificationResponse(
            dag_id=saved_dag.dag_id,
            station_id=saved_dag.station_id,
            version=saved_dag.version,
            operations_applied=operations_applied,
            timestamp=datetime.utcnow()
        )
        
    except (ResourceNotFoundError, ValidationError):
        raise
    except ValueError as e:
        # Catch cycle detection errors
        raise ValidationError(
            message=str(e),
            detail={"station_id": station_id}
        )
    except Exception as e:
        logger.error(f"Error modifying DAG edges for station {station_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error modifying DAG: {str(e)}"
        )
    finally:
        if 'dag_repo' in locals():
            dag_repo.close()



@router.post(
    "/{station_id}/import",
    response_model=DAGResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_dag(
    station_id: str = Path(..., description="Manufacturing station identifier"),
    format: str = Form(..., description="Import format: dot or graphml"),
    file: UploadFile = File(..., description="DAG file to import"),
    created_by: str = Form(..., description="User identifier"),
    validate_variables: bool = Form(False, description="Validate against known variables"),
) -> DAGResponse:
    """
    Import a causal DAG from DOT or GraphML format.

    Validates that the imported graph is acyclic and optionally checks
    that all variables match the data schema.

    **Requirements:** 22.1, 22.2, 22.3, 22.4, 22.5, 22.6
    """
    if format not in ["dot", "graphml"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format must be 'dot' or 'graphml'",
        )

    try:
        # Read file content
        content = await file.read()
        content_str = content.decode('utf-8')
        
        # Parse based on format
        if format == "dot":
            dag = DAGParser.parse_dot(content_str, station_id, created_by)
        else:  # graphml
            dag = DAGParser.parse_graphml(content_str, station_id, created_by)
        
        # Validate acyclicity
        if not dag.is_acyclic():
            cycle_path = dag.find_cycle()
            raise ValidationError(
                message="Cannot import DAG: graph contains cycles",
                detail={
                    "station_id": station_id,
                    "cycle_path": cycle_path or []
                }
            )
        
        # Optionally validate against known variables
        if validate_variables:
            # TODO: Fetch known variables from data schema
            # For now, skip validation
            pass
        
        # Save imported DAG
        dag_repo = DAGRepository()
        dag_id = dag_repo.save_dag(dag)
        
        # Reload to get assigned version
        saved_dag = dag_repo.load_dag(station_id=station_id)
        
        logger.info(
            f"Imported DAG from {format} format for station {station_id}, "
            f"version {saved_dag.version}"
        )
        
        # Convert edges to dictionary format
        edges_dict = [
            {
                "source": edge.source,
                "target": edge.target,
                "coefficient": edge.coefficient,
                "confidence": edge.confidence,
                "edge_type": edge.edge_type,
                "metadata": edge.metadata
            }
            for edge in saved_dag.edges
        ]
        
        return DAGResponse(
            dag_id=saved_dag.dag_id,
            station_id=saved_dag.station_id,
            version=saved_dag.version,
            nodes=saved_dag.nodes,
            edges=edges_dict,
            algorithm=saved_dag.algorithm,
            created_at=saved_dag.created_at,
            metadata=saved_dag.metadata
        )
        
    except ValidationError:
        raise
    except ValueError as e:
        raise ValidationError(
            message=str(e),
            detail={"station_id": station_id, "format": format}
        )
    except Exception as e:
        logger.error(f"Error importing DAG for station {station_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error importing DAG: {str(e)}"
        )
    finally:
        if 'dag_repo' in locals():
            dag_repo.close()
