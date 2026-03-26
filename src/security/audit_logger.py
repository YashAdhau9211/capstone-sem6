"""Audit logging for comprehensive tracking of user actions and system decisions.

This module provides immutable audit logging with:
- Login/logout event tracking
- DAG modification tracking
- Simulation execution tracking
- Data export tracking
- Query interface with filtering
- CSV export functionality
- Encryption for sensitive data
"""

import csv
import io
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from cryptography.fernet import Fernet
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from config.settings import settings


logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Types of auditable actions."""
    
    LOGIN = "login"
    LOGOUT = "logout"
    DAG_CREATE = "dag_create"
    DAG_MODIFY = "dag_modify"
    DAG_DELETE = "dag_delete"
    DAG_EXPORT = "dag_export"
    SIMULATION_RUN = "simulation_run"
    DATA_EXPORT = "data_export"
    MODEL_CREATE = "model_create"
    MODEL_DELETE = "model_delete"
    CONFIG_CHANGE = "config_change"
    API_REQUEST = "api_request"


class ResourceType(Enum):
    """Types of resources that can be audited."""
    
    USER = "user"
    DAG = "dag"
    MODEL = "model"
    SIMULATION = "simulation"
    DATA = "data"
    CONFIG = "config"
    API = "api"


class Result(Enum):
    """Result of an audited action."""
    
    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"


@dataclass
class AuditEvent:
    """Audit event data structure."""
    
    log_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    action_type: str = ""
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    session_id: Optional[str] = None
    result: str = Result.SUCCESS.value


@dataclass
class AuditFilters:
    """Filters for querying audit logs."""
    
    user_id: Optional[str] = None
    action_type: Optional[str] = None
    resource_type: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    result: Optional[str] = None
    limit: int = 1000


class AuditLogger:
    """Audit logger with immutable logging and query capabilities.
    
    Provides comprehensive audit logging including:
    - Login/logout events
    - DAG modifications
    - Simulation executions
    - Data exports
    - Query interface with filtering
    - CSV export functionality
    - Encryption for sensitive data in details field
    
    Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7
    """
    
    def __init__(
        self,
        connection_url: Optional[str] = None,
        encryption_key: Optional[bytes] = None
    ):
        """Initialize audit logger.
        
        Args:
            connection_url: PostgreSQL connection URL. If None, uses settings.
            encryption_key: Encryption key for sensitive data. If None, generates new key.
        """
        self.connection_url = connection_url or settings.postgres_url
        self._engine: Optional[Engine] = None
        
        # Initialize encryption
        if encryption_key is None:
            # In production, this should be loaded from secure storage (e.g., HashiCorp Vault)
            encryption_key = Fernet.generate_key()
            logger.warning(
                "Using generated encryption key. In production, load from secure storage."
            )
        
        self._cipher = Fernet(encryption_key)
    
    def _get_engine(self) -> Engine:
        """Get or create SQLAlchemy engine."""
        if self._engine is None:
            # Determine if we're using SQLite (which has different pool parameters)
            is_sqlite = self.connection_url.startswith("sqlite")
            
            if is_sqlite:
                self._engine = create_engine(
                    self.connection_url,
                    pool_pre_ping=True,
                    echo=False
                )
            else:
                self._engine = create_engine(
                    self.connection_url,
                    pool_size=10,
                    max_overflow=20,
                    pool_pre_ping=True,
                    echo=False
                )
        return self._engine
    
    def _encrypt_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive fields in details dictionary.
        
        Encrypts fields that may contain sensitive information:
        - passwords
        - tokens
        - api_keys
        - credentials
        
        Args:
            data: Dictionary with potentially sensitive data
            
        Returns:
            Dictionary with sensitive fields encrypted
        """
        sensitive_fields = {"password", "token", "api_key", "credentials", "secret"}
        encrypted_data = data.copy()
        
        for key, value in data.items():
            if key.lower() in sensitive_fields and value is not None:
                # Convert to string, encrypt, and encode as base64
                value_str = str(value)
                encrypted_bytes = self._cipher.encrypt(value_str.encode())
                encrypted_data[key] = encrypted_bytes.decode()
                encrypted_data[f"{key}_encrypted"] = True
        
        return encrypted_data
    
    def log_event(
        self,
        user_id: Optional[str],
        action_type: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None,
        result: str = Result.SUCCESS.value
    ) -> UUID:
        """Log an audit event.
        
        Main logging method for recording user actions and system decisions.
        
        Args:
            user_id: User identifier
            action_type: Type of action (from ActionType enum)
            resource_type: Type of resource affected (from ResourceType enum)
            resource_id: Identifier of affected resource
            details: Additional details (sensitive fields will be encrypted)
            ip_address: Client IP address
            session_id: Session identifier
            result: Result of action (success, failure, denied)
            
        Returns:
            log_id of the created audit entry
            
        Raises:
            RuntimeError: If database operation fails
            
        Requirements: 17.1, 17.2, 17.3, 17.4
        """
        log_id = uuid4()
        timestamp = datetime.utcnow()
        
        # Encrypt sensitive data in details
        if details:
            details = self._encrypt_sensitive_data(details)
        else:
            details = {}
        
        engine = self._get_engine()
        
        try:
            with engine.begin() as conn:
                query = text("""
                    INSERT INTO audit_logs (
                        log_id, timestamp, user_id, action_type, resource_type,
                        resource_id, details, ip_address, session_id, result
                    ) VALUES (
                        :log_id, :timestamp, :user_id, :action_type, :resource_type,
                        :resource_id, :details, :ip_address, :session_id, :result
                    )
                """)
                
                conn.execute(
                    query,
                    {
                        "log_id": str(log_id),
                        "timestamp": timestamp,
                        "user_id": user_id,
                        "action_type": action_type,
                        "resource_type": resource_type,
                        "resource_id": resource_id,
                        "details": json.dumps(details),
                        "ip_address": ip_address,
                        "session_id": session_id,
                        "result": result
                    }
                )
                
                logger.info(
                    f"Audit log created: {action_type} by {user_id} "
                    f"on {resource_type}/{resource_id} - {result}"
                )
                
                return log_id
                
        except SQLAlchemyError as e:
            logger.error(f"Database error logging audit event: {e}")
            raise RuntimeError(f"Failed to log audit event: {e}")
    
    def log_login(
        self,
        user_id: str,
        ip_address: str,
        session_id: Optional[str] = None,
        result: str = Result.SUCCESS.value,
        details: Optional[Dict[str, Any]] = None
    ) -> UUID:
        """Log a login event.
        
        Convenience method for logging user login events.
        
        Args:
            user_id: User identifier
            ip_address: Client IP address
            session_id: Session identifier
            result: Result of login attempt
            details: Additional details (e.g., authentication method)
            
        Returns:
            log_id of the created audit entry
            
        Requirements: 17.1
        """
        return self.log_event(
            user_id=user_id,
            action_type=ActionType.LOGIN.value,
            resource_type=ResourceType.USER.value,
            resource_id=user_id,
            details=details or {},
            ip_address=ip_address,
            session_id=session_id,
            result=result
        )
    
    def log_logout(
        self,
        user_id: str,
        ip_address: str,
        session_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> UUID:
        """Log a logout event.
        
        Convenience method for logging user logout events.
        
        Args:
            user_id: User identifier
            ip_address: Client IP address
            session_id: Session identifier
            details: Additional details
            
        Returns:
            log_id of the created audit entry
            
        Requirements: 17.1
        """
        return self.log_event(
            user_id=user_id,
            action_type=ActionType.LOGOUT.value,
            resource_type=ResourceType.USER.value,
            resource_id=user_id,
            details=details or {},
            ip_address=ip_address,
            session_id=session_id,
            result=Result.SUCCESS.value
        )
    
    def log_dag_modification(
        self,
        user_id: str,
        dag_id: str,
        station_id: str,
        change_details: Dict[str, Any],
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None,
        result: str = Result.SUCCESS.value
    ) -> UUID:
        """Log a DAG modification event.
        
        Convenience method for logging DAG changes (create, modify, delete).
        
        Args:
            user_id: User identifier
            dag_id: DAG identifier
            station_id: Station identifier
            change_details: Details of the change (edges added/removed, etc.)
            ip_address: Client IP address
            session_id: Session identifier
            result: Result of modification
            
        Returns:
            log_id of the created audit entry
            
        Requirements: 17.2
        """
        details = {
            "station_id": station_id,
            **change_details
        }
        
        return self.log_event(
            user_id=user_id,
            action_type=ActionType.DAG_MODIFY.value,
            resource_type=ResourceType.DAG.value,
            resource_id=dag_id,
            details=details,
            ip_address=ip_address,
            session_id=session_id,
            result=result
        )
    
    def log_simulation(
        self,
        user_id: str,
        station_id: str,
        interventions: Dict[str, float],
        results: Dict[str, Any],
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None,
        result: str = Result.SUCCESS.value
    ) -> UUID:
        """Log a simulation execution event.
        
        Convenience method for logging simulation runs.
        
        Args:
            user_id: User identifier
            station_id: Station identifier
            interventions: Intervention parameters
            results: Simulation results
            ip_address: Client IP address
            session_id: Session identifier
            result: Result of simulation
            
        Returns:
            log_id of the created audit entry
            
        Requirements: 17.3
        """
        details = {
            "station_id": station_id,
            "interventions": interventions,
            "results": results
        }
        
        return self.log_event(
            user_id=user_id,
            action_type=ActionType.SIMULATION_RUN.value,
            resource_type=ResourceType.SIMULATION.value,
            resource_id=station_id,
            details=details,
            ip_address=ip_address,
            session_id=session_id,
            result=result
        )
    
    def log_data_export(
        self,
        user_id: str,
        data_scope: Dict[str, Any],
        export_format: str,
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None,
        result: str = Result.SUCCESS.value
    ) -> UUID:
        """Log a data export event.
        
        Convenience method for logging data exports.
        
        Args:
            user_id: User identifier
            data_scope: Scope of exported data (time range, variables, etc.)
            export_format: Export format (CSV, PDF, etc.)
            ip_address: Client IP address
            session_id: Session identifier
            result: Result of export
            
        Returns:
            log_id of the created audit entry
            
        Requirements: 17.4
        """
        details = {
            "data_scope": data_scope,
            "export_format": export_format
        }
        
        return self.log_event(
            user_id=user_id,
            action_type=ActionType.DATA_EXPORT.value,
            resource_type=ResourceType.DATA.value,
            details=details,
            ip_address=ip_address,
            session_id=session_id,
            result=result
        )
    
    def query_logs(self, filters: AuditFilters) -> List[AuditEvent]:
        """Query audit logs with filtering.
        
        Supports filtering by:
        - user_id
        - action_type
        - resource_type
        - time range (start_time, end_time)
        - result
        
        Args:
            filters: AuditFilters object with query parameters
            
        Returns:
            List of AuditEvent objects matching the filters
            
        Raises:
            RuntimeError: If database operation fails
            
        Requirements: 17.6
        """
        engine = self._get_engine()
        
        # Build query with filters
        where_clauses = []
        params = {}
        
        if filters.user_id:
            where_clauses.append("user_id = :user_id")
            params["user_id"] = filters.user_id
        
        if filters.action_type:
            where_clauses.append("action_type = :action_type")
            params["action_type"] = filters.action_type
        
        if filters.resource_type:
            where_clauses.append("resource_type = :resource_type")
            params["resource_type"] = filters.resource_type
        
        if filters.start_time:
            where_clauses.append("timestamp >= :start_time")
            params["start_time"] = filters.start_time
        
        if filters.end_time:
            where_clauses.append("timestamp <= :end_time")
            params["end_time"] = filters.end_time
        
        if filters.result:
            where_clauses.append("result = :result")
            params["result"] = filters.result
        
        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        query_str = f"""
            SELECT log_id, timestamp, user_id, action_type, resource_type,
                   resource_id, details, ip_address, session_id, result
            FROM audit_logs
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT :limit
        """
        
        params["limit"] = filters.limit
        
        try:
            with engine.connect() as conn:
                result = conn.execute(text(query_str), params)
                
                events = []
                for row in result:
                    # Parse details JSON
                    details = json.loads(row[6]) if row[6] else {}
                    
                    event = AuditEvent(
                        log_id=UUID(row[0]),
                        timestamp=row[1],
                        user_id=row[2],
                        action_type=row[3],
                        resource_type=row[4],
                        resource_id=row[5],
                        details=details,
                        ip_address=row[7],
                        session_id=row[8],
                        result=row[9]
                    )
                    events.append(event)
                
                logger.info(f"Retrieved {len(events)} audit log entries")
                
                return events
                
        except SQLAlchemyError as e:
            logger.error(f"Database error querying audit logs: {e}")
            raise RuntimeError(f"Failed to query audit logs: {e}")
    
    def export_logs_csv(
        self,
        filters: AuditFilters,
        include_details: bool = True
    ) -> str:
        """Export audit logs to CSV format.
        
        Args:
            filters: AuditFilters object with query parameters
            include_details: Whether to include details column (default: True)
            
        Returns:
            CSV string with audit log data
            
        Raises:
            RuntimeError: If database operation fails
            
        Requirements: 17.6
        """
        # Query logs with filters
        events = self.query_logs(filters)
        
        # Create CSV in memory
        output = io.StringIO()
        
        # Define CSV columns
        fieldnames = [
            "log_id",
            "timestamp",
            "user_id",
            "action_type",
            "resource_type",
            "resource_id",
            "ip_address",
            "session_id",
            "result"
        ]
        
        if include_details:
            fieldnames.append("details")
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        # Write events
        for event in events:
            row = {
                "log_id": str(event.log_id),
                "timestamp": event.timestamp.isoformat(),
                "user_id": event.user_id or "",
                "action_type": event.action_type,
                "resource_type": event.resource_type or "",
                "resource_id": event.resource_id or "",
                "ip_address": event.ip_address or "",
                "session_id": event.session_id or "",
                "result": event.result
            }
            
            if include_details:
                row["details"] = json.dumps(event.details)
            
            writer.writerow(row)
        
        csv_content = output.getvalue()
        output.close()
        
        logger.info(f"Exported {len(events)} audit log entries to CSV")
        
        return csv_content
    
    def close(self):
        """Close database connection and dispose engine."""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            logger.info("Audit logger connection closed")
