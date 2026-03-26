"""Quick test script to verify all API endpoints are working with mock data."""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint."""
    print("\n=== Testing Health Endpoint ===")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_login():
    """Test login endpoint."""
    print("\n=== Testing Login Endpoint ===")
    data = {
        "username": "admin",
        "password": "admin123"
    }
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", data=data)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    return response.status_code == 200, result.get("token")

def test_models(token):
    """Test models endpoint."""
    print("\n=== Testing Models Endpoint ===")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/v1/models", headers=headers)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    return response.status_code == 200

def test_dags(token):
    """Test DAGs endpoint."""
    print("\n=== Testing DAGs Endpoint ===")
    headers = {"Authorization": f"Bearer {token}"}
    
    # List all DAGs
    response = requests.get(f"{BASE_URL}/api/v1/dags", headers=headers)
    print(f"List DAGs Status: {response.status_code}")
    result = response.json()
    print(f"Found {len(result)} DAGs")
    
    # Get specific DAG
    if result:
        dag_id = result[0]["station_id"]
        response = requests.get(f"{BASE_URL}/api/v1/dags/{dag_id}", headers=headers)
        print(f"Get DAG Status: {response.status_code}")
        dag_result = response.json()
        print(f"DAG has {len(dag_result['nodes'])} nodes and {len(dag_result['edges'])} edges")
    
    return response.status_code == 200

def test_simulation(token):
    """Test simulation endpoint."""
    print("\n=== Testing Simulation Endpoint ===")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    data = {
        "station_id": "furnace-01",
        "interventions": {
            "temperature": 850.0
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/simulation/counterfactual", 
                            headers=headers, json=data)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Factual values: {list(result['factual'].keys())}")
        print(f"Counterfactual values: {list(result['counterfactual'].keys())}")
    else:
        print(f"Error: {response.text}")
    
    return response.status_code == 200

def test_rca(token):
    """Test RCA endpoint."""
    print("\n=== Testing RCA Endpoint ===")
    headers = {"Authorization": f"Bearer {token}"}
    
    # List RCA reports
    response = requests.get(f"{BASE_URL}/api/v1/rca", headers=headers)
    print(f"List RCA Status: {response.status_code}")
    result = response.json()
    print(f"Found {len(result)} RCA reports")
    
    # Get specific RCA report
    response = requests.get(f"{BASE_URL}/api/v1/rca/anomaly-001", headers=headers)
    print(f"Get RCA Status: {response.status_code}")
    if response.status_code == 200:
        rca_result = response.json()
        print(f"RCA has {len(rca_result['root_causes'])} root causes")
    
    return response.status_code == 200

def test_optimization(token):
    """Test optimization endpoints."""
    print("\n=== Testing Optimization Endpoints ===")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # Energy optimization
    data = {
        "station_id": "furnace-01",
        "energy_variable": "energy_consumption"
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/optimization/energy", 
                            headers=headers, json=data)
    print(f"Energy Optimization Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Found {len(result['recommendations'])} energy recommendations")
    else:
        print(f"Error: {response.text}")
    
    return response.status_code == 200

def main():
    """Run all tests."""
    print("=" * 60)
    print("API Endpoint Testing")
    print("=" * 60)
    
    results = {}
    
    # Test health
    results["health"] = test_health()
    
    # Test login and get token
    login_success, token = test_login()
    results["login"] = login_success
    
    if not token:
        print("\n❌ Login failed - cannot continue with authenticated tests")
        return
    
    # Test authenticated endpoints
    results["models"] = test_models(token)
    results["dags"] = test_dags(token)
    results["simulation"] = test_simulation(token)
    results["rca"] = test_rca(token)
    results["optimization"] = test_optimization(token)
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for endpoint, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{endpoint:20s}: {status}")
    
    all_passed = all(results.values())
    print("\n" + ("=" * 60))
    if all_passed:
        print("🎉 All tests passed! Backend is ready for demo.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    print("=" * 60)

if __name__ == "__main__":
    main()
