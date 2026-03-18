"""ETL Pipeline for time-series data synchronization and preprocessing."""

from src.etl.pipeline import ETLPipeline, RawDataBatch, ProcessedDataBatch, ResampleStrategy
from src.etl.kafka_consumer import StreamingETLConsumer, KafkaConsumerConfig
from src.etl.metadata import (
    DataLineage,
    MetadataTracker,
    TransformationRecord,
    TransformationType
)

__all__ = [
    "ETLPipeline",
    "RawDataBatch",
    "ProcessedDataBatch",
    "ResampleStrategy",
    "StreamingETLConsumer",
    "KafkaConsumerConfig",
    "DataLineage",
    "MetadataTracker",
    "TransformationRecord",
    "TransformationType",
]
