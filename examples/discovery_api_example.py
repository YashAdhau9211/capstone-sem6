"""Example usage of causal discovery API endpoints."""

import time
from uuid import UUID

import requests

# Base URL for the API
BASE_URL = "http://localhost:8000/api/v1"


def trigger_linear_discovery(station_id: str) -> UUID:
    """
    Trigger a linear causal discovery job.

    Args:
        station_id: Manufacturing station identifier

    Returns:
        Job ID for tracking
    """
    print(f"\n=== Triggering Linear Discovery for {station_id} ===")

    # Submit discovery job
    response = requests.post(
        f"{BASE_URL}/discovery/linear",
        json={
            "station_id": station_id,
            "algorithm": "linear",
            "data_source": "timeseries_db",
            "time_range": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-01-02T00:00:00Z",
            },
        },
    )

    if response.status_code != 202:
        print(f"Error: {response.status_code} - {response.text}")
        return None

    data = response.json()
    job_id = UUID(data["job_id"])

    print(f"Job submitted successfully!")
    print(f"  Job ID: {job_id}")
    print(f"  Station: {data['station_id']}")
    print(f"  Algorithm: {data['algorithm']}")
    print(f"  Status: {data['status']}")

    return job_id


def trigger_nonlinear_discovery(station_id: str) -> UUID:
    """
    Trigger a nonlinear causal discovery job.

    Args:
        station_id: Manufacturing station identifier

    Returns:
        Job ID for tracking
    """
    print(f"\n=== Triggering Nonlinear Discovery for {station_id} ===")

    # Submit discovery job
    response = requests.post(
        f"{BASE_URL}/discovery/nonlinear",
        json={
            "station_id": station_id,
            "algorithm": "nonlinear",
        },
    )

    if response.status_code != 202:
        print(f"Error: {response.status_code} - {response.text}")
        return None

    data = response.json()
    job_id = UUID(data["job_id"])

    print(f"Job submitted successfully!")
    print(f"  Job ID: {job_id}")
    print(f"  Station: {data['station_id']}")
    print(f"  Algorithm: {data['algorithm']}")
    print(f"  Status: {data['status']}")

    return job_id


def check_job_status(job_id: UUID) -> dict:
    """
    Check the status of a discovery job.

    Args:
        job_id: Job identifier

    Returns:
        Job status information
    """
    response = requests.get(f"{BASE_URL}/discovery/jobs/{job_id}")

    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return None

    return response.json()


def wait_for_completion(job_id: UUID, max_wait: int = 60) -> dict:
    """
    Wait for a discovery job to complete.

    Args:
        job_id: Job identifier
        max_wait: Maximum wait time in seconds

    Returns:
        Final job status
    """
    print(f"\n=== Waiting for Job {job_id} to Complete ===")

    start_time = time.time()
    last_progress = None

    while time.time() - start_time < max_wait:
        status = check_job_status(job_id)

        if status is None:
            return None

        # Print progress updates
        if status["progress"] != last_progress:
            print(f"  Status: {status['status']}, Progress: {status['progress']}%")
            last_progress = status["progress"]

        # Check if completed
        if status["status"] in ["completed", "failed"]:
            print(f"\nJob {status['status']}!")

            if status["status"] == "completed":
                print(f"  Result DAG ID: {status['result_dag_id']}")
                print(f"  Started: {status['started_at']}")
                print(f"  Completed: {status['completed_at']}")
            else:
                print(f"  Error: {status['error_message']}")

            return status

        time.sleep(1)

    print(f"\nTimeout waiting for job to complete")
    return status


def main():
    """Run discovery API examples."""
    print("=" * 60)
    print("Causal Discovery API Example")
    print("=" * 60)

    # Example 1: Linear discovery
    job_id = trigger_linear_discovery("furnace-01")
    if job_id:
        final_status = wait_for_completion(job_id)

        if final_status and final_status["status"] == "completed":
            print(f"\n✓ Linear discovery completed successfully!")
            print(f"  DAG ID: {final_status['result_dag_id']}")

    # Example 2: Nonlinear discovery
    job_id = trigger_nonlinear_discovery("mill-01")
    if job_id:
        final_status = wait_for_completion(job_id)

        if final_status and final_status["status"] == "completed":
            print(f"\n✓ Nonlinear discovery completed successfully!")
            print(f"  DAG ID: {final_status['result_dag_id']}")

    # Example 3: Multiple concurrent jobs
    print("\n" + "=" * 60)
    print("Running Multiple Concurrent Discovery Jobs")
    print("=" * 60)

    stations = ["furnace-01", "mill-01", "anneal-01"]
    job_ids = []

    for station in stations:
        job_id = trigger_linear_discovery(station)
        if job_id:
            job_ids.append(job_id)

    print(f"\nSubmitted {len(job_ids)} jobs. Waiting for completion...")

    for job_id in job_ids:
        status = wait_for_completion(job_id, max_wait=30)
        if status and status["status"] == "completed":
            print(f"  ✓ Job {job_id} completed")

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    # Note: This example requires the API server to be running
    # Start the server with: uvicorn src.main:app --reload
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\nError: Could not connect to API server.")
        print("Please start the server with: uvicorn src.main:app --reload")
    except Exception as e:
        print(f"\nError: {e}")
