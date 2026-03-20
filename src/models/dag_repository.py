"""DAG repository for versioned storage of causal graphs."""

import json
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .causal_graph import CausalDAG, CausalEdge
from config.settings import settings


logger = logging.getLogger(__name__)


class DAGRepository:
    """Repository for storing and retrieving versioned causal DAGs."""
    
    def __init__(self, connection_url: Optional[str] = None):
        """Initialize DAG repository.
        
        Args:
            connection_url: PostgreSQL connection URL. If None, uses settings.
        """
        self.connection_url = connection_url or settings.postgres_url
        self._engine: Optional[Engine] = None
    
    def _get_engine(self) -> Engine:
        """Get or create SQLAlchemy engine."""
        if self._engine is None:
            # Determine if we're using SQLite (which has different pool parameters)
            is_sqlite = self.connection_url.startswith("sqlite")
            
            if is_sqlite:
                # SQLite uses SingletonThreadPool which doesn't support max_overflow
                self._engine = create_engine(
                    self.connection_url,
                    pool_pre_ping=True,
                    echo=False
                )
            else:
                # PostgreSQL and other databases support QueuePool with max_overflow
                self._engine = create_engine(
                    self.connection_url,
                    pool_size=10,
                    max_overflow=20,
                    pool_pre_ping=True,
                    echo=False
                )
        return self._engine
    
    def save_dag(
        self,
        dag: CausalDAG,
        parent_version: Optional[int] = None
    ) -> str:
        """Save a DAG with automatic version increment.
        
        Args:
            dag: CausalDAG to save
            parent_version: Parent version for tracking expert edits (optional)
            
        Returns:
            dag_id as string
            
        Raises:
            ValueError: If DAG validation fails
            RuntimeError: If database operation fails
        """
        # Validate DAG
        if not dag.is_acyclic():
            raise ValueError("Cannot save DAG with cycles")
        
        engine = self._get_engine()
        
        try:
            with engine.begin() as conn:
                # Get next version number for this station
                version_query = text("""
                    SELECT COALESCE(MAX(version), 0) + 1 as next_version
                    FROM causal_dags
                    WHERE station_id = :station_id
                """)
                result = conn.execute(
                    version_query,
                    {"station_id": dag.station_id}
                )
                next_version = result.fetchone()[0]
                
                # Serialize DAG to JSONB
                dag_data = self._serialize_dag(dag)
                
                # Insert new DAG version
                insert_query = text("""
                    INSERT INTO causal_dags (
                        dag_id, station_id, version, dag_data, algorithm,
                        created_at, created_by, parent_version
                    ) VALUES (
                        :dag_id, :station_id, :version, :dag_data, :algorithm,
                        :created_at, :created_by, :parent_version
                    )
                """)
                
                conn.execute(
                    insert_query,
                    {
                        "dag_id": str(dag.dag_id),
                        "station_id": dag.station_id,
                        "version": next_version,
                        "dag_data": json.dumps(dag_data),
                        "algorithm": dag.algorithm,
                        "created_at": dag.created_at,
                        "created_by": dag.created_by,
                        "parent_version": parent_version
                    }
                )
                
                logger.info(
                    f"Saved DAG {dag.dag_id} for station {dag.station_id} "
                    f"as version {next_version}"
                )
                
                return str(dag.dag_id)
                
        except IntegrityError as e:
            logger.error(f"Integrity error saving DAG: {e}")
            raise RuntimeError(f"Failed to save DAG: {e}")
        except SQLAlchemyError as e:
            logger.error(f"Database error saving DAG: {e}")
            raise RuntimeError(f"Database error: {e}")
    
    def load_dag(
        self,
        station_id: str,
        version: Optional[int] = None
    ) -> Optional[CausalDAG]:
        """Load a DAG by station_id and version.
        
        Args:
            station_id: Manufacturing station identifier
            version: Version number. If None, loads latest version.
            
        Returns:
            CausalDAG if found, None otherwise
            
        Raises:
            RuntimeError: If database operation fails
        """
        engine = self._get_engine()
        
        try:
            with engine.connect() as conn:
                if version is None:
                    # Load latest version
                    query = text("""
                        SELECT dag_id, station_id, version, dag_data, algorithm,
                               created_at, created_by, parent_version
                        FROM causal_dags
                        WHERE station_id = :station_id
                        ORDER BY version DESC
                        LIMIT 1
                    """)
                    result = conn.execute(query, {"station_id": station_id})
                else:
                    # Load specific version
                    query = text("""
                        SELECT dag_id, station_id, version, dag_data, algorithm,
                               created_at, created_by, parent_version
                        FROM causal_dags
                        WHERE station_id = :station_id AND version = :version
                    """)
                    result = conn.execute(
                        query,
                        {"station_id": station_id, "version": version}
                    )
                
                row = result.fetchone()
                
                if row is None:
                    logger.warning(
                        f"No DAG found for station {station_id} "
                        f"version {version or 'latest'}"
                    )
                    return None
                
                # Deserialize DAG
                dag = self._deserialize_dag(
                    dag_id=UUID(row[0]),
                    station_id=row[1],
                    version=row[2],
                    dag_data=json.loads(row[3]) if isinstance(row[3], str) else row[3],
                    algorithm=row[4],
                    created_at=row[5],
                    created_by=row[6]
                )
                
                logger.info(
                    f"Loaded DAG {dag.dag_id} for station {station_id} "
                    f"version {dag.version}"
                )
                
                return dag
                
        except SQLAlchemyError as e:
            logger.error(f"Database error loading DAG: {e}")
            raise RuntimeError(f"Database error: {e}")
    
    def list_versions(self, station_id: str) -> List[dict]:
        """List version history for a station.
        
        Args:
            station_id: Manufacturing station identifier
            
        Returns:
            List of version metadata dictionaries with keys:
            - version: Version number
            - dag_id: DAG identifier
            - algorithm: Algorithm used
            - created_at: Creation timestamp
            - created_by: User who created this version
            - parent_version: Parent version (for expert edits)
            
        Raises:
            RuntimeError: If database operation fails
        """
        engine = self._get_engine()
        
        try:
            with engine.connect() as conn:
                query = text("""
                    SELECT version, dag_id, algorithm, created_at, created_by, parent_version
                    FROM causal_dags
                    WHERE station_id = :station_id
                    ORDER BY version DESC
                """)
                result = conn.execute(query, {"station_id": station_id})
                
                versions = []
                for row in result:
                    versions.append({
                        "version": row[0],
                        "dag_id": str(row[1]),
                        "algorithm": row[2],
                        "created_at": row[3],
                        "created_by": row[4],
                        "parent_version": row[5]
                    })
                
                logger.info(
                    f"Retrieved {len(versions)} versions for station {station_id}"
                )
                
                return versions
                
        except SQLAlchemyError as e:
            logger.error(f"Database error listing versions: {e}")
            raise RuntimeError(f"Database error: {e}")
    
    def _serialize_dag(self, dag: CausalDAG) -> dict:
        """Serialize CausalDAG to dictionary for JSONB storage.
        
        Args:
            dag: CausalDAG to serialize
            
        Returns:
            Dictionary representation
        """
        return {
            "nodes": dag.nodes,
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "coefficient": edge.coefficient,
                    "confidence": edge.confidence,
                    "edge_type": edge.edge_type,
                    "metadata": edge.metadata
                }
                for edge in dag.edges
            ],
            "metadata": dag.metadata
        }
    
    def _deserialize_dag(
        self,
        dag_id: UUID,
        station_id: str,
        version: int,
        dag_data: dict,
        algorithm: str,
        created_at: datetime,
        created_by: str
    ) -> CausalDAG:
        """Deserialize dictionary to CausalDAG object.
        
        Args:
            dag_id: DAG identifier
            station_id: Station identifier
            version: Version number
            dag_data: Serialized DAG data
            algorithm: Algorithm used
            created_at: Creation timestamp
            created_by: User who created this version
            
        Returns:
            CausalDAG object
        """
        # Reconstruct edges
        edges = [
            CausalEdge(
                source=edge_data["source"],
                target=edge_data["target"],
                coefficient=edge_data["coefficient"],
                confidence=edge_data["confidence"],
                edge_type=edge_data["edge_type"],
                metadata=edge_data.get("metadata", {})
            )
            for edge_data in dag_data["edges"]
        ]
        
        # Create DAG (temporarily disable validation during construction)
        dag = object.__new__(CausalDAG)
        dag.dag_id = dag_id
        dag.station_id = station_id
        dag.version = version
        dag.nodes = dag_data["nodes"]
        dag.edges = edges
        dag.algorithm = algorithm
        dag.created_at = created_at
        dag.created_by = created_by
        dag.metadata = dag_data.get("metadata", {})
        
        # Validate after construction
        if not dag.is_acyclic():
            raise ValueError(
                f"Deserialized DAG {dag_id} contains cycles - data corruption?"
            )
        
        return dag
    
    def close(self):
        """Close database connection and dispose engine."""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            logger.info("DAG repository connection closed")
