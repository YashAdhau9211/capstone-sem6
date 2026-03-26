"""Test script to verify optimization endpoints work with mock data."""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_yield_optimization():
    """Test yield optimization endpoint."""
    print("\n=== Testing Yield Optimization ===")
    
    # Login first
    login_data = {"username": "admin", "password": "admin123"}
    login_response = requests.post(f"{BASE_URL}/api/v1/auth/login", data=login_data)
    token = login_response.json().get("token")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Test yield optimization
    data = {
        "station_id": "furnace-01",
        "yield_variable": "yield",
        "energy_variable": "energy_consumption",
        "quality_variable": "quality_score"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/optimization/yield",
        headers=headers,
        json=data
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ SUCCESS!")
        print(f"Station: {result['station_id']}")
        print(f"Yield Variable: {result['yield_variable']}")
        print(f"Recommendations: {len(result['recommendations'])}")
        
        if result['recommendations']:
            print("\nTop Recommendation:")
            rec = result['recommendations'][0]
            print(f"  Variable: {rec['variable']}")
            print(f"  Direction: {rec['direction']}")
            print(f"  Current Value: {rec['current_value']:.2f}")
            print(f"  Recommended Value: {rec['recommended_value']:.2f}")
            print(f"  Expected Improvement: {rec['expected_savings']:.2f}")
            if rec.get('energy_tradeoff'):
                print(f"  Energy Trade-off: {rec['energy_tradeoff']:.2f}")
    else:
        print(f"❌ FAILED!")
        print(f"Error: {response.text}")
    
    return response.status_code == 200


def test_energy_optimization():
    """Test energy optimization endpoint."""
    print("\n=== Testing Energy Optimization ===")
    
    # Login first
    login_data = {"username": "admin", "password": "admin123"}
    login_response = requests.post(f"{BASE_URL}/api/v1/auth/login", data=login_data)
    token = login_response.json().get("token")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Test energy optimization
    data = {
        "station_id": "furnace-01",
        "energy_variable": "energy_consumption"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/optimization/energy",
        headers=headers,
        json=data
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ SUCCESS!")
        print(f"Station: {result['station_id']}")
        print(f"Energy Variable: {result['energy_variable']}")
        print(f"Recommendations: {len(result['recommendations'])}")
        
        if result['recommendations']:
            print("\nTop Recommendation:")
            rec = result['recommendations'][0]
            print(f"  Variable: {rec['variable']}")
            print(f"  Direction: {rec['direction']}")
            print(f"  Current Value: {rec['current_value']:.2f}")
            print(f"  Recommended Value: {rec['recommended_value']:.2f}")
            print(f"  Expected Savings: {rec['expected_savings']:.2f}")
    else:
        print(f"❌ FAILED!")
        print(f"Error: {response.text}")
    
    return response.status_code == 200


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Optimization Endpoints")
    print("=" * 60)
    print("\nMake sure the backend is running:")
    print("python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000")
    print()
    
    try:
        # Check if backend is running
        health = requests.get(f"{BASE_URL}/health", timeout=2)
        if health.status_code != 200:
            print("❌ Backend is not responding correctly")
            exit(1)
    except requests.exceptions.RequestException:
        print("❌ Backend is not running on http://localhost:8000")
        print("Please start the backend first!")
        exit(1)
    
    results = {
        "yield_optimization": test_yield_optimization(),
        "energy_optimization": test_energy_optimization()
    }
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:25s}: {status}")
    
    if all(results.values()):
        print("\n🎉 All optimization tests passed!")
        print("The yield optimization page should now work correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the output above.")
