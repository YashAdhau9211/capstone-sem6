"""Example demonstrating authentication and authorization."""

import requests
import json

# Base URL
BASE_URL = "http://localhost:8000"


def login(username: str, password: str) -> dict:
    """Login and get access token."""
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        data={"username": username, "password": password},
    )
    response.raise_for_status()
    return response.json()


def get_current_user(token: str) -> dict:
    """Get current user information."""
    response = requests.get(
        f"{BASE_URL}/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    response.raise_for_status()
    return response.json()


def list_dags(token: str) -> list:
    """List all DAGs (requires view_model permission)."""
    response = requests.get(
        f"{BASE_URL}/api/v1/dags/",
        headers={"Authorization": f"Bearer {token}"},
    )
    response.raise_for_status()
    return response.json()


def create_dag(token: str, station_id: str) -> dict:
    """Create a new DAG (requires create_model permission)."""
    dag_data = {
        "nodes": ["temperature", "pressure", "yield"],
        "edges": [
            {
                "source": "temperature",
                "target": "yield",
                "coefficient": 0.5,
                "confidence": 0.9,
                "edge_type": "linear",
            }
        ],
        "algorithm": "DirectLiNGAM",
        "created_by": "test-user",
        "metadata": {},
    }

    response = requests.post(
        f"{BASE_URL}/api/v1/dags/{station_id}",
        headers={"Authorization": f"Bearer {token}"},
        json=dag_data,
    )
    response.raise_for_status()
    return response.json()


def run_simulation(token: str, station_id: str) -> dict:
    """Run counterfactual simulation (requires run_simulation permission)."""
    simulation_data = {
        "station_id": station_id,
        "interventions": {"temperature": 1500},
        "time_range": {
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-01T01:00:00Z",
        },
    }

    response = requests.post(
        f"{BASE_URL}/api/v1/simulation/counterfactual",
        headers={"Authorization": f"Bearer {token}"},
        json=simulation_data,
    )
    response.raise_for_status()
    return response.json()


def main():
    """Run authentication examples."""
    print("=== Authentication and Authorization Examples ===\n")

    # Example 1: Login as Process Engineer
    print("1. Login as Process Engineer")
    try:
        login_response = login("engineer", "Engineer123!")
        token = login_response["access_token"]
        user = login_response["user"]

        print(f"   ✓ Logged in as: {user['username']}")
        print(f"   ✓ Roles: {', '.join(user['roles'])}")
        print(f"   ✓ Permissions: {', '.join(user['permissions'])}")
        print()

        # Example 2: View DAGs (allowed)
        print("2. View DAGs (allowed for Process_Engineer)")
        dags = list_dags(token)
        print(f"   ✓ Retrieved {len(dags)} DAGs")
        print()

        # Example 3: Create DAG (allowed)
        print("3. Create DAG (allowed for Process_Engineer)")
        new_dag = create_dag(token, "test-station-01")
        print(f"   ✓ Created DAG for station: {new_dag['station_id']}")
        print()

        # Example 4: Run simulation (allowed)
        print("4. Run simulation (allowed for Process_Engineer)")
        try:
            simulation_result = run_simulation(token, "furnace-01")
            print(f"   ✓ Simulation completed")
        except requests.HTTPError as e:
            print(f"   ✗ Simulation failed: {e}")
        print()

    except requests.HTTPError as e:
        print(f"   ✗ Error: {e}")
        print()

    # Example 5: Login as Citizen Data Scientist
    print("5. Login as Citizen Data Scientist")
    try:
        login_response = login("analyst", "Analyst123!")
        token = login_response["access_token"]
        user = login_response["user"]

        print(f"   ✓ Logged in as: {user['username']}")
        print(f"   ✓ Roles: {', '.join(user['roles'])}")
        print(f"   ✓ Permissions: {', '.join(user['permissions'])}")
        print()

        # Example 6: View DAGs (allowed)
        print("6. View DAGs (allowed for Citizen_Data_Scientist)")
        dags = list_dags(token)
        print(f"   ✓ Retrieved {len(dags)} DAGs")
        print()

        # Example 7: Try to create DAG (should fail - no create_model permission)
        print("7. Try to create DAG (should fail - no create_model permission)")
        try:
            new_dag = create_dag(token, "test-station-02")
            print(f"   ✗ Unexpected success - should have been denied")
        except requests.HTTPError as e:
            if e.response.status_code == 403:
                print(f"   ✓ Access denied as expected (403 Forbidden)")
            else:
                print(f"   ✗ Unexpected error: {e}")
        print()

    except requests.HTTPError as e:
        print(f"   ✗ Error: {e}")
        print()

    # Example 8: Login as Plant Manager
    print("8. Login as Plant Manager")
    try:
        login_response = login("manager", "Manager123!")
        token = login_response["access_token"]
        user = login_response["user"]

        print(f"   ✓ Logged in as: {user['username']}")
        print(f"   ✓ Roles: {', '.join(user['roles'])}")
        print(f"   ✓ Permissions: {', '.join(user['permissions'])}")
        print()

        # Example 9: View DAGs (allowed)
        print("9. View DAGs (allowed for Plant_Manager)")
        dags = list_dags(token)
        print(f"   ✓ Retrieved {len(dags)} DAGs")
        print()

        # Example 10: Try to edit DAG (should fail - no edit_model permission)
        print("10. Try to edit DAG (should fail - no edit_model permission)")
        try:
            response = requests.put(
                f"{BASE_URL}/api/v1/dags/furnace-01/edges",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "operations": [
                        {
                            "operation": "add",
                            "source": "temperature",
                            "target": "pressure",
                        }
                    ]
                },
            )
            response.raise_for_status()
            print(f"   ✗ Unexpected success - should have been denied")
        except requests.HTTPError as e:
            if e.response.status_code == 403:
                print(f"   ✓ Access denied as expected (403 Forbidden)")
            else:
                print(f"   ✗ Unexpected error: {e}")
        print()

    except requests.HTTPError as e:
        print(f"   ✗ Error: {e}")
        print()

    print("=== Examples Complete ===")


if __name__ == "__main__":
    main()
