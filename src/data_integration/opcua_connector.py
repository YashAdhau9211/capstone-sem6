"""OPC UA connector for SCADA/PLC systems."""

import asyncio
import logging
from datetime import datetime
from typing import Callable, List
from uuid import UUID, uuid4

import pandas as pd
from asyncua import Client, ua
from asyncua.common.subscription import Subscription as OPCUASubscription

from .isa95_connector import (
    ConnectionState,
    ISA95Connector,
    SystemConfig,
    TimeRange,
)


logger = logging.getLogger(__name__)


class OPCUAConnector(ISA95Connector):
    """OPC UA connector for SCADA and PLC systems."""
    
    HEARTBEAT_INTERVAL = 30  # seconds
    
    def __init__(self, config: SystemConfig):
        """Initialize OPC UA connector.
        
        Args:
            config: System configuration with OPC UA parameters
        """
        super().__init__(config)
        self._client: Optional[Client] = None
        self._opcua_subscription: Optional[OPCUASubscription] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._node_cache: dict[str, ua.NodeId] = {}
    
    async def _connect_impl(self) -> None:
        """Connect to OPC UA server with authentication."""
        url = f"opc.tcp://{self.config.host}:{self.config.port}"
        
        self._client = Client(url=url)
        
        # Set authentication if provided
        if self.config.username and self.config.password:
            self._client.set_user(self.config.username)
            self._client.set_password(self.config.password)
        
        # Set timeout
        self._client.session_timeout = self.config.timeout * 1000  # Convert to ms
        
        # Apply additional connection parameters
        if "security_policy" in self.config.connection_params:
            self._client.set_security_string(
                self.config.connection_params["security_policy"]
            )
        
        # Connect to server
        await self._client.connect()
        
        # Start heartbeat keepalive
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        logger.info(f"Connected to OPC UA server at {url}")
    
    async def _disconnect_impl(self) -> None:
        """Disconnect from OPC UA server."""
        # Stop heartbeat
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Delete subscription
        if self._opcua_subscription:
            try:
                await self._opcua_subscription.delete()
            except Exception as e:
                logger.warning(f"Error deleting OPC UA subscription: {e}")
            self._opcua_subscription = None
        
        # Disconnect client
        if self._client:
            try:
                await self._client.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting OPC UA client: {e}")
            self._client = None
        
        self._node_cache.clear()
    
    async def _read_data_impl(
        self, variables: List[str], time_range: TimeRange
    ) -> pd.DataFrame:
        """Read historical data from OPC UA server.
        
        Args:
            variables: List of variable node IDs or browse paths
            time_range: Time range for historical data
            
        Returns:
            DataFrame with columns: timestamp, variable, value, quality
        """
        if not self._client:
            raise ConnectionError("OPC UA client not connected")
        
        data_records = []
        
        for variable in variables:
            try:
                # Get node
                node = await self._get_node(variable)
                
                # Read historical data
                # Note: This requires the server to support historical access
                history = await node.read_raw_history(
                    starttime=time_range.start,
                    endtime=time_range.end
                )
                
                # Convert to records
                for data_value in history:
                    data_records.append({
                        "timestamp": data_value.SourceTimestamp,
                        "variable": variable,
                        "value": data_value.Value.Value,
                        "quality": self._map_quality(data_value.StatusCode)
                    })
                    
            except Exception as e:
                logger.error(f"Error reading historical data for {variable}: {e}")
                # Continue with other variables
        
        return pd.DataFrame(data_records)
    
    async def _subscribe_realtime_impl(
        self, variables: List[str], callback: Callable
    ) -> UUID:
        """Subscribe to real-time variable updates.
        
        Args:
            variables: List of variable node IDs or browse paths
            callback: Callback function for data updates
            
        Returns:
            Subscription ID
        """
        if not self._client:
            raise ConnectionError("OPC UA client not connected")
        
        subscription_id = uuid4()
        
        # Create OPC UA subscription if not exists
        if not self._opcua_subscription:
            self._opcua_subscription = await self._client.create_subscription(
                period=100,  # 100ms publishing interval
                handler=None
            )
        
        # Subscribe to each variable
        nodes = []
        for variable in variables:
            try:
                node = await self._get_node(variable)
                nodes.append(node)
            except Exception as e:
                logger.error(f"Error getting node for {variable}: {e}")
        
        # Create data change handler
        class DataChangeHandler:
            def __init__(self, variables: List[str], callback: Callable):
                self.variables = variables
                self.callback = callback
                self.var_map = {node: var for node, var in zip(nodes, variables)}
            
            def datachange_notification(self, node, val, data):
                """Handle data change notification."""
                try:
                    variable = self.var_map.get(node, str(node))
                    
                    record = {
                        "timestamp": data.monitored_item.Value.SourceTimestamp,
                        "variable": variable,
                        "value": val,
                        "quality": OPCUAConnector._map_quality_static(
                            data.monitored_item.Value.StatusCode
                        )
                    }
                    
                    df = pd.DataFrame([record])
                    
                    # Call user callback
                    asyncio.create_task(self._async_callback(df))
                    
                except Exception as e:
                    logger.error(f"Error in data change handler: {e}")
            
            async def _async_callback(self, df: pd.DataFrame):
                """Async wrapper for callback."""
                try:
                    if asyncio.iscoroutinefunction(self.callback):
                        await self.callback(df)
                    else:
                        self.callback(df)
                except Exception as e:
                    logger.error(f"Error in user callback: {e}")
        
        handler = DataChangeHandler(variables, callback)
        
        # Subscribe to nodes
        await self._opcua_subscription.subscribe_data_change(nodes, handler)
        
        logger.info(f"Subscribed to {len(nodes)} OPC UA variables")
        
        return subscription_id
    
    async def _get_node(self, variable: str):
        """Get OPC UA node by ID or browse path.
        
        Args:
            variable: Node ID string or browse path
            
        Returns:
            OPC UA Node object
        """
        if variable in self._node_cache:
            return self._node_cache[variable]
        
        if not self._client:
            raise ConnectionError("OPC UA client not connected")
        
        try:
            # Try as node ID first
            if variable.startswith("ns="):
                node = self._client.get_node(variable)
            else:
                # Try as browse path
                root = self._client.get_root_node()
                node = await root.get_child(variable.split("/"))
            
            # Cache the node
            self._node_cache[variable] = node
            return node
            
        except Exception as e:
            raise ValueError(f"Cannot find OPC UA node '{variable}': {e}")
    
    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeat to keep connection alive."""
        while True:
            try:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                
                if self._client and self._status.state == ConnectionState.CONNECTED:
                    # Read server status to verify connection
                    try:
                        await self._client.get_namespace_array()
                        logger.debug(f"Heartbeat OK for {self.config.system_id}")
                    except Exception as e:
                        logger.warning(
                            f"Heartbeat failed for {self.config.system_id}: {e}"
                        )
                        # Trigger reconnection
                        self._status.state = ConnectionState.ERROR
                        self._status.last_error = f"Heartbeat failed: {e}"
                        asyncio.create_task(self._retry_connection())
                        break
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
    
    @staticmethod
    def _map_quality(status_code: ua.StatusCode) -> str:
        """Map OPC UA status code to quality string.
        
        Args:
            status_code: OPC UA status code
            
        Returns:
            Quality string: "good", "uncertain", or "bad"
        """
        if status_code.is_good():
            return "good"
        elif status_code.is_uncertain():
            return "uncertain"
        else:
            return "bad"
    
    @staticmethod
    def _map_quality_static(status_code: ua.StatusCode) -> str:
        """Static version of quality mapping for use in nested classes."""
        if status_code.is_good():
            return "good"
        elif status_code.is_uncertain():
            return "uncertain"
        else:
            return "bad"
