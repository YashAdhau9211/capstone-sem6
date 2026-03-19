#!/usr/bin/env python3
"""Example usage of TimeSeriesWriter for writing sensor data to InfluxDB.

This example demonstrates:
1. Writing individual batches
2. Writing large streams with automatic batching
3. Error handling and retry logic
4. Using context manager for automatic cleanup
"""

import random
from datetime import datetime, timedelta

from config.settings import settings
from src.data_integration.timeseries_writer import TimeSeriesWriter
from src.models.timeseries import TimeSeriesData


def generate_sample_data(
    station_id: str, variable: str, num_points: int = 100
) -> list[TimeSeriesData]:
    """Generate sample sensor data for testing.

    Args:
        station_id: Manufacturing station identifier
        variable: Variable name (e.g., "temperature", "pressure")
        num_points: Number of data points to generate

    Returns:
        List of TimeSeriesData objects
    """
    base_time = datetime.now()
    data = []

    for i in range(num_points):
        # Generate realistic sensor values with some noise
        if variable == "temperature":
            base_value = 1500.0
            noise = random.uniform(-50, 50)
        elif variable == "pressure":
            base_value = 2.5
            noise = random.uniform(-0.2, 0.2)
        elif variable == "speed":
            base_value = 1200.0
            noise = random.uniform(-100, 100)
        else:
            base_value = 100.0
            noise = random.uniform(-10, 10)

        # Randomly assign quality
        quality = random.choices(
            ["good", "uncertain", "bad"], weights=[0.85, 0.10, 0.05]
        )[0]

        data.append(
            TimeSeriesData(
                station_id=station_id,
                variable=variable,
                timestamp=base_time + timedelta(seconds=i),
                value=base_value + noise,
                quality=quality,
                metadata={"unit": "celsius" if variable == "temperature" else ""},
            )
        )

    return data


def example_batch_write():
    """Example: Write a single batch of data."""
    print("\n" + "=" * 60)
    print("Example 1: Writing a single batch")
    print("=" * 60)

    # Create writer with context manager
    with TimeSeriesWriter(
        url=settings.influxdb_url,
        token=settings.influxdb_token,
        org=settings.influxdb_org,
        bucket=settings.influxdb_bucket,
        batch_size=1000,
        max_retries=3,
    ) as writer:
        # Generate sample data
        data = generate_sample_data("furnace-01", "temperature", num_points=100)

        print(f"Writing {len(data)} records to InfluxDB...")

        # Write batch
        result = writer.write_batch(data)

        if result.success:
            print(f"✓ Successfully wrote {result.records_written} records")
            if result.retry_count > 0:
                print(f"  (after {result.retry_count} retries)")
        else:
            print(f"✗ Write failed: {result.error_message}")


def example_stream_write():
    """Example: Write a large stream with automatic batching."""
    print("\n" + "=" * 60)
    print("Example 2: Writing a large stream with automatic batching")
    print("=" * 60)

    with TimeSeriesWriter(
        url=settings.influxdb_url,
        token=settings.influxdb_token,
        org=settings.influxdb_org,
        bucket=settings.influxdb_bucket,
        batch_size=1000,
    ) as writer:
        # Generate large dataset (5000 records)
        print("Generating 5000 sample records...")
        data = []
        for station in ["furnace-01", "mill-01", "anneal-01"]:
            for variable in ["temperature", "pressure", "speed"]:
                data.extend(
                    generate_sample_data(station, variable, num_points=555)
                )

        print(f"Writing {len(data)} records in batches of 1000...")

        # Write stream (automatically batched)
        results = writer.write_stream(data)

        # Report results
        total_written = sum(r.records_written for r in results)
        failed_batches = sum(1 for r in results if not r.success)

        print(f"\n✓ Wrote {total_written} records in {len(results)} batches")
        if failed_batches > 0:
            print(f"✗ {failed_batches} batches failed")


def example_multi_station_write():
    """Example: Write data from multiple stations."""
    print("\n" + "=" * 60)
    print("Example 3: Writing data from multiple stations")
    print("=" * 60)

    with TimeSeriesWriter(
        url=settings.influxdb_url,
        token=settings.influxdb_token,
        org=settings.influxdb_org,
        bucket=settings.influxdb_bucket,
    ) as writer:
        # Generate data for multiple stations
        stations = {
            "furnace-01": ["temperature", "pressure", "oxygen_level"],
            "mill-01": ["speed", "torque", "vibration"],
            "anneal-01": ["temperature", "cooling_rate", "hardness"],
        }

        all_data = []
        for station_id, variables in stations.items():
            for variable in variables:
                data = generate_sample_data(station_id, variable, num_points=50)
                all_data.extend(data)

        print(f"Writing {len(all_data)} records from {len(stations)} stations...")

        result = writer.write_batch(all_data)

        if result.success:
            print(f"✓ Successfully wrote {result.records_written} records")
            print(f"  Stations: {', '.join(stations.keys())}")
        else:
            print(f"✗ Write failed: {result.error_message}")


def example_error_handling():
    """Example: Demonstrate error handling with invalid configuration."""
    print("\n" + "=" * 60)
    print("Example 4: Error handling with retry logic")
    print("=" * 60)

    # Use invalid token to trigger error (for demonstration)
    print("Attempting write with invalid token (will retry)...")

    writer = TimeSeriesWriter(
        url=settings.influxdb_url,
        token="invalid-token-for-demo",
        org=settings.influxdb_org,
        bucket=settings.influxdb_bucket,
        max_retries=2,
    )

    data = generate_sample_data("test-station", "test-variable", num_points=10)

    result = writer.write_batch(data)

    if result.success:
        print(f"✓ Write succeeded after {result.retry_count} retries")
    else:
        print(f"✗ Write failed after {result.retry_count} retries")
        print(f"  Error: {result.error_message}")

    writer.close()


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("TimeSeriesWriter Examples")
    print("=" * 60)
    print(f"\nInfluxDB Configuration:")
    print(f"  URL: {settings.influxdb_url}")
    print(f"  Org: {settings.influxdb_org}")
    print(f"  Bucket: {settings.influxdb_bucket}")

    try:
        # Run examples
        example_batch_write()
        example_stream_write()
        example_multi_station_write()

        # Uncomment to test error handling
        # example_error_handling()

        print("\n" + "=" * 60)
        print("All examples completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error running examples: {e}")
        print("\nMake sure InfluxDB is running:")
        print("  docker-compose up -d influxdb")
        print("  make setup-influxdb")


if __name__ == "__main__":
    main()
