"""MQTT connector for IIoT sensors."""

import asyncio
import json
import logging
from collections import deque
from datetime import datetime
from typing import Callable, Dict, List, Optional
from uuid import UUID, uuid4

import pandas as pd
import paho.mqtt.client as mqtt

from .isa95_connector import (
    ConnectionState,
    ISA95Connector,
    SystemConfig,
    TimeRange,
)


logger = logging.getLogger(__name__)


class MQTTConnector(ISA95Connector):
    """MQTT connector for IIoT sensor networks."""
    
    # QoS levels
    QOS_AT_MOST_ONCE = 0
    QOS_AT_LEAST_ONCE = 1
    QOS_EXACTLY_ONCE = 2
    
    def __init__(self, config: SystemConfig):
        """Initialize MQTT connector.
        
        Args:
            config: System configuration with MQTT parameters
        """
        super().__init__(config)
        self._client: Optional[mqtt.Client] = None
        self._message_buffer: deque = deque(maxlen=10000)  # Buffer for messages
        self._topic_callbacks: Dict[str, List[Callable]] = {}
        self._qos = config.connection_params.get("qos", self.QOS_AT_LEAST_ONCE)
        self._buffer_size = config.connection_params.get("buffer_size", 10000)
        self._message_buffer = deque(maxlen=self._buffer_size)
    
    async def _connect_impl(self) -> None:
        """Connect to MQTT broker with authentication."""
        # Create MQTT client
        client_id = self.config.connection_params.get(
            "client_id", f"isa95_{self.config.system_id}"
        )
        
        clean_session = self.config.connection_params.get("clean_session", True)
        protocol = self.config.connection_params.get("protocol", mqtt.MQTTv311)
        
        self._client = mqtt.Client(
            client_id=client_id,
            clean_session=clean_session,
            protocol=protocol
        )
        
        # Set authentication
        if self.config.username and self.config.password:
            self._client.username_pw_set(self.config.username, self.config.password)
        
        # Set TLS if configured
        if self.config.connection_params.get("use_tls", False):
            ca_certs = self.config.connection_params.get("ca_certs")
            certfile = self.config.connection_params.get("certfile")
            keyfile = self.config.connection_params.get("keyfile")
            
            self._client.tls_set(
                ca_certs=ca_certs,
                certfile=certfile,
                keyfile=keyfile
            )
        
        # Set callbacks
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        
        # Connect to broker
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._client.connect,
            self.config.host,
            self.config.port,
            self.config.timeout
        )
        
        # Start network loop in background thread
        self._client.loop_start()
        
        # Wait for connection to be established
        max_wait = 10  # seconds
        waited = 0
        while not self._client.is_connected() and waited < max_wait:
            await asyncio.sleep(0.1)
            waited += 0.1
        
        if not self._client.is_connected():
            raise ConnectionError("Failed to connect to MQTT broker within timeout")
        
        logger.info(
            f"Connected to MQTT broker at {self.config.host}:{self.config.port}"
        )
    
    async def _disconnect_impl(self) -> None:
        """Disconnect from MQTT broker."""
        if self._client:
            # Unsubscribe from all topics
            for topic in self._topic_callbacks.keys():
                try:
                    self._client.unsubscribe(topic)
                except Exception as e:
                    logger.warning(f"Error unsubscribing from {topic}: {e}")
            
            self._topic_callbacks.clear()
            
            # Stop network loop
            self._client.loop_stop()
            
            # Disconnect
            self._client.disconnect()
            self._client = None
        
        # Clear message buffer
        self._message_buffer.clear()
    
    async def _read_data_impl(
        self, variables: List[str], time_range: TimeRange
    ) -> pd.DataFrame:
        """Read historical data from message buffer.
        
        Note: MQTT is primarily for real-time streaming. Historical data
        is limited to what's in the message buffer.
        
        Args:
            variables: List of topic names
            time_range: Time range for historical data
            
        Returns:
            DataFrame with columns: timestamp, variable, value, quality
        """
        # Filter buffered messages by topic and time range
        filtered_records = []
        
        for msg in self._message_buffer:
            if (
                msg["variable"] in variables
                and time_range.start <= msg["timestamp"] <= time_range.end
            ):
                filtered_records.append(msg)
        
        if not filtered_records:
            logger.warning(
                f"No historical data found in buffer for topics {variables}. "
                f"MQTT connector only stores recent messages in memory."
            )
        
        return pd.DataFrame(filtered_records)
    
    async def _subscribe_realtime_impl(
        self, variables: List[str], callback: Callable
    ) -> UUID:
        """Subscribe to MQTT topics for real-time data.
        
        Args:
            variables: List of MQTT topic names (supports wildcards: +, #)
            callback: Callback function for data updates
            
        Returns:
            Subscription ID
        """
        if not self._client or not self._client.is_connected():
            raise ConnectionError("MQTT client not connected")
        
        subscription_id = uuid4()
        
        # Subscribe to each topic
        for topic in variables:
            # Add callback to topic callbacks
            if topic not in self._topic_callbacks:
                self._topic_callbacks[topic] = []
                
                # Subscribe to topic with configured QoS
                result, mid = self._client.subscribe(topic, qos=self._qos)
                
                if result != mqtt.MQTT_ERR_SUCCESS:
                    raise ConnectionError(
                        f"Failed to subscribe to topic {topic}: {result}"
                    )
                
                logger.info(f"Subscribed to MQTT topic: {topic} (QoS {self._qos})")
            
            self._topic_callbacks[topic].append(callback)
        
        return subscription_id
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker."""
        if rc == 0:
            logger.info(f"MQTT connection established for {self.config.system_id}")
            self._status.state = ConnectionState.CONNECTED
            self._status.last_connected = datetime.utcnow()
        else:
            error_msg = f"MQTT connection failed with code {rc}"
            logger.error(f"{self.config.system_id}: {error_msg}")
            self._status.state = ConnectionState.ERROR
            self._status.last_error = error_msg
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker."""
        if rc != 0:
            logger.warning(
                f"Unexpected MQTT disconnect for {self.config.system_id}: {rc}"
            )
            self._status.state = ConnectionState.ERROR
            self._status.last_error = f"Unexpected disconnect: {rc}"
            
            # Trigger reconnection
            asyncio.create_task(self._retry_connection())
        else:
            logger.info(f"MQTT disconnected for {self.config.system_id}")
            self._status.state = ConnectionState.DISCONNECTED
    
    def _on_message(self, client, userdata, msg):
        """Callback when message received from MQTT broker."""
        try:
            # Parse message payload
            topic = msg.topic
            payload = msg.payload.decode("utf-8")
            
            # Try to parse as JSON
            try:
                data = json.loads(payload)
                
                # Extract value and timestamp
                if isinstance(data, dict):
                    value = data.get("value", payload)
                    timestamp_str = data.get("timestamp")
                    quality = data.get("quality", "good")
                    
                    if timestamp_str:
                        timestamp = datetime.fromisoformat(timestamp_str)
                    else:
                        timestamp = datetime.utcnow()
                else:
                    value = data
                    timestamp = datetime.utcnow()
                    quality = "good"
                    
            except json.JSONDecodeError:
                # Not JSON, use raw payload
                value = payload
                timestamp = datetime.utcnow()
                quality = "good"
            
            # Create record
            record = {
                "timestamp": timestamp,
                "variable": topic,
                "value": value,
                "quality": quality
            }
            
            # Add to buffer
            self._message_buffer.append(record)
            
            # Call registered callbacks for this topic
            callbacks = self._topic_callbacks.get(topic, [])
            
            # Also check for wildcard matches
            for pattern, pattern_callbacks in self._topic_callbacks.items():
                if self._topic_matches(topic, pattern):
                    callbacks.extend(pattern_callbacks)
            
            # Remove duplicates
            callbacks = list(set(callbacks))
            
            if callbacks:
                df = pd.DataFrame([record])
                
                for callback in callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            asyncio.create_task(callback(df))
                        else:
                            callback(df)
                    except Exception as e:
                        logger.error(f"Error in MQTT callback: {e}")
                        
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    @staticmethod
    def _topic_matches(topic: str, pattern: str) -> bool:
        """Check if topic matches MQTT pattern with wildcards.
        
        Args:
            topic: Actual topic name
            pattern: Pattern with wildcards (+ for single level, # for multi-level)
            
        Returns:
            True if topic matches pattern
        """
        if topic == pattern:
            return True
        
        topic_parts = topic.split("/")
        pattern_parts = pattern.split("/")
        
        # Multi-level wildcard
        if "#" in pattern_parts:
            hash_index = pattern_parts.index("#")
            if hash_index != len(pattern_parts) - 1:
                return False  # # must be last
            
            # Check parts before #
            for i in range(hash_index):
                if i >= len(topic_parts):
                    return False
                if pattern_parts[i] != "+" and pattern_parts[i] != topic_parts[i]:
                    return False
            
            return True
        
        # Single-level wildcard
        if len(topic_parts) != len(pattern_parts):
            return False
        
        for topic_part, pattern_part in zip(topic_parts, pattern_parts):
            if pattern_part != "+" and pattern_part != topic_part:
                return False
        
        return True
    
    def publish(self, topic: str, payload: str, qos: Optional[int] = None) -> None:
        """Publish message to MQTT topic.
        
        Args:
            topic: Topic name
            payload: Message payload
            qos: Quality of Service level (default: connector's QoS)
        """
        if not self._client or not self._client.is_connected():
            raise ConnectionError("MQTT client not connected")
        
        if qos is None:
            qos = self._qos
        
        result = self._client.publish(topic, payload, qos=qos)
        
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.error(f"Failed to publish to {topic}: {result.rc}")
        else:
            logger.debug(f"Published to {topic}: {payload}")
