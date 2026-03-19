"""Example usage of Redis caching layer for the Causal AI Manufacturing Platform.

This example demonstrates how to use the RedisCacheManager for:
- Connection status caching (100ms TTL) - Requirement 1.8
- DAG and model parameter caching (5-minute TTL)
- Query result caching - Requirements 11.1, 11.2
- Session management
"""

import time
from config.settings import settings
from src.utils.redis_cache import RedisCacheManager


def main():
    """Demonstrate Redis caching functionality."""
    
    # Initialize Redis cache manager
    cache = RedisCacheManager(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        password=settings.redis_password,
    )
    
    if not cache.is_available:
        print("Warning: Redis is not available. Operating without cache.")
        return
    
    print("Redis cache manager initialized successfully\n")
    
    # Example 1: Connection Status Caching (100ms TTL)
    # Requirement 1.8: Report connection status within 100 milliseconds
    print("=== Example 1: Connection Status Caching ===")
    connection_status = {
        "system_id": "PLC-001",
        "connected": True,
        "last_check": "2024-01-15T10:30:00Z",
        "latency_ms": 45,
    }
    
    cache.set_connection_status("PLC-001", connection_status)
    print(f"Cached connection status: {connection_status}")
    
    # Retrieve within 100ms window
    cached_status = cache.get_connection_status("PLC-001")
    print(f"Retrieved from cache: {cached_status}")
    
    # Wait for TTL expiration (100ms)
    time.sleep(0.15)
    expired_status = cache.get_connection_status("PLC-001")
    print(f"After TTL expiration: {expired_status}\n")
    
    # Example 2: DAG Caching (5-minute TTL)
    print("=== Example 2: DAG Caching ===")
    dag_data = {
        "station_id": "furnace-01",
        "nodes": ["temperature", "pressure", "energy_consumption", "yield"],
        "edges": [
            ["temperature", "energy_consumption"],
            ["pressure", "yield"],
            ["temperature", "yield"],
        ],
        "coefficients": {
            "temperature->energy_consumption": 0.85,
            "pressure->yield": 0.62,
            "temperature->yield": 0.43,
        },
    }
    
    cache.set_dag("furnace-01", dag_data)
    print(f"Cached DAG for furnace-01")
    
    cached_dag = cache.get_dag("furnace-01")
    print(f"Retrieved DAG: {cached_dag['station_id']}")
    print(f"  Nodes: {len(cached_dag['nodes'])}")
    print(f"  Edges: {len(cached_dag['edges'])}\n")
    
    # Example 3: Model Parameter Caching (5-minute TTL)
    print("=== Example 3: Model Parameter Caching ===")
    model_params = {
        "model_id": "causal_model_v1",
        "algorithm": "DirectLiNGAM",
        "learning_rate": 0.01,
        "max_iterations": 1000,
        "convergence_threshold": 1e-6,
    }
    
    cache.set_model_params("causal_model_v1", model_params)
    print(f"Cached model parameters")
    
    cached_params = cache.get_model_params("causal_model_v1")
    print(f"Retrieved parameters: {cached_params['algorithm']}\n")
    
    # Example 4: Query Result Caching (configurable TTL)
    # Requirements 11.1, 11.2: Dashboard query performance
    print("=== Example 4: Query Result Caching ===")
    query_result = {
        "query_id": "simulation_001",
        "intervention": {"temperature": 1500},
        "predicted_outcomes": {
            "energy_consumption": 245.3,
            "yield": 0.94,
        },
        "confidence_intervals": {
            "energy_consumption": [240.1, 250.5],
            "yield": [0.92, 0.96],
        },
    }
    
    # Cache with default 5-minute TTL
    cache.set_query_result("simulation_001", query_result)
    print(f"Cached query result for simulation_001")
    
    # Cache with custom 1-minute TTL for frequently changing data
    cache.set_query_result("realtime_query", query_result, ttl=60)
    print(f"Cached realtime query with 60s TTL")
    
    cached_result = cache.get_query_result("simulation_001")
    print(f"Retrieved result: {cached_result['intervention']}\n")
    
    # Example 5: Session Management
    print("=== Example 5: Session Management ===")
    session_data = {
        "user_id": "engineer_001",
        "role": "Process_Engineer",
        "login_time": "2024-01-15T10:00:00Z",
        "permissions": ["view_dags", "edit_dags", "run_simulations"],
    }
    
    cache.set_session("session_abc123", session_data)
    print(f"Created session for {session_data['user_id']}")
    
    cached_session = cache.get_session("session_abc123")
    print(f"Retrieved session: {cached_session['role']}")
    
    # Refresh session TTL
    cache.refresh_session("session_abc123")
    print(f"Refreshed session TTL\n")
    
    # Example 6: Cache Statistics
    print("=== Example 6: Cache Statistics ===")
    stats = cache.get_stats()
    if stats:
        print(f"Connected clients: {stats['connected_clients']}")
        print(f"Memory used: {stats['used_memory']}")
        print(f"Cache hits: {stats['keyspace_hits']}")
        print(f"Cache misses: {stats['keyspace_misses']}")
        
        if stats['keyspace_hits'] + stats['keyspace_misses'] > 0:
            hit_rate = stats['keyspace_hits'] / (stats['keyspace_hits'] + stats['keyspace_misses'])
            print(f"Hit rate: {hit_rate:.2%}\n")
    
    # Cleanup
    cache.delete_session("session_abc123")
    print("Session deleted")
    
    cache.close()
    print("Redis connection closed")


if __name__ == "__main__":
    main()
