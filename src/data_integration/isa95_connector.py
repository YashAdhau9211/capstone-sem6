"""ISA-95 connector base class and interface."""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4

import pandas as pd


logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection state enumeration."""
    
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


@dataclass
class ConnectionStatus:
    """Connection status information."""
    
    system_id: str
    state: ConnectionState
    last_connected: Optional[datetime] = None
    last_error: Optional[str] = None
    error_timestamp: Optional[datetime] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemConfig:
    """Configuration for ISA-95 system connection."""
    
    system_id: str
    system_type: str  # "ERP", "MES", "SCADA", "PLC", "IIoT"
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    connection_params: Dict[str, Any] = field(default_factory=dict)
    pool_size: int = 10
    timeout: int = 30


@dataclass
class TimeRange:
    """Time range for data queries."""
    
    start: datetime
    end: datetime


@dataclass
class Subscription:
    """Real-time data subscription."""
    
    subscription_id: UUID
    variables: List[str]
    callback: Callable
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


class ConnectionPool:
    """Connection pool for managing multiple connections."""
    
    def __init__(self, max_size: int = 10):
        """Initialize connection pool.
        
        Args:
            max_size: Maximum number of connections in pool
        """
        self.max_size = max_size
        self._pool: List[Any] = []
        self._in_use: List[Any] = []
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> Any:
        """Acquire a connection from the pool."""
        async with self._lock:
            if self._pool:
                conn = self._pool.pop()
                self._in_use.append(conn)
                return conn
            elif len(self._in_use) < self.max_size:
                # Pool will be populated by concrete implementations
                return None
            else:
                # Wait for a connection to be released
                raise RuntimeError("Connection pool exhausted")
    
    async def release(self, conn: Any) -> None:
        """Release a connection back to the pool."""
        async with self._lock:
            if conn in self._in_use:
                self._in_use.remove(conn)
                self._pool.append(conn)
    
    async def add_connection(self, conn: Any) -> None:
        """Add a new connection to the pool."""
        async with self._lock:
            if len(self._pool) + len(self._in_use) < self.max_size:
                self._pool.append(conn)
    
    async def close_all(self) -> None:
        """Close all connections in the pool."""
        async with self._lock:
            all_conns = self._pool + self._in_use
            self._pool.clear()
            self._in_use.clear()
            return all_conns


class ISA95Connector(ABC):
    """Abstract base class for ISA-95 system connectors."""
    
    # Exponential backoff retry intervals (seconds)
    RETRY_INTERVALS = [1, 2, 4, 8, 16, 32, 64, 128, 256, 300]
    
    # Connection status cache TTL (seconds)
    STATUS_CACHE_TTL = 0.1  # 100ms
    
    def __init__(self, config: SystemConfig):
        """Initialize ISA-95 connector.
        
        Args:
            config: System configuration
        """
        self.config = config
        self._status = ConnectionStatus(
            system_id=config.system_id,
            state=ConnectionState.DISCONNECTED
        )
        self._status_cache_time: Optional[float] = None
        self._pool = ConnectionPool(max_size=config.pool_size)
        self._subscriptions: Dict[UUID, Subscription] = {}
        self._retry_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
    
    @abstractmethod
    async def _connect_impl(self) -> None:
        """Implementation-specific connection logic.
        
        Raises:
            ConnectionError: If connection fails
        """
        pass
    
    @abstractmethod
    async def _disconnect_impl(self) -> None:
        """Implementation-specific disconnection logic."""
        pass
    
    @abstractmethod
    async def _read_data_impl(
        self, variables: List[str], time_range: TimeRange
    ) -> pd.DataFrame:
        """Implementation-specific data reading logic.
        
        Args:
            variables: List of variable names to read
            time_range: Time range for historical data
            
        Returns:
            DataFrame with columns: timestamp, variable, value, quality
        """
        pass
    
    @abstractmethod
    async def _subscribe_realtime_impl(
        self, variables: List[str], callback: Callable
    ) -> UUID:
        """Implementation-specific real-time subscription logic.
        
        Args:
            variables: List of variable names to subscribe to
            callback: Callback function for data updates
            
        Returns:
            Subscription ID
        """
        pass
    
    async def connect(self) -> ConnectionStatus:
        """Connect to the ISA-95 system.
        
        Returns:
            Connection status
        """
        async with self._lock:
            try:
                self._status.state = ConnectionState.CONNECTING
                logger.info(f"Connecting to {self.config.system_id}...")
                
                await self._connect_impl()
                
                self._status.state = ConnectionState.CONNECTED
                self._status.last_connected = datetime.utcnow()
                self._status.retry_count = 0
                self._status.last_error = None
                self._status_cache_time = time.time()
                
                logger.info(f"Successfully connected to {self.config.system_id}")
                
            except Exception as e:
                error_msg = f"Connection failed: {str(e)}"
                logger.error(f"{self.config.system_id}: {error_msg}")
                
                self._status.state = ConnectionState.ERROR
                self._status.last_error = error_msg
                self._status.error_timestamp = datetime.utcnow()
                
                # Log connection failure
                self._log_connection_failure(error_msg)
                
                # Start retry with exponential backoff
                if not self._retry_task or self._retry_task.done():
                    self._retry_task = asyncio.create_task(self._retry_connection())
                
                raise ConnectionError(error_msg)
            
            return self._status
    
    async def disconnect(self) -> None:
        """Disconnect from the ISA-95 system."""
        async with self._lock:
            try:
                logger.info(f"Disconnecting from {self.config.system_id}...")
                
                # Cancel retry task if running
                if self._retry_task and not self._retry_task.done():
                    self._retry_task.cancel()
                
                # Close all subscriptions
                for sub in self._subscriptions.values():
                    sub.active = False
                self._subscriptions.clear()
                
                # Close all connections in pool
                await self._pool.close_all()
                
                await self._disconnect_impl()
                
                self._status.state = ConnectionState.DISCONNECTED
                self._status_cache_time = time.time()
                
                logger.info(f"Disconnected from {self.config.system_id}")
                
            except Exception as e:
                logger.error(f"Error during disconnect from {self.config.system_id}: {e}")
    
    def get_connection_status(self) -> ConnectionStatus:
        """Get current connection status with caching.
        
        Returns:
            Connection status (cached for 100ms)
        """
        current_time = time.time()
        
        # Return cached status if within TTL
        if (
            self._status_cache_time is not None
            and current_time - self._status_cache_time < self.STATUS_CACHE_TTL
        ):
            return self._status
        
        # Update cache timestamp
        self._status_cache_time = current_time
        return self._status
    
    async def read_data(
        self, variables: List[str], time_range: TimeRange
    ) -> pd.DataFrame:
        """Read historical data from the system.
        
        Args:
            variables: List of variable names to read
            time_range: Time range for historical data
            
        Returns:
            DataFrame with columns: timestamp, variable, value, quality
            
        Raises:
            ConnectionError: If not connected
        """
        if self._status.state != ConnectionState.CONNECTED:
            raise ConnectionError(
                f"Cannot read data: {self.config.system_id} is not connected"
            )
        
        try:
            return await self._read_data_impl(variables, time_range)
        except Exception as e:
            logger.error(f"Error reading data from {self.config.system_id}: {e}")
            raise
    
    async def subscribe_realtime(
        self, variables: List[str], callback: Callable
    ) -> Subscription:
        """Subscribe to real-time data updates.
        
        Args:
            variables: List of variable names to subscribe to
            callback: Callback function(data: pd.DataFrame) for updates
            
        Returns:
            Subscription object
            
        Raises:
            ConnectionError: If not connected
        """
        if self._status.state != ConnectionState.CONNECTED:
            raise ConnectionError(
                f"Cannot subscribe: {self.config.system_id} is not connected"
            )
        
        try:
            subscription_id = await self._subscribe_realtime_impl(variables, callback)
            
            subscription = Subscription(
                subscription_id=subscription_id,
                variables=variables,
                callback=callback,
                active=True
            )
            
            self._subscriptions[subscription_id] = subscription
            
            logger.info(
                f"Created subscription {subscription_id} for "
                f"{len(variables)} variables on {self.config.system_id}"
            )
            
            return subscription
            
        except Exception as e:
            logger.error(f"Error creating subscription on {self.config.system_id}: {e}")
            raise
    
    async def unsubscribe(self, subscription_id: UUID) -> None:
        """Unsubscribe from real-time data updates.
        
        Args:
            subscription_id: Subscription ID to cancel
        """
        if subscription_id in self._subscriptions:
            self._subscriptions[subscription_id].active = False
            del self._subscriptions[subscription_id]
            logger.info(f"Cancelled subscription {subscription_id}")
    
    async def _retry_connection(self) -> None:
        """Retry connection with exponential backoff."""
        retry_count = 0
        
        while retry_count < len(self.RETRY_INTERVALS):
            interval = self.RETRY_INTERVALS[retry_count]
            
            logger.info(
                f"Retrying connection to {self.config.system_id} "
                f"in {interval} seconds (attempt {retry_count + 1})"
            )
            
            self._status.state = ConnectionState.RECONNECTING
            self._status.retry_count = retry_count + 1
            
            await asyncio.sleep(interval)
            
            try:
                await self.connect()
                logger.info(f"Reconnection successful for {self.config.system_id}")
                return
            except Exception as e:
                logger.warning(
                    f"Reconnection attempt {retry_count + 1} failed "
                    f"for {self.config.system_id}: {e}"
                )
                retry_count += 1
        
        # Max retries reached
        logger.error(
            f"Max retry attempts reached for {self.config.system_id}. "
            f"Connection remains in error state."
        )
        self._status.state = ConnectionState.ERROR
    
    def _log_connection_failure(self, error_msg: str) -> None:
        """Log connection failure with timestamp and system details.
        
        Args:
            error_msg: Error message
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "system_id": self.config.system_id,
            "system_type": self.config.system_type,
            "host": self.config.host,
            "port": self.config.port,
            "error": error_msg,
            "retry_count": self._status.retry_count
        }
        
        # Log as structured data
        logger.error(f"Connection failure: {log_entry}")
