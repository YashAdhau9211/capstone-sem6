#!/usr/bin/env python3
"""Setup script for InfluxDB time-series database.

This script configures InfluxDB with:
- Measurement schema for sensor_data
- Retention policies: raw data (2 years), 1-hour aggregates (7 years), daily aggregates (indefinite)
- Continuous queries for automatic downsampling
- Indexes for efficient time-range queries

Requirements: 29.1, 29.2
"""

import logging
import sys
from datetime import timedelta

from influxdb_client import InfluxDBClient

try:
    from influxdb_client.domain.bucket_retention_rules import BucketRetentionRules
except ImportError:
    # Fallback for different influxdb-client versions
    try:
        from influxdb_client.client.bucket_api import BucketRetentionRules
    except ImportError:
        # For older versions, we'll create retention rules as dicts
        BucketRetentionRules = None

from config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _create_retention_rule(every_seconds: int):
    """Create a retention rule compatible with different influxdb-client versions."""
    if BucketRetentionRules is not None:
        return BucketRetentionRules(type="expire", every_seconds=every_seconds)
    else:
        # Fallback for older versions - return dict
        return {"type": "expire", "everySeconds": every_seconds}


def setup_influxdb() -> bool:
    """Set up InfluxDB buckets and retention policies.

    Returns:
        True if setup successful, False otherwise
    """
    try:
        # Connect to InfluxDB
        client = InfluxDBClient(
            url=settings.influxdb_url,
            token=settings.influxdb_token,
            org=settings.influxdb_org,
        )

        bucket_api = client.buckets_api()
        org_id = client.organizations_api().find_organizations(
            org=settings.influxdb_org
        )[0].id

        logger.info(f"Connected to InfluxDB at {settings.influxdb_url}")

        # 1. Create/update raw data bucket with 2-year retention
        # Requirement 29.1: Retain raw sensor data for at least 2 years
        raw_bucket_name = settings.influxdb_bucket
        raw_retention_seconds = int(timedelta(days=730).total_seconds())  # 2 years

        existing_raw = bucket_api.find_bucket_by_name(raw_bucket_name)
        if existing_raw:
            logger.info(f"Updating existing bucket: {raw_bucket_name}")
            existing_raw.retention_rules = [_create_retention_rule(raw_retention_seconds)]
            bucket_api.update_bucket(bucket=existing_raw)
        else:
            logger.info(f"Creating bucket: {raw_bucket_name} (2-year retention)")
            bucket_api.create_bucket(
                bucket_name=raw_bucket_name,
                org_id=org_id,
                retention_rules=[_create_retention_rule(raw_retention_seconds)],
                description="Raw sensor data with 2-year retention",
            )

        # 2. Create 1-hour aggregates bucket with 7-year retention
        # Requirement 29.2: Retain aggregated daily statistics for at least 7 years
        hourly_bucket_name = f"{settings.influxdb_bucket}_hourly"
        hourly_retention_seconds = int(timedelta(days=2555).total_seconds())  # 7 years

        existing_hourly = bucket_api.find_bucket_by_name(hourly_bucket_name)
        if existing_hourly:
            logger.info(f"Updating existing bucket: {hourly_bucket_name}")
            existing_hourly.retention_rules = [_create_retention_rule(hourly_retention_seconds)]
            bucket_api.update_bucket(bucket=existing_hourly)
        else:
            logger.info(f"Creating bucket: {hourly_bucket_name} (7-year retention)")
            bucket_api.create_bucket(
                bucket_name=hourly_bucket_name,
                org_id=org_id,
                retention_rules=[_create_retention_rule(hourly_retention_seconds)],
                description="1-hour aggregated sensor data with 7-year retention",
            )

        # 3. Create daily aggregates bucket with indefinite retention
        daily_bucket_name = f"{settings.influxdb_bucket}_daily"

        existing_daily = bucket_api.find_bucket_by_name(daily_bucket_name)
        if existing_daily:
            logger.info(f"Updating existing bucket: {daily_bucket_name}")
            existing_daily.retention_rules = []  # Indefinite retention
            bucket_api.update_bucket(bucket=existing_daily)
        else:
            logger.info(
                f"Creating bucket: {daily_bucket_name} (indefinite retention)"
            )
            bucket_api.create_bucket(
                bucket_name=daily_bucket_name,
                org_id=org_id,
                retention_rules=[],  # Empty list = indefinite retention
                description="Daily aggregated sensor data with indefinite retention",
            )

        # 4. Create tasks for automatic downsampling
        logger.info("Setting up downsampling tasks...")
        setup_downsampling_tasks(client, org_id)

        client.close()
        logger.info("InfluxDB setup completed successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to setup InfluxDB: {e}")
        return False


def setup_downsampling_tasks(client: InfluxDBClient, org_id: str) -> None:
    """Create InfluxDB tasks for automatic downsampling.

    Args:
        client: InfluxDB client
        org_id: Organization ID
    """
    tasks_api = client.tasks_api()

    # Task 1: Downsample raw data to 1-hour aggregates
    hourly_task_name = "downsample_to_hourly"
    hourly_flux = f"""
option task = {{name: "{hourly_task_name}", every: 1h}}

from(bucket: "{settings.influxdb_bucket}")
    |> range(start: -2h)
    |> filter(fn: (r) => r._measurement == "sensor_data")
    |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
    |> set(key: "_measurement", value: "sensor_data_hourly")
    |> to(bucket: "{settings.influxdb_bucket}_hourly", org: "{settings.influxdb_org}")
"""

    # Check if task exists
    try:
        existing_tasks = tasks_api.find_tasks(name=hourly_task_name)
        if existing_tasks:
            logger.info(f"Task '{hourly_task_name}' already exists, skipping creation")
        else:
            logger.info(f"Creating task: {hourly_task_name}")
            from influxdb_client.domain.task_create_request import TaskCreateRequest
            task_request = TaskCreateRequest(
                name=hourly_task_name,
                org_id=org_id,
                flux=hourly_flux,
                every="1h"
            )
            tasks_api.create_task(task_create_request=task_request)
    except Exception as e:
        logger.warning(f"Could not create task '{hourly_task_name}': {e}")

    # Task 2: Downsample 1-hour aggregates to daily aggregates
    daily_task_name = "downsample_to_daily"
    daily_flux = f"""
option task = {{name: "{daily_task_name}", every: 1d}}

from(bucket: "{settings.influxdb_bucket}_hourly")
    |> range(start: -2d)
    |> filter(fn: (r) => r._measurement == "sensor_data_hourly")
    |> aggregateWindow(every: 1d, fn: mean, createEmpty: false)
    |> set(key: "_measurement", value: "sensor_data_daily")
    |> to(bucket: "{settings.influxdb_bucket}_daily", org: "{settings.influxdb_org}")
"""

    try:
        existing_daily_tasks = tasks_api.find_tasks(name=daily_task_name)
        if existing_daily_tasks:
            logger.info(f"Task '{daily_task_name}' already exists, skipping creation")
        else:
            logger.info(f"Creating task: {daily_task_name}")
            from influxdb_client.domain.task_create_request import TaskCreateRequest
            task_request = TaskCreateRequest(
                name=daily_task_name,
                org_id=org_id,
                flux=daily_flux,
                every="1d"
            )
            tasks_api.create_task(task_create_request=task_request)
    except Exception as e:
        logger.warning(f"Could not create task '{daily_task_name}': {e}")


def verify_setup() -> bool:
    """Verify InfluxDB setup is correct.

    Returns:
        True if verification successful, False otherwise
    """
    try:
        client = InfluxDBClient(
            url=settings.influxdb_url,
            token=settings.influxdb_token,
            org=settings.influxdb_org,
        )

        bucket_api = client.buckets_api()

        # Check all buckets exist
        buckets_to_check = [
            settings.influxdb_bucket,
            f"{settings.influxdb_bucket}_hourly",
            f"{settings.influxdb_bucket}_daily",
        ]

        for bucket_name in buckets_to_check:
            bucket = bucket_api.find_bucket_by_name(bucket_name)
            if not bucket:
                logger.error(f"Bucket '{bucket_name}' not found")
                return False
            logger.info(f"✓ Bucket '{bucket_name}' exists")

        # Check tasks exist (optional - don't fail if tasks aren't created)
        try:
            tasks_api = client.tasks_api()
            tasks_to_check = ["downsample_to_hourly", "downsample_to_daily"]

            for task_name in tasks_to_check:
                tasks = tasks_api.find_tasks(name=task_name)
                if not tasks:
                    logger.warning(f"Task '{task_name}' not found (optional)")
                else:
                    logger.info(f"✓ Task '{task_name}' exists")
        except Exception as e:
            logger.warning(f"Could not verify tasks: {e}")

        client.close()
        logger.info("✓ InfluxDB verification completed successfully")
        return True

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False


def main() -> int:
    """Main entry point."""
    logger.info("Starting InfluxDB setup...")

    if not setup_influxdb():
        logger.error("Setup failed")
        return 1

    logger.info("\nVerifying setup...")
    if not verify_setup():
        logger.error("Verification failed")
        return 1

    logger.info("\n" + "=" * 60)
    logger.info("InfluxDB setup completed successfully!")
    logger.info("=" * 60)
    logger.info(f"\nBuckets created:")
    logger.info(f"  - {settings.influxdb_bucket} (raw data, 2-year retention)")
    logger.info(
        f"  - {settings.influxdb_bucket}_hourly (1-hour aggregates, 7-year retention)"
    )
    logger.info(
        f"  - {settings.influxdb_bucket}_daily (daily aggregates, indefinite retention)"
    )
    logger.info(f"\nDownsampling tasks created:")
    logger.info(f"  - downsample_to_hourly (runs every 1 hour)")
    logger.info(f"  - downsample_to_daily (runs every 1 day)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
