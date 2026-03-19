"""Example demonstrating nonlinear causal discovery using RESIT algorithm."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd

from src.causal_engine import CausalDiscoveryEngine


def main():
    """Demonstrate nonlinear causal discovery with RESIT."""
    print("=" * 80)
    print("Nonlinear Causal Discovery Example using RESIT")
    print("=" * 80)
    print()

    # Generate synthetic nonlinear causal data
    # Ground truth: X1 -> X2 -> X3 (with nonlinear relationships)
    print("Generating synthetic nonlinear causal data...")
    np.random.seed(42)
    n_samples = 2000

    x1 = np.random.randn(n_samples)
    x2 = np.tanh(0.8 * x1) + np.random.randn(n_samples) * 0.2  # Nonlinear: tanh
    x3 = np.sin(0.6 * x2) + np.random.randn(n_samples) * 0.2  # Nonlinear: sin

    data = pd.DataFrame({"Temperature": x1, "Pressure": x2, "FlowRate": x3})

    print(f"Generated {len(data)} observations with {len(data.columns)} variables")
    print(f"Variables: {', '.join(data.columns)}")
    print()

    # Initialize causal discovery engine
    print("Initializing CausalDiscoveryEngine...")
    engine = CausalDiscoveryEngine(random_state=42, n_bootstrap=50)
    print()

    # Discover nonlinear causal relationships
    print("Discovering nonlinear causal relationships with RESIT...")
    dag = engine.discover_nonlinear(
        data=data,
        station_id="furnace-01",
        created_by="example_user",
        adaptive_sample_size=True,
    )
    print()

    # Display results
    print("=" * 80)
    print("Discovery Results")
    print("=" * 80)
    print(f"Station ID: {dag.station_id}")
    print(f"Algorithm: {dag.algorithm}")
    print(f"Number of nodes: {len(dag.nodes)}")
    print(f"Number of edges: {len(dag.edges)}")
    print(f"Created at: {dag.created_at}")
    print()

    print("Discovered Causal Edges:")
    print("-" * 80)
    for i, edge in enumerate(dag.edges, 1):
        print(f"{i}. {edge.source} -> {edge.target}")
        print(f"   Coefficient: {edge.coefficient:.4f}")
        print(f"   Confidence: {edge.confidence:.4f}")
        print(f"   Edge Type: {edge.edge_type}")
        print(f"   Independence Test: {edge.metadata.get('independence_test', 'N/A')}")
        print()

    # Export to DOT format for visualization
    print("=" * 80)
    print("DAG in DOT Format (for Graphviz)")
    print("=" * 80)
    print(dag.to_dot())
    print()

    # Compare with linear discovery
    print("=" * 80)
    print("Comparison: Linear vs Nonlinear Discovery")
    print("=" * 80)
    print("Discovering linear causal relationships with DirectLiNGAM...")
    linear_dag = engine.discover_linear(
        data=data, station_id="furnace-01", created_by="example_user"
    )
    print()

    print(f"Linear Discovery (DirectLiNGAM): {len(linear_dag.edges)} edges")
    print(f"Nonlinear Discovery (RESIT): {len(dag.edges)} edges")
    print()

    print("Linear edges:")
    for edge in linear_dag.edges:
        print(f"  {edge.source} -> {edge.target} (coef={edge.coefficient:.4f}, conf={edge.confidence:.4f})")
    print()

    print("Nonlinear edges:")
    for edge in dag.edges:
        print(f"  {edge.source} -> {edge.target} (coef={edge.coefficient:.4f}, conf={edge.confidence:.4f})")
    print()

    print("=" * 80)
    print("Example completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
