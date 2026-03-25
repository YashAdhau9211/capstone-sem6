"""Example demonstrating the Alert Suppression System.

This example shows how the alert suppression system identifies causal
relationships between anomalies and suppresses descendant alerts to
focus on root causes.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
from uuid import uuid4

import numpy as np
import pandas as pd

from src.causal_engine.alert_suppression import AlertSuppressionSystem
from src.causal_engine.rca import RCAEngine
from src.models.causal_graph import CausalDAG, CausalEdge
from src.models.rca import Anomaly


def create_example_dag():
    """
    Create an example manufacturing DAG:
    
    Temperature -> Pressure -> Quality
    Temperature -> Viscosity -> Quality
    Speed -> Quality
    """
    return CausalDAG(
        dag_id=uuid4(),
        station_id="furnace-01",
        version=1,
        nodes=["Temperature", "Pressure", "Viscosity", "Speed", "Quality"],
        edges=[
            CausalEdge(
                source="Temperature",
                target="Pressure",
                coefficient=0.75,
                confidence=0.95,
                edge_type="linear"
            ),
            CausalEdge(
                source="Temperature",
                target="Viscosity",
                coefficient=0.60,
                confidence=0.92,
                edge_type="linear"
            ),
            CausalEdge(
                source="Pressure",
                target="Quality",
                coefficient=0.80,
                confidence=0.94,
                edge_type="linear"
            ),
            CausalEdge(
                source="Viscosity",
                target="Quality",
                coefficient=0.65,
                confidence=0.90,
                edge_type="linear"
            ),
            CausalEdge(
                source="Speed",
                target="Quality",
                coefficient=0.70,
                confidence=0.93,
                edge_type="linear"
            )
        ],
        algorithm="DirectLiNGAM",
        created_at=datetime.now(),
        created_by="system"
    )


def create_sample_data():
    """Create sample time-series data for the manufacturing process."""
    np.random.seed(42)
    n_samples = 1000
    
    # Generate correlated data
    Temperature = np.random.randn(n_samples) * 10 + 100
    Pressure = 0.75 * Temperature + np.random.randn(n_samples) * 5 + 50
    Viscosity = 0.60 * Temperature + np.random.randn(n_samples) * 3 + 20
    Speed = np.random.randn(n_samples) * 5 + 50
    Quality = (
        0.80 * Pressure +
        0.65 * Viscosity +
        0.70 * Speed +
        np.random.randn(n_samples) * 2
    )
    
    return pd.DataFrame({
        "Temperature": Temperature,
        "Pressure": Pressure,
        "Viscosity": Viscosity,
        "Speed": Speed,
        "Quality": Quality
    })


def main():
    """Run alert suppression example."""
    print("=" * 80)
    print("Alert Suppression System Example")
    print("=" * 80)
    print()
    
    # Create DAG and data
    dag = create_example_dag()
    data = create_sample_data()
    
    print("Manufacturing Process DAG:")
    print("  Temperature -> Pressure -> Quality")
    print("  Temperature -> Viscosity -> Quality")
    print("  Speed -> Quality")
    print()
    
    # Scenario: Multiple anomalies detected
    print("Scenario: Multiple anomalies detected simultaneously")
    print("-" * 80)
    
    anomalies = [
        Anomaly(
            anomaly_id=uuid4(),
            station_id="furnace-01",
            variable="Temperature",
            timestamp=datetime.now(),
            value=125.0,
            deviation=4.5,
            severity="critical",
            metadata={"description": "Temperature spike detected"}
        ),
        Anomaly(
            anomaly_id=uuid4(),
            station_id="furnace-01",
            variable="Pressure",
            timestamp=datetime.now(),
            value=145.0,
            deviation=3.8,
            severity="high",
            metadata={"description": "Pressure anomaly detected"}
        ),
        Anomaly(
            anomaly_id=uuid4(),
            station_id="furnace-01",
            variable="Quality",
            timestamp=datetime.now(),
            value=85.0,
            deviation=5.2,
            severity="critical",
            metadata={"description": "Quality defect detected"}
        )
    ]
    
    print(f"\nDetected {len(anomalies)} anomalies:")
    for i, anomaly in enumerate(anomalies, 1):
        print(f"  {i}. {anomaly.variable}: {anomaly.severity} "
              f"(deviation: {anomaly.deviation:.1f}σ)")
    print()
    
    # Apply alert suppression
    print("Applying Alert Suppression...")
    print("-" * 80)
    
    suppression_system = AlertSuppressionSystem()
    root_causes, suppressed = suppression_system.suppress_alerts(anomalies, dag)
    
    print(f"\nRoot Cause Alerts (to be sent): {len(root_causes)}")
    for i, anomaly in enumerate(root_causes, 1):
        print(f"  {i}. {anomaly.variable}: {anomaly.severity}")
    
    print(f"\nSuppressed Alerts (secondary list): {len(suppressed)}")
    for i, anomaly in enumerate(suppressed, 1):
        print(f"  {i}. {anomaly.variable}: {anomaly.severity}")
    print()
    
    # View suppressed alert details
    print("Suppressed Alert Details:")
    print("-" * 80)
    
    suppressed_details = suppression_system.get_suppressed_alerts(
        suppressed_anomalies=suppressed,
        all_anomalies=anomalies,
        dag=dag
    )
    
    for detail in suppressed_details:
        anomaly = detail["anomaly"]
        print(f"\nSuppressed: {anomaly.variable}")
        print(f"  Suppressed by: {[a.variable for a in detail['suppressed_by']]}")
        print(f"  Causal paths:")
        for path_info in detail["causal_paths"]:
            path_str = " -> ".join(path_info["path"])
            print(f"    {path_str}")
    print()
    
    # Generate RCA reports with suppression
    print("Generating RCA Reports with Alert Suppression:")
    print("-" * 80)
    
    rca_engine = RCAEngine()
    reports = rca_engine.analyze_anomalies_with_suppression(
        anomalies=anomalies,
        dag=dag,
        data=data,
        max_root_causes=3
    )
    
    print(f"\nGenerated {len(reports)} RCA report(s):")
    
    for i, report in enumerate(reports, 1):
        print(f"\n--- Report {i}: {report.anomaly.variable} ---")
        print(f"Anomaly: {report.anomaly.variable} ({report.anomaly.severity})")
        print(f"Root Causes (top {len(report.root_causes)}):")
        
        for j, root_cause in enumerate(report.root_causes, 1):
            path_str = " -> ".join(root_cause.causal_path)
            print(f"  {j}. {root_cause.variable}")
            print(f"     Attribution: {root_cause.attribution_score:.3f}")
            print(f"     Confidence: [{root_cause.confidence_interval[0]:.3f}, "
                  f"{root_cause.confidence_interval[1]:.3f}]")
            print(f"     Path: {path_str}")
        
        if report.suppressed_alerts:
            print(f"\nSuppressed Descendant Alerts: {len(report.suppressed_alerts)}")
            for suppressed_anomaly in report.suppressed_alerts:
                print(f"  - {suppressed_anomaly.variable} ({suppressed_anomaly.severity})")
    
    print()
    print("=" * 80)
    print("Summary:")
    print("=" * 80)
    print(f"Total anomalies detected: {len(anomalies)}")
    print(f"Root cause alerts generated: {len(root_causes)}")
    print(f"Alerts suppressed: {len(suppressed)}")
    print(f"Alert reduction: {len(suppressed) / len(anomalies) * 100:.1f}%")
    print()
    print("Benefits:")
    print("  ✓ Operators focus on root causes (Temperature)")
    print("  ✓ Reduced alert fatigue from cascading symptoms")
    print("  ✓ Suppressed alerts still available for investigation")
    print("  ✓ Causal paths explain suppression decisions")
    print()


if __name__ == "__main__":
    main()
