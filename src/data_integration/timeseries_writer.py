"""Time-series database writer for sensor data.

This module provides a writer class for batch inserts to InfluxDB with error handling,
retry logic, and data compression for storage efficiency.

Requirements: 29.1, 29.2, 29.7
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS, WriteApi
from influxdb_client.rest import ApiException

from src.models.timeseries import TimeSeriesData

logger = logging.getLogger(__name__)


@dataclass
class WriteResult:
    """Result of a batch write operation."""

    success: bool
    records_written: int
    error_message: Optional[str] = None
    retry_count: int = 0


class TimeSeriesWriter:
    """Writer class for batch inserts to InfluxDB time-series database.

    Features:
    - Batch inserts (1000 records/batch by default)
    - Error handling and retry logic with exponential backoff
    - Data compression for storage efficiency
    - Support for sensor data with tags (station_id, variable, quality)
    """

    def __init__(
        self,
        url: str,
        token: str,
        org: str,
        bucket: str,
        batch_size: int = 1000,
        max_retries: int = 3,
    ):
        """Initialize the time-series writer.

        Args:
            url: InfluxDB server URL
            token: Authentication token
            org: Organization name
            bucket: Bucket name for storing data
            batch_size: Number of records per batch (default: 1000)
            max_retries: Maximum number of retry attempts (default: 3)
        """
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket
        self.batch_size = batch_size
        self.max_retries = max_retries

        # Initialize InfluxDB client with compression enabled
        self.client = InfluxDBClient(
            url=url,
            token=token,
            org=org,
            enable_gzip=True,  # Enable compression for storage efficiency
        )
        self.write_api: WriteApi = self.client.write_api(write_options=SYNCHRONOUS)

    def write_batch(
        self, data: List[TimeSeriesData], retry_count: int = 0
    ) -> WriteResult:
        """Write a batch of time-series data to InfluxDB.

        Args:
            data: List of TimeSeriesData objects to write
            retry_count: Current retry attempt number

        Returns:
            WriteResult with success status and metadata
        """
        if not data:
            return WriteResult(success=True, records_written=0)

        try:
            # Convert TimeSeriesData to InfluxDB Points
            points = self._convert_to_points(data)

            # Write points to InfluxDB
            self.write_api.write(bucket=self.bucket, org=self.org, record=points)

            logger.info(f"Successfully wrote {len(data)} records to InfluxDB")
            return WriteResult(
                success=True, records_written=len(data), retry_count=retry_count
            )

        except ApiException as e:
            logger.error(f"InfluxDB API error: {e}")
            return self._handle_write_error(data, e, retry_count)

        except Exception as e:
            logger.error(f"Unexpected error writing to InfluxDB: {e}")
            return self._handle_write_error(data, e, retry_count)

    def write_stream(self, data_stream: List[TimeSeriesData]) -> List[WriteResult]:
        """Write a stream of time-series data in batches.

        Args:
            data_stream: List of TimeSeriesData objects to write

        Returns:
            List of WriteResult objects, one per batch
        """
        results = []
        for i in range(0, len(data_stream), self.batch_size):
            batch = data_stream[i : i + self.batch_size]
            result = self.write_batch(batch)
            results.append(result)

            if not result.success:
                logger.warning(
                    f"Batch {i // self.batch_size + 1} failed: {result.error_message}"
                )

        return results

    def _convert_to_points(self, data: List[TimeSeriesData]) -> List[Point]:
        """Convert TimeSeriesData objects to InfluxDB Points.

        Args:
            data: List of TimeSeriesData objects

        Returns:
            List of InfluxDB Point objects
        """
        points = []
        for record in data:
            point = (
                Point("sensor_data")
                .tag("station_id", record.station_id)
                .tag("variable", record.variable)
                .tag("quality", record.quality)
                .field("value", float(record.value))
                .time(record.timestamp, WritePrecision.NS)
            )

            # Add metadata as fields if present
            if record.metadata:
                for key, value in record.metadata.items():
                    if isinstance(value, (int, float, bool)):
                        point = point.field(f"meta_{key}", value)
                    elif isinstance(value, str):
                        point = point.tag(f"meta_{key}", value)

            points.append(point)

        return points

    def _handle_write_error(
        self, data: List[TimeSeriesData], error: Exception, retry_count: int
    ) -> WriteResult:
        """Handle write errors with retry logic.

        Args:
            data: Data that failed to write
            error: Exception that occurred
            retry_count: Current retry attempt number

        Returns:
            WriteResult with error information
        """
        if retry_count >= self.max_retries:
            error_msg = f"Max retries ({self.max_retries}) exceeded: {str(error)}"
            logger.error(error_msg)
            return WriteResult(
                success=False,
                records_written=0,
                error_message=error_msg,
                retry_count=retry_count,
            )

        # Exponential backoff: 1s, 2s, 4s
        wait_time = 2**retry_count
        logger.warning(
            f"Write failed, retrying in {wait_time}s (attempt {retry_count + 1}/{self.max_retries})"
        )

        import time

        time.sleep(wait_time)

        # Retry the write
        return self.write_batch(data, retry_count + 1)

    def close(self) -> None:
        """Close the InfluxDB client connection."""
        if self.write_api:
            self.write_api.close()
        if self.client:
            self.client.close()
        logger.info("InfluxDB client connection closed")

    def __enter__(self) -> "TimeSeriesWriter":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()
