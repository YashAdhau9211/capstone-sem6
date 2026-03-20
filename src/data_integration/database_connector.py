"""ODBC/JDBC connectors for ERP/MES systems."""

import asyncio
import logging
from datetime import datetime
from typing import Callable, List, Optional
from uuid import UUID, uuid4

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

from .isa95_connector import (
    ISA95Connector,
    SystemConfig,
    TimeRange,
)


logger = logging.getLogger(__name__)


class DatabaseConnector(ISA95Connector):
    """Database connector for ERP and MES systems using SQLAlchemy."""
    
    HEALTH_CHECK_INTERVAL = 60  # seconds
    HEALTH_CHECK_QUERY = "SELECT 1"
    
    def __init__(self, config: SystemConfig):
        """Initialize database connector.
        
        Args:
            config: System configuration with database parameters
        """
        super().__init__(config)
        self._engine: Optional[Engine] = None
        self._health_check_task: Optional[asyncio.Task] = None
    
    async def _connect_impl(self) -> None:
        """Connect to database with connection pooling."""
        # Build connection string
        db_type = self.config.connection_params.get("db_type", "postgresql")
        driver = self.config.connection_params.get("driver", None)
        database = self.config.connection_params.get("database", "")
        
        if driver:
            connection_string = (
                f"{db_type}+{driver}://{self.config.username}:{self.config.password}"
                f"@{self.config.host}:{self.config.port}/{database}"
            )
        else:
            connection_string = (
                f"{db_type}://{self.config.username}:{self.config.password}"
                f"@{self.config.host}:{self.config.port}/{database}"
            )
        
        # Add additional connection parameters
        extra_params = self.config.connection_params.get("extra_params", {})
        if extra_params:
            param_str = "&".join([f"{k}={v}" for k, v in extra_params.items()])
            connection_string += f"?{param_str}"
        
        # Create engine with connection pooling
        self._engine = create_engine(
            connection_string,
            poolclass=QueuePool,
            pool_size=self.config.pool_size,
            max_overflow=self.config.pool_size * 2,
            pool_timeout=self.config.timeout,
            pool_pre_ping=True,  # Verify connections before using
            echo=False
        )
        
        # Test connection
        await self._validate_connection()
        
        # Start health check loop
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        logger.info(
            f"Connected to {db_type} database at "
            f"{self.config.host}:{self.config.port}/{database}"
        )
    
    async def _disconnect_impl(self) -> None:
        """Disconnect from database."""
        # Stop health check
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Dispose engine and close all connections
        if self._engine:
            self._engine.dispose()
            self._engine = None
    
    async def _read_data_impl(
        self, variables: List[str], time_range: TimeRange
    ) -> pd.DataFrame:
        """Read historical data from database.
        
        Args:
            variables: List of column names or table.column references
            time_range: Time range for historical data
            
        Returns:
            DataFrame with columns: timestamp, variable, value, quality
        """
        if not self._engine:
            raise ConnectionError("Database engine not initialized")
        
        # Build query based on configuration
        table_name = self.config.connection_params.get("table_name", "sensor_data")
        timestamp_column = self.config.connection_params.get(
            "timestamp_column", "timestamp"
        )
        variable_column = self.config.connection_params.get(
            "variable_column", "variable"
        )
        value_column = self.config.connection_params.get("value_column", "value")
        quality_column = self.config.connection_params.get("quality_column", "quality")
        
        # Build WHERE clause for variables
        variable_list = ", ".join([f"'{v}'" for v in variables])
        
        query = text(f"""
            SELECT 
                {timestamp_column} as timestamp,
                {variable_column} as variable,
                {value_column} as value,
                {quality_column} as quality
            FROM {table_name}
            WHERE {variable_column} IN ({variable_list})
                AND {timestamp_column} >= :start_time
                AND {timestamp_column} <= :end_time
            ORDER BY {timestamp_column}
        """)
        
        # Execute query in thread pool (SQLAlchemy is sync)
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(
            None,
            self._execute_query,
            query,
            {"start_time": time_range.start, "end_time": time_range.end}
        )
        
        return df
    
    async def _subscribe_realtime_impl(
        self, variables: List[str], callback: Callable
    ) -> UUID:
        """Subscribe to real-time data updates via polling.
        
        Note: Database systems don't typically support push notifications,
        so this implementation uses polling.
        
        Args:
            variables: List of column names to monitor
            callback: Callback function for data updates
            
        Returns:
            Subscription ID
        """
        subscription_id = uuid4()
        
        # Start polling task
        poll_interval = self.config.connection_params.get("poll_interval", 5)  # seconds
        
        async def poll_loop():
            last_timestamp = datetime.utcnow()
            
            while subscription_id in self._subscriptions:
                try:
                    await asyncio.sleep(poll_interval)
                    
                    # Query for new data since last poll
                    current_time = datetime.utcnow()
                    time_range = TimeRange(start=last_timestamp, end=current_time)
                    
                    df = await self._read_data_impl(variables, time_range)
                    
                    if not df.empty:
                        # Call user callback
                        if asyncio.iscoroutinefunction(callback):
                            await callback(df)
                        else:
                            callback(df)
                    
                    last_timestamp = current_time
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in database polling loop: {e}")
        
        # Start polling task
        asyncio.create_task(poll_loop())
        
        logger.info(
            f"Started database polling for {len(variables)} variables "
            f"with {poll_interval}s interval"
        )
        
        return subscription_id
    
    def _execute_query(self, query: text, params: dict) -> pd.DataFrame:
        """Execute SQL query and return DataFrame.
        
        Args:
            query: SQLAlchemy text query
            params: Query parameters
            
        Returns:
            Query results as DataFrame
        """
        if not self._engine:
            raise ConnectionError("Database engine not initialized")
        
        with self._engine.connect() as conn:
            df = pd.read_sql(query, conn, params=params)
        
        return df
    
    async def _validate_connection(self) -> None:
        """Validate database connection with health check query."""
        if not self._engine:
            raise ConnectionError("Database engine not initialized")
        
        loop = asyncio.get_event_loop()
        
        try:
            await loop.run_in_executor(
                None,
                self._execute_health_check
            )
        except Exception as e:
            raise ConnectionError(f"Database health check failed: {e}")
    
    def _execute_health_check(self) -> None:
        """Execute health check query."""
        if not self._engine:
            raise ConnectionError("Database engine not initialized")
        
        with self._engine.connect() as conn:
            result = conn.execute(text(self.HEALTH_CHECK_QUERY))
            result.fetchone()
    
    async def _health_check_loop(self) -> None:
        """Periodic health check to verify connection."""
        while True:
            try:
                await asyncio.sleep(self.HEALTH_CHECK_INTERVAL)
                
                if self._engine:
                    try:
                        await self._validate_connection()
                        logger.debug(
                            f"Database health check OK for {self.config.system_id}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Database health check failed for "
                            f"{self.config.system_id}: {e}"
                        )
                        # Trigger reconnection
                        self._status.last_error = f"Health check failed: {e}"
                        asyncio.create_task(self._retry_connection())
                        break
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")


class ODBCConnector(DatabaseConnector):
    """ODBC connector for ERP/MES systems."""
    
    def __init__(self, config: SystemConfig):
        """Initialize ODBC connector.
        
        Args:
            config: System configuration with ODBC parameters
        """
        # Set default ODBC driver if not specified
        if "driver" not in config.connection_params:
            config.connection_params["driver"] = "pyodbc"
        
        super().__init__(config)


class JDBCConnector(DatabaseConnector):
    """JDBC connector for ERP/MES systems (via JayDeBeApi)."""
    
    def __init__(self, config: SystemConfig):
        """Initialize JDBC connector.
        
        Args:
            config: System configuration with JDBC parameters
        """
        # Note: JDBC support requires JayDeBeApi and JVM
        # This is a placeholder for JDBC-specific configuration
        
        if "driver" not in config.connection_params:
            # Default to PostgreSQL JDBC driver
            config.connection_params["driver"] = "postgresql"
        
        super().__init__(config)
