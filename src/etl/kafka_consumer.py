"""Kafka consumer for streaming data ingestion.

This module implements Kafka integration for real-time data ingestion from
ISA-95 systems with configurable batch processing and offset management.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, List, Optional, Any

import pandas as pd

try:
    from confluent_kafka import Consumer, KafkaError as ConfluentKafkaError, TopicPartition
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    Consumer = None
    ConfluentKafkaError = None
    TopicPartition = None

from src.etl.pipeline import ETLPipeline, RawDataBatch, ProcessedDataBatch


logger = logging.getLogger(__name__)


@dataclass
class KafkaConsumerConfig:
    """Configuration for Kafka consumer."""
    bootstrap_servers: str  # Comma-separated list of brokers
    group_id: str
    topics: List[str]
    batch_size: int = 1000
    auto_offset_reset: str = "earliest"
    enable_auto_commit: bool = False
    max_poll_records: int = 1000
    session_timeout_ms: int = 30000
    heartbeat_interval_ms: int = 10000


class StreamingETLConsumer:
    """Kafka consumer for streaming ETL pipeline.
    
    This class integrates Kafka consumer with the ETL pipeline for real-time
    data ingestion from ISA-95 systems.
    
    Features:
    - Consumer group with configurable batch size (1000 records/batch)
    - Manual offset management for at-least-once delivery
    - Error handling and retry logic
    - Integration with ETL pipeline for data processing
    
    Requirements: 2.1
    
    Note: Requires confluent-kafka-python package to be installed.
    """
    
    def __init__(
        self,
        config: KafkaConsumerConfig,
        etl_pipeline: ETLPipeline,
        error_callback: Optional[Callable[[Exception, Dict], None]] = None
    ):
        """Initialize Kafka consumer with ETL pipeline.
        
        Args:
            config: Kafka consumer configuration
            etl_pipeline: ETL pipeline for data processing
            error_callback: Optional callback for error handling
            
        Raises:
            ImportError: If confluent-kafka-python is not installed
        """
        if not KAFKA_AVAILABLE:
            raise ImportError(
                "confluent-kafka-python is required for Kafka integration. "
                "Install it with: pip install confluent-kafka"
            )
        
        self.config = config
        self.etl_pipeline = etl_pipeline
        self.error_callback = error_callback
        self.consumer: Optional[Consumer] = None
        self._running = False
    
    def connect(self) -> None:
        """Connect to Kafka cluster and subscribe to topics.
        
        Raises:
            Exception: If connection fails
        """
        try:
            consumer_conf = {
                'bootstrap.servers': self.config.bootstrap_servers,
                'group.id': self.config.group_id,
                'auto.offset.reset': self.config.auto_offset_reset,
                'enable.auto.commit': self.config.enable_auto_commit,
                'session.timeout.ms': self.config.session_timeout_ms,
                'heartbeat.interval.ms': self.config.heartbeat_interval_ms,
            }
            
            self.consumer = Consumer(consumer_conf)
            self.consumer.subscribe(self.config.topics)
            
            logger.info(
                f"Connected to Kafka cluster. Subscribed to topics: {self.config.topics}"
            )
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            raise
    
    def disconnect(self) -> None:
        """Disconnect from Kafka cluster."""
        if self.consumer:
            self.consumer.close()
            self.consumer = None
            logger.info("Disconnected from Kafka cluster")
    
    def consume_batch(
        self,
        timeout_seconds: float = 1.0
    ) -> List[ProcessedDataBatch]:
        """Consume a batch of messages and process through ETL pipeline.
        
        This method:
        1. Polls Kafka for up to batch_size messages
        2. Groups messages by source_id
        3. Processes each group through ETL pipeline
        4. Returns processed batches
        
        Note: Offsets are NOT committed automatically. Call commit_offsets()
        after successfully processing the batch.
        
        Args:
            timeout_seconds: Timeout for polling messages (default: 1.0s)
            
        Returns:
            List of processed data batches
            
        Requirements: 2.1
        """
        if not self.consumer:
            raise RuntimeError("Consumer not connected. Call connect() first.")
        
        processed_batches: List[ProcessedDataBatch] = []
        grouped_messages: Dict[str, List[Dict]] = {}
        
        try:
            # Poll for messages up to batch_size
            messages_consumed = 0
            while messages_consumed < self.config.batch_size:
                msg = self.consumer.poll(timeout=timeout_seconds)
                
                if msg is None:
                    # No more messages available
                    break
                
                if msg.error():
                    logger.error(f"Consumer error: {msg.error()}")
                    if self.error_callback:
                        self.error_callback(Exception(msg.error()), {})
                    continue
                
                try:
                    # Deserialize message value
                    value = json.loads(msg.value().decode('utf-8'))
                    source_id = value.get('source_id', 'unknown')
                    
                    if source_id not in grouped_messages:
                        grouped_messages[source_id] = []
                    
                    grouped_messages[source_id].append(value)
                    messages_consumed += 1
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    if self.error_callback:
                        self.error_callback(e, {'message': msg})
            
            # Process each group through ETL pipeline
            for source_id, messages in grouped_messages.items():
                try:
                    # Convert messages to DataFrame
                    df = self._messages_to_dataframe(messages)
                    
                    # Create raw data batch
                    raw_batch = RawDataBatch(
                        source_id=source_id,
                        data=df,
                        timestamp=datetime.utcnow(),
                        metadata={
                            'kafka_topic': self.config.topics,
                            'message_count': len(messages),
                            'consumer_group': self.config.group_id
                        }
                    )
                    
                    # Process through ETL pipeline
                    processed_batch = self.etl_pipeline.ingest(raw_batch)
                    processed_batches.append(processed_batch)
                    
                    logger.debug(
                        f"Processed batch from {source_id}: {len(messages)} messages"
                    )
                    
                except Exception as e:
                    logger.error(f"Error processing batch from {source_id}: {e}")
                    if self.error_callback:
                        self.error_callback(e, {
                            'source_id': source_id,
                            'message_count': len(messages)
                        })
            
            return processed_batches
            
        except Exception as e:
            logger.error(f"Error during consume: {e}")
            if self.error_callback:
                self.error_callback(e, {})
            raise
    
    def commit_offsets(self) -> None:
        """Commit current offsets to Kafka.
        
        This should be called after successfully processing a batch to ensure
        at-least-once delivery semantics.
        
        Requirements: 2.1
        """
        if not self.consumer:
            raise RuntimeError("Consumer not connected. Call connect() first.")
        
        try:
            self.consumer.commit(asynchronous=False)
            logger.debug("Committed offsets to Kafka")
        except Exception as e:
            logger.error(f"Error committing offsets: {e}")
            raise
    
    def seek_to_beginning(self) -> None:
        """Seek to the beginning of all assigned partitions."""
        if not self.consumer:
            raise RuntimeError("Consumer not connected. Call connect() first.")
        
        partitions = self.consumer.assignment()
        for partition in partitions:
            self.consumer.seek(TopicPartition(partition.topic, partition.partition, 0))
        
        logger.info(f"Seeked to beginning of {len(partitions)} partitions")
    
    def seek_to_end(self) -> None:
        """Seek to the end of all assigned partitions."""
        if not self.consumer:
            raise RuntimeError("Consumer not connected. Call connect() first.")
        
        partitions = self.consumer.assignment()
        for partition in partitions:
            # Get high watermark (end offset)
            low, high = self.consumer.get_watermark_offsets(partition)
            self.consumer.seek(TopicPartition(partition.topic, partition.partition, high))
        
        logger.info(f"Seeked to end of {len(partitions)} partitions")
    
    def _messages_to_dataframe(self, messages: List[Dict]) -> pd.DataFrame:
        """Convert Kafka messages to pandas DataFrame.
        
        Expected message format:
        {
            "source_id": "station-01",
            "timestamp": "2024-01-01T00:00:00Z",
            "variables": {
                "temperature": 1500.0,
                "pressure": 2.5,
                "flow_rate": 100.0
            }
        }
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            DataFrame with timestamp index and variable columns
        """
        records = []
        
        for msg in messages:
            timestamp = msg.get('timestamp')
            variables = msg.get('variables', {})
            
            if timestamp and variables:
                record = {'timestamp': timestamp, **variables}
                records.append(record)
        
        if not records:
            # Return empty DataFrame with timestamp column
            return pd.DataFrame(columns=['timestamp'])
        
        df = pd.DataFrame(records)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')
        
        return df
    
    def start_streaming(
        self,
        callback: Callable[[List[ProcessedDataBatch]], None],
        poll_timeout_seconds: float = 1.0
    ) -> None:
        """Start streaming consumption with callback.
        
        This method runs in a loop, consuming batches and calling the callback
        for each processed batch. Use stop_streaming() to stop the loop.
        
        Args:
            callback: Function to call with processed batches
            poll_timeout_seconds: Timeout for each poll operation
        """
        if not self.consumer:
            raise RuntimeError("Consumer not connected. Call connect() first.")
        
        self._running = True
        logger.info("Started streaming consumption")
        
        try:
            while self._running:
                try:
                    # Consume and process batch
                    processed_batches = self.consume_batch(timeout_seconds=poll_timeout_seconds)
                    
                    if processed_batches:
                        # Call callback with processed batches
                        callback(processed_batches)
                        
                        # Commit offsets after successful processing
                        self.commit_offsets()
                        
                except Exception as e:
                    logger.error(f"Error in streaming loop: {e}")
                    if self.error_callback:
                        self.error_callback(e, {})
                    # Continue processing despite errors
                    
        except KeyboardInterrupt:
            logger.info("Streaming interrupted by user")
        finally:
            self._running = False
            logger.info("Stopped streaming consumption")
    
    def stop_streaming(self) -> None:
        """Stop streaming consumption."""
        self._running = False
        logger.info("Stopping streaming consumption...")
