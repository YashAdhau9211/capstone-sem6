"""Connection failure logging and monitoring for ISA-95 connectors."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from .isa95_connector import ConnectionState, ConnectionStatus, ISA95Connector


logger = logging.getLogger(__name__)


class EventType(Enum):
    """Connection event types."""
    
    CONNECTION_ESTABLISHED = "connection_established"
    CONNECTION_FAILED = "connection_failed"
    CONNECTION_LOST = "connection_lost"
    RECONNECTION_ATTEMPT = "reconnection_attempt"
    RECONNECTION_SUCCESS = "reconnection_success"
    RECONNECTION_FAILED = "reconnection_failed"
    HEALTH_CHECK_FAILED = "health_check_failed"
    GRACEFUL_DEGRADATION = "graceful_degradation"


class Severity(Enum):
    """Event severity levels."""
    
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ConnectionEvent:
    """Connection event record."""
    
    event_id: UUID
    timestamp: datetime
    event_type: EventType
    severity: Severity
    system_id: str
    system_type: str
    host: str
    port: int
    error_details: Optional[str] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for logging."""
        return {
            "event_id": str(self.event_id),
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "system_id": self.system_id,
            "system_type": self.system_type,
            "host": self.host,
            "port": self.port,
            "error_details": self.error_details,
            "retry_count": self.retry_count,
            "metadata": self.metadata
        }


@dataclass
class SystemHealth:
    """System health status."""
    
    system_id: str
    is_healthy: bool
    connection_state: ConnectionState
    uptime_percentage: float
    total_failures: int
    last_failure: Optional[datetime] = None
    last_success: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConnectionMonitor:
    """Monitor and log connection events for ISA-95 connectors."""
    
    def __init__(self):
        """Initialize connection monitor."""
        self._connectors: Dict[str, ISA95Connector] = {}
        self._event_history: List[ConnectionEvent] = []
        self._max_history = 10000  # Keep last 10k events
        self._health_stats: Dict[str, Dict[str, Any]] = {}
        self._monitoring_task: Optional[asyncio.Task] = None
        self._monitoring_interval = 60  # seconds
        self._event_callbacks: List[callable] = []
    
    def register_connector(self, connector: ISA95Connector) -> None:
        """Register a connector for monitoring.
        
        Args:
            connector: ISA-95 connector instance
        """
        system_id = connector.config.system_id
        
        if system_id in self._connectors:
            logger.warning(f"Connector {system_id} already registered")
            return
        
        self._connectors[system_id] = connector
        
        # Initialize health stats
        self._health_stats[system_id] = {
            "total_connections": 0,
            "total_failures": 0,
            "total_reconnections": 0,
            "first_seen": datetime.utcnow(),
            "last_event": None,
            "uptime_start": None,
            "total_uptime_seconds": 0
        }
        
        logger.info(f"Registered connector for monitoring: {system_id}")
    
    def unregister_connector(self, system_id: str) -> None:
        """Unregister a connector from monitoring.
        
        Args:
            system_id: System identifier
        """
        if system_id in self._connectors:
            del self._connectors[system_id]
            logger.info(f"Unregistered connector: {system_id}")
    
    def log_event(
        self,
        connector: ISA95Connector,
        event_type: EventType,
        severity: Severity,
        error_details: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConnectionEvent:
        """Log a connection event.
        
        Args:
            connector: ISA-95 connector
            event_type: Type of event
            severity: Event severity
            error_details: Optional error details
            metadata: Optional additional metadata
            
        Returns:
            Created event record
        """
        event = ConnectionEvent(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            event_type=event_type,
            severity=severity,
            system_id=connector.config.system_id,
            system_type=connector.config.system_type,
            host=connector.config.host,
            port=connector.config.port,
            error_details=error_details,
            retry_count=connector._status.retry_count,
            metadata=metadata or {}
        )
        
        # Add to history
        self._event_history.append(event)
        
        # Trim history if needed
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]
        
        # Update health stats
        self._update_health_stats(connector, event)
        
        # Log to standard logger
        log_msg = (
            f"[{event.system_id}] {event.event_type.value}: "
            f"{error_details or 'OK'}"
        )
        
        if severity == Severity.INFO:
            logger.info(log_msg)
        elif severity == Severity.WARNING:
            logger.warning(log_msg)
        elif severity == Severity.ERROR:
            logger.error(log_msg)
        elif severity == Severity.CRITICAL:
            logger.critical(log_msg)
        
        # Emit to registered callbacks
        self._emit_event(event)
        
        return event
    
    def log_connection_failure(
        self,
        connector: ISA95Connector,
        error_msg: str,
        is_reconnection: bool = False
    ) -> None:
        """Log connection failure with timestamp and system details.
        
        Args:
            connector: ISA-95 connector
            error_msg: Error message
            is_reconnection: Whether this is a reconnection attempt
        """
        event_type = (
            EventType.RECONNECTION_FAILED if is_reconnection
            else EventType.CONNECTION_FAILED
        )
        
        self.log_event(
            connector=connector,
            event_type=event_type,
            severity=Severity.ERROR,
            error_details=error_msg,
            metadata={
                "connection_state": connector._status.state.value,
                "retry_count": connector._status.retry_count
            }
        )
    
    def log_connection_success(
        self,
        connector: ISA95Connector,
        is_reconnection: bool = False
    ) -> None:
        """Log successful connection.
        
        Args:
            connector: ISA-95 connector
            is_reconnection: Whether this is a reconnection
        """
        event_type = (
            EventType.RECONNECTION_SUCCESS if is_reconnection
            else EventType.CONNECTION_ESTABLISHED
        )
        
        self.log_event(
            connector=connector,
            event_type=event_type,
            severity=Severity.INFO,
            metadata={
                "connection_state": connector._status.state.value
            }
        )
    
    def log_graceful_degradation(
        self,
        failed_systems: List[str],
        operational_systems: List[str]
    ) -> None:
        """Log graceful degradation when some systems fail.
        
        Args:
            failed_systems: List of failed system IDs
            operational_systems: List of operational system IDs
        """
        for system_id in failed_systems:
            if system_id in self._connectors:
                connector = self._connectors[system_id]
                
                self.log_event(
                    connector=connector,
                    event_type=EventType.GRACEFUL_DEGRADATION,
                    severity=Severity.WARNING,
                    error_details=f"System degraded. {len(operational_systems)} "
                                  f"of {len(failed_systems) + len(operational_systems)} "
                                  f"systems operational",
                    metadata={
                        "failed_systems": failed_systems,
                        "operational_systems": operational_systems
                    }
                )
    
    def get_system_health(self, system_id: str) -> Optional[SystemHealth]:
        """Get health status for a system.
        
        Args:
            system_id: System identifier
            
        Returns:
            System health status or None if not found
        """
        if system_id not in self._connectors:
            return None
        
        connector = self._connectors[system_id]
        stats = self._health_stats.get(system_id, {})
        
        # Calculate uptime percentage
        total_time = (
            datetime.utcnow() - stats.get("first_seen", datetime.utcnow())
        ).total_seconds()
        
        uptime_seconds = stats.get("total_uptime_seconds", 0)
        
        # Add current uptime if connected
        if connector._status.state == ConnectionState.CONNECTED:
            if stats.get("uptime_start"):
                uptime_seconds += (
                    datetime.utcnow() - stats["uptime_start"]
                ).total_seconds()
        
        uptime_percentage = (uptime_seconds / total_time * 100) if total_time > 0 else 0
        
        return SystemHealth(
            system_id=system_id,
            is_healthy=connector._status.state == ConnectionState.CONNECTED,
            connection_state=connector._status.state,
            uptime_percentage=uptime_percentage,
            total_failures=stats.get("total_failures", 0),
            last_failure=stats.get("last_failure"),
            last_success=stats.get("last_success"),
            metadata={
                "total_connections": stats.get("total_connections", 0),
                "total_reconnections": stats.get("total_reconnections", 0)
            }
        )
    
    def get_all_health_status(self) -> List[SystemHealth]:
        """Get health status for all registered systems.
        
        Returns:
            List of system health statuses
        """
        return [
            self.get_system_health(system_id)
            for system_id in self._connectors.keys()
        ]
    
    def get_event_history(
        self,
        system_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        severity: Optional[Severity] = None,
        limit: int = 100
    ) -> List[ConnectionEvent]:
        """Get event history with optional filters.
        
        Args:
            system_id: Filter by system ID
            event_type: Filter by event type
            severity: Filter by severity
            limit: Maximum number of events to return
            
        Returns:
            List of connection events
        """
        filtered_events = self._event_history
        
        if system_id:
            filtered_events = [e for e in filtered_events if e.system_id == system_id]
        
        if event_type:
            filtered_events = [e for e in filtered_events if e.event_type == event_type]
        
        if severity:
            filtered_events = [e for e in filtered_events if e.severity == severity]
        
        # Return most recent events
        return filtered_events[-limit:]
    
    def register_event_callback(self, callback: callable) -> None:
        """Register callback for connection events.
        
        Args:
            callback: Callback function(event: ConnectionEvent)
        """
        self._event_callbacks.append(callback)
    
    def start_monitoring(self, interval: int = 60) -> None:
        """Start periodic monitoring of all connectors.
        
        Args:
            interval: Monitoring interval in seconds
        """
        if self._monitoring_task and not self._monitoring_task.done():
            logger.warning("Monitoring already started")
            return
        
        self._monitoring_interval = interval
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info(f"Started connection monitoring (interval: {interval}s)")
    
    def stop_monitoring(self) -> None:
        """Stop periodic monitoring."""
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            logger.info("Stopped connection monitoring")
    
    async def _monitoring_loop(self) -> None:
        """Periodic monitoring loop."""
        while True:
            try:
                await asyncio.sleep(self._monitoring_interval)
                
                # Check status of all connectors
                for system_id, connector in self._connectors.items():
                    status = connector.get_connection_status()
                    
                    # Log if in error state
                    if status.state == ConnectionState.ERROR:
                        self.log_event(
                            connector=connector,
                            event_type=EventType.HEALTH_CHECK_FAILED,
                            severity=Severity.WARNING,
                            error_details=status.last_error
                        )
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
    
    def _update_health_stats(
        self, connector: ISA95Connector, event: ConnectionEvent
    ) -> None:
        """Update health statistics for a connector.
        
        Args:
            connector: ISA-95 connector
            event: Connection event
        """
        system_id = connector.config.system_id
        stats = self._health_stats.get(system_id, {})
        
        stats["last_event"] = event.timestamp
        
        if event.event_type == EventType.CONNECTION_ESTABLISHED:
            stats["total_connections"] = stats.get("total_connections", 0) + 1
            stats["last_success"] = event.timestamp
            stats["uptime_start"] = event.timestamp
            
        elif event.event_type == EventType.RECONNECTION_SUCCESS:
            stats["total_reconnections"] = stats.get("total_reconnections", 0) + 1
            stats["last_success"] = event.timestamp
            stats["uptime_start"] = event.timestamp
            
        elif event.event_type in (
            EventType.CONNECTION_FAILED,
            EventType.CONNECTION_LOST,
            EventType.RECONNECTION_FAILED
        ):
            stats["total_failures"] = stats.get("total_failures", 0) + 1
            stats["last_failure"] = event.timestamp
            
            # Update uptime
            if stats.get("uptime_start"):
                uptime_seconds = (event.timestamp - stats["uptime_start"]).total_seconds()
                stats["total_uptime_seconds"] = (
                    stats.get("total_uptime_seconds", 0) + uptime_seconds
                )
                stats["uptime_start"] = None
        
        self._health_stats[system_id] = stats
    
    def _emit_event(self, event: ConnectionEvent) -> None:
        """Emit event to registered callbacks.
        
        Args:
            event: Connection event
        """
        for callback in self._event_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(event))
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Error in event callback: {e}")


# Global monitor instance
_global_monitor: Optional[ConnectionMonitor] = None


def get_monitor() -> ConnectionMonitor:
    """Get global connection monitor instance.
    
    Returns:
        Global ConnectionMonitor instance
    """
    global _global_monitor
    
    if _global_monitor is None:
        _global_monitor = ConnectionMonitor()
    
    return _global_monitor
