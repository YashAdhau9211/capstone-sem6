# ETL Pipeline Module

This module implements the ETL (Extract, Transform, Load) pipeline for time-series data synchronization and preprocessing in the Causal AI Manufacturing Platform.

## Overview

The ETL pipeline handles data ingestion from ISA-95 industrial control systems, performs timestamp synchronization, resampling, and gap interpolation to prepare data for causal analysis.

## Components

### 1. ETLPipeline (`pipeline.py`)

Core ETL pipeline with the following capabilities:

- **Raw data batch processing**: Ingest data from multiple sources
- **Timestamp synchronization**: Align timestamps to NTP-aligned reference clock (UTC)
- **Resampling**: Convert data to uniform intervals with multiple strategies:
  - Forward-fill
  - Backward-fill
  - Linear interpolation
- **Gap interpolation**: Handle missing data intelligently:
  - Gaps < 5 minutes: Linear interpolation
  - Gaps ≥ 5 minutes: Mark as NaN

**Requirements**: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6

**Example Usage**:

```python
from datetime import timedelta
from src.etl import ETLPipeline, RawDataBatch
import pandas as pd

# Create pipeline
pipeline = ETLPipeline(
    reference_clock='UTC',
    max_gap_interpolation=timedelta(minutes=5),
    default_resample_interval=timedelta(seconds=30)
)

# Create raw data batch
raw_data = RawDataBatch(
    source_id='station-01',
    data=your_dataframe,
    timestamp=datetime.utcnow()
)

# Process through pipeline
processed = pipeline.ingest(raw_data)

# Access processed data
print(processed.data)
print(processed.lineage)  # Track transformations
print(processed.original_timestamps)  # Audit trail
```

### 2. Kafka Consumer (`kafka_consumer.py`)

Streaming data ingestion from Kafka topics with ETL integration.

**Features**:
- Consumer group with configurable batch size (1000 records/batch)
- Manual offset management for at-least-once delivery
- Error handling and retry logic
- Integration with ETL pipeline

**Requirements**: 2.1

**Note**: Requires `confluent-kafka-python` package:
```bash
pip install confluent-kafka
```

**Example Usage**:

```python
from src.etl import StreamingETLConsumer, KafkaConsumerConfig, ETLPipeline

# Configure Kafka consumer
config = KafkaConsumerConfig(
    bootstrap_servers='localhost:9092',
    group_id='manufacturing-etl',
    topics=['sensor-data'],
    batch_size=1000
)

# Create ETL pipeline
pipeline = ETLPipeline()

# Create streaming consumer
consumer = StreamingETLConsumer(config, pipeline)

# Connect and consume
consumer.connect()

# Process batches
processed_batches = consumer.consume_batch(timeout_seconds=1.0)

# Commit offsets after successful processing
consumer.commit_offsets()

# Or use streaming mode with callback
def process_batches(batches):
    for batch in batches:
        # Store to database, etc.
        print(f"Processed {len(batch.data)} records from {batch.source_id}")

consumer.start_streaming(process_batches)
```

### 3. Metadata Tracker (`metadata.py`)

Data lineage tracking and metadata management.

**Features**:
- Original timestamp preservation
- Transformation history tracking
- Alignment error calculation
- Audit trail generation

**Requirements**: 2.5, 2.6

**Example Usage**:

```python
from src.etl.metadata import MetadataTracker, DataLineage, TransformationType

# Create lineage
lineage = MetadataTracker.create_lineage(
    source_id='station-01',
    original_data=your_dataframe,
    metadata={'source': 'OPC UA'}
)

# Add transformations
lineage.add_transformation(
    transformation_type=TransformationType.TIMESTAMP_SYNC,
    parameters={'reference_clock': 'UTC'},
    input_count=1000,
    output_count=1000
)

# Get summary
print(lineage.get_transformation_summary())

# Calculate alignment error
error = MetadataTracker.calculate_alignment_error(original, synchronized)
assert error < 1.0  # Must be <1 second per Requirement 2.6
```

## Data Models

### RawDataBatch

```python
@dataclass
class RawDataBatch:
    source_id: str              # Source system identifier
    data: DataFrame             # Raw time-series data
    timestamp: datetime         # Ingestion timestamp
    metadata: Dict[str, Any]    # Additional metadata
```

### ProcessedDataBatch

```python
@dataclass
class ProcessedDataBatch:
    source_id: str                  # Source system identifier
    data: DataFrame                 # Processed time-series data
    timestamp: datetime             # Processing timestamp
    original_timestamps: DataFrame  # Original timestamps (audit)
    metadata: Dict[str, Any]        # Enriched metadata
    lineage: List[str]             # Transformation history
```

### DataLineage

```python
@dataclass
class DataLineage:
    source_id: str                          # Source identifier
    ingestion_timestamp: datetime           # When data was ingested
    transformations: List[TransformationRecord]  # All transformations
    original_timestamps: DataFrame          # Original timestamps
    metadata: Dict[str, Any]               # Additional metadata
```

## Performance Targets

- **Throughput**: 10,000 records/second per pipeline instance
- **Latency**: <1 second from ingestion to storage
- **Timestamp alignment error**: <1 second (Requirement 2.6)
- **Batch size**: 1000 records per batch (configurable)

## Testing

Run unit tests:

```bash
pytest tests/test_etl_pipeline.py -v
```

Test coverage includes:
- Timestamp synchronization accuracy
- Gap interpolation logic (< 5min vs ≥ 5min)
- Resampling strategies (forward-fill, backward-fill, linear)
- Metadata tracking and lineage
- Alignment error validation

## Requirements Mapping

| Requirement | Description | Implementation |
|-------------|-------------|----------------|
| 2.1 | Time-series synchronization | `ETLPipeline.synchronize_timestamps()` |
| 2.2 | Uniform interval resampling | `ETLPipeline.resample()` |
| 2.3 | Gap interpolation (<5min) | `ETLPipeline.interpolate_gaps()` |
| 2.4 | Large gap handling (≥5min) | `ETLPipeline.interpolate_gaps()` |
| 2.5 | Original timestamp preservation | `ProcessedDataBatch.original_timestamps` |
| 2.6 | Alignment error <1 second | `MetadataTracker.calculate_alignment_error()` |

## Integration

The ETL pipeline integrates with:

1. **Data Integration Layer**: Receives data from ISA-95 connectors
2. **Time-Series Database**: Stores processed data (InfluxDB/TimescaleDB)
3. **Causal Discovery Engine**: Provides synchronized data for analysis
4. **Audit Logger**: Tracks data lineage for compliance

## Configuration

Environment variables:

```bash
# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_GROUP_ID=manufacturing-etl
KAFKA_TOPICS=sensor-data,plc-data

# ETL configuration
ETL_REFERENCE_CLOCK=UTC
ETL_MAX_GAP_MINUTES=5
ETL_RESAMPLE_INTERVAL_SECONDS=30
ETL_BATCH_SIZE=1000
```

## Error Handling

The ETL pipeline includes comprehensive error handling:

- **Connection failures**: Logged with timestamp and system ID
- **Data validation errors**: Flagged and quarantined
- **Processing errors**: Logged with context and lineage
- **Kafka errors**: Retry logic with exponential backoff

## Future Enhancements

- [ ] Support for additional resampling strategies (cubic spline, etc.)
- [ ] Distributed processing with Dask for large datasets
- [ ] Real-time anomaly detection during ingestion
- [ ] Automatic schema inference and validation
- [ ] Support for additional message formats (Avro, Protobuf)
