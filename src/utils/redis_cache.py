"""Redis caching layer for the Causal AI Manufacturing Platform.

This module provides a Redis client wrapper with support for:
- Connection status caching (100ms TTL)
- DAG and model parameter caching (5-minute TTL)
- Query result caching (configurable TTL)
- Session management
- Error handling and fallback behavior
"""

import json
import logging
from typing import Any, Optional, Dict
from datetime import timedelta

import redis
from redis.exceptions import RedisError, ConnectionError, TimeoutError

logger = logging.getLogger(__name__)


class RedisCacheManager:
    """Redis cache manager for the platform.
    
    Provides caching functionality with different TTL configurations for:
    - Connection status (100ms TTL)
    - DAG and model parameters (5-minute TTL)
    - Query results (configurable TTL)
    - Session management
    """

    # TTL constants (in seconds)
    CONNECTION_STATUS_TTL = 1  # 1 second (Redis minimum for setex)
    DAG_MODEL_TTL = 300  # 5 minutes
    DEFAULT_QUERY_TTL = 300  # 5 minutes (default)
    SESSION_TTL = 1800  # 30 minutes

    # Key prefixes for different cache types
    PREFIX_CONNECTION = "conn_status:"
    PREFIX_DAG = "dag:"
    PREFIX_MODEL = "model:"
    PREFIX_QUERY = "query:"
    PREFIX_SESSION = "session:"

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0,
        decode_responses: bool = True,
    ):
        """Initialize Redis cache manager.
        
        Args:
            host: Redis server host
            port: Redis server port
            db: Redis database number
            password: Redis password (optional)
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Socket connect timeout in seconds
            decode_responses: Whether to decode responses to strings
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.decode_responses = decode_responses
        
        self._client: Optional[redis.Redis] = None
        self._is_available = False
        
        self._connect()

    def _connect(self) -> None:
        """Establish connection to Redis server."""
        try:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                socket_timeout=self.socket_timeout,
                socket_connect_timeout=self.socket_connect_timeout,
                decode_responses=self.decode_responses,
            )
            # Test connection
            self._client.ping()
            self._is_available = True
            logger.info(f"Connected to Redis at {self.host}:{self.port}")
        except (ConnectionError, TimeoutError, RedisError) as e:
            self._is_available = False
            logger.warning(f"Failed to connect to Redis: {e}. Operating without cache.")

    @property
    def is_available(self) -> bool:
        """Check if Redis is available."""
        return self._is_available and self._client is not None

    def _handle_error(self, operation: str, error: Exception) -> None:
        """Handle Redis errors with logging.
        
        Args:
            operation: Name of the operation that failed
            error: The exception that occurred
        """
        logger.warning(f"Redis {operation} failed: {error}. Continuing without cache.")
        # Mark as unavailable if connection error
        if isinstance(error, (ConnectionError, TimeoutError)):
            self._is_available = False

    # Connection Status Caching (100ms TTL)
    
    def set_connection_status(
        self, system_id: str, status: Dict[str, Any]
    ) -> bool:
        """Cache connection status for an ISA-95 system.
        
        Args:
            system_id: Unique identifier for the system
            status: Connection status dictionary
            
        Returns:
            True if cached successfully, False otherwise
        """
        if not self.is_available:
            return False
            
        try:
            key = f"{self.PREFIX_CONNECTION}{system_id}"
            value = json.dumps(status)
            self._client.setex(key, self.CONNECTION_STATUS_TTL, value)
            return True
        except RedisError as e:
            self._handle_error("set_connection_status", e)
            return False

    def get_connection_status(self, system_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached connection status.
        
        Args:
            system_id: Unique identifier for the system
            
        Returns:
            Connection status dictionary if cached, None otherwise
        """
        if not self.is_available:
            return None
            
        try:
            key = f"{self.PREFIX_CONNECTION}{system_id}"
            value = self._client.get(key)
            if value:
                return json.loads(value)
            return None
        except RedisError as e:
            self._handle_error("get_connection_status", e)
            return None

    # DAG Caching (5-minute TTL)
    
    def set_dag(self, station_id: str, dag_data: Dict[str, Any]) -> bool:
        """Cache DAG data for a station.
        
        Args:
            station_id: Station identifier
            dag_data: DAG data dictionary
            
        Returns:
            True if cached successfully, False otherwise
        """
        if not self.is_available:
            return False
            
        try:
            key = f"{self.PREFIX_DAG}{station_id}"
            value = json.dumps(dag_data)
            self._client.setex(key, self.DAG_MODEL_TTL, value)
            return True
        except RedisError as e:
            self._handle_error("set_dag", e)
            return False

    def get_dag(self, station_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached DAG data.
        
        Args:
            station_id: Station identifier
            
        Returns:
            DAG data dictionary if cached, None otherwise
        """
        if not self.is_available:
            return None
            
        try:
            key = f"{self.PREFIX_DAG}{station_id}"
            value = self._client.get(key)
            if value:
                return json.loads(value)
            return None
        except RedisError as e:
            self._handle_error("get_dag", e)
            return None

    def invalidate_dag(self, station_id: str) -> bool:
        """Invalidate cached DAG data.
        
        Args:
            station_id: Station identifier
            
        Returns:
            True if invalidated successfully, False otherwise
        """
        if not self.is_available:
            return False
            
        try:
            key = f"{self.PREFIX_DAG}{station_id}"
            self._client.delete(key)
            return True
        except RedisError as e:
            self._handle_error("invalidate_dag", e)
            return False

    # Model Parameter Caching (5-minute TTL)
    
    def set_model_params(
        self, model_id: str, params: Dict[str, Any]
    ) -> bool:
        """Cache model parameters.
        
        Args:
            model_id: Model identifier
            params: Model parameters dictionary
            
        Returns:
            True if cached successfully, False otherwise
        """
        if not self.is_available:
            return False
            
        try:
            key = f"{self.PREFIX_MODEL}{model_id}"
            value = json.dumps(params)
            self._client.setex(key, self.DAG_MODEL_TTL, value)
            return True
        except RedisError as e:
            self._handle_error("set_model_params", e)
            return False

    def get_model_params(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached model parameters.
        
        Args:
            model_id: Model identifier
            
        Returns:
            Model parameters dictionary if cached, None otherwise
        """
        if not self.is_available:
            return None
            
        try:
            key = f"{self.PREFIX_MODEL}{model_id}"
            value = self._client.get(key)
            if value:
                return json.loads(value)
            return None
        except RedisError as e:
            self._handle_error("get_model_params", e)
            return None

    def invalidate_model_params(self, model_id: str) -> bool:
        """Invalidate cached model parameters.
        
        Args:
            model_id: Model identifier
            
        Returns:
            True if invalidated successfully, False otherwise
        """
        if not self.is_available:
            return False
            
        try:
            key = f"{self.PREFIX_MODEL}{model_id}"
            self._client.delete(key)
            return True
        except RedisError as e:
            self._handle_error("invalidate_model_params", e)
            return False

    # Query Result Caching (configurable TTL)
    
    def set_query_result(
        self,
        query_key: str,
        result: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """Cache query result.
        
        Args:
            query_key: Unique key for the query
            result: Query result (will be JSON serialized)
            ttl: Time-to-live in seconds (default: 5 minutes)
            
        Returns:
            True if cached successfully, False otherwise
        """
        if not self.is_available:
            return False
            
        try:
            key = f"{self.PREFIX_QUERY}{query_key}"
            value = json.dumps(result)
            ttl = ttl or self.DEFAULT_QUERY_TTL
            self._client.setex(key, ttl, value)
            return True
        except RedisError as e:
            self._handle_error("set_query_result", e)
            return False

    def get_query_result(self, query_key: str) -> Optional[Any]:
        """Retrieve cached query result.
        
        Args:
            query_key: Unique key for the query
            
        Returns:
            Query result if cached, None otherwise
        """
        if not self.is_available:
            return None
            
        try:
            key = f"{self.PREFIX_QUERY}{query_key}"
            value = self._client.get(key)
            if value:
                return json.loads(value)
            return None
        except RedisError as e:
            self._handle_error("get_query_result", e)
            return None

    def invalidate_query_result(self, query_key: str) -> bool:
        """Invalidate cached query result.
        
        Args:
            query_key: Unique key for the query
            
        Returns:
            True if invalidated successfully, False otherwise
        """
        if not self.is_available:
            return False
            
        try:
            key = f"{self.PREFIX_QUERY}{query_key}"
            self._client.delete(key)
            return True
        except RedisError as e:
            self._handle_error("invalidate_query_result", e)
            return False

    # Session Management
    
    def set_session(
        self, session_id: str, session_data: Dict[str, Any], ttl: Optional[int] = None
    ) -> bool:
        """Store session data.
        
        Args:
            session_id: Session identifier
            session_data: Session data dictionary
            ttl: Time-to-live in seconds (default: 30 minutes)
            
        Returns:
            True if stored successfully, False otherwise
        """
        if not self.is_available:
            return False
            
        try:
            key = f"{self.PREFIX_SESSION}{session_id}"
            value = json.dumps(session_data)
            ttl = ttl or self.SESSION_TTL
            self._client.setex(key, ttl, value)
            return True
        except RedisError as e:
            self._handle_error("set_session", e)
            return False

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session data.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data dictionary if exists, None otherwise
        """
        if not self.is_available:
            return None
            
        try:
            key = f"{self.PREFIX_SESSION}{session_id}"
            value = self._client.get(key)
            if value:
                return json.loads(value)
            return None
        except RedisError as e:
            self._handle_error("get_session", e)
            return None

    def delete_session(self, session_id: str) -> bool:
        """Delete session data.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if deleted successfully, False otherwise
        """
        if not self.is_available:
            return False
            
        try:
            key = f"{self.PREFIX_SESSION}{session_id}"
            self._client.delete(key)
            return True
        except RedisError as e:
            self._handle_error("delete_session", e)
            return False

    def refresh_session(self, session_id: str, ttl: Optional[int] = None) -> bool:
        """Refresh session TTL.
        
        Args:
            session_id: Session identifier
            ttl: New time-to-live in seconds (default: 30 minutes)
            
        Returns:
            True if refreshed successfully, False otherwise
        """
        if not self.is_available:
            return False
            
        try:
            key = f"{self.PREFIX_SESSION}{session_id}"
            ttl = ttl or self.SESSION_TTL
            self._client.expire(key, ttl)
            return True
        except RedisError as e:
            self._handle_error("refresh_session", e)
            return False

    # Utility Methods
    
    def clear_all(self) -> bool:
        """Clear all cached data (use with caution).
        
        Returns:
            True if cleared successfully, False otherwise
        """
        if not self.is_available:
            return False
            
        try:
            self._client.flushdb()
            logger.info("Cleared all Redis cache data")
            return True
        except RedisError as e:
            self._handle_error("clear_all", e)
            return False

    def get_stats(self) -> Optional[Dict[str, Any]]:
        """Get Redis server statistics.
        
        Returns:
            Statistics dictionary if available, None otherwise
        """
        if not self.is_available:
            return None
            
        try:
            info = self._client.info()
            return {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "0"),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
            }
        except RedisError as e:
            self._handle_error("get_stats", e)
            return None

    def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            try:
                self._client.close()
                logger.info("Closed Redis connection")
            except RedisError as e:
                logger.warning(f"Error closing Redis connection: {e}")
            finally:
                self._is_available = False
                self._client = None
