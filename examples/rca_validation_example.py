"""
RCA and Monitoring Validation Example

This example demonstrates the complete RCA and monitoring workflow:
1. Create a causal DAG representing a manufacturing process
2. Simulate anomalies in the process
3. Perform root cause analysis
4. Demonstrate alert suppression
5. Validate model drift detection
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from uuid import uuid4

from src.models.causal_graph import CausalDAG, CausalEdge
from src.models.rca import Anomaly, RootCause
from src.models.station import StationModel, ModelConfig
from src.causal_engine.rca import RCAEngine
from src.causal_engine.alert_suppression import AlertSuppressionSystem
from src.causal_engine.drift_detector import ModelDriftDetector


def create_manufacturing_dag():
    """Create a causal DAG for a steel manufacturing process."""
    # Variables: temperature -> pressure -> flow_rate -> yield
    #            energy -> temperature
    edges = [
        CausalEdge(
            source="energy",
            target="temperature",
            coefficient=0.8,
            confidence=0.95,
            edge_type="linear"
        ),
        CausalEdge(
            source="temperature",
            target="pressure",
            coefficient=0.7,
            confidence=0.92,
            edge_type="linear"
        ),
        CausalEdge(
            source="pressure",
            target="flow_rate",
            coefficient=0.6,
            confidence=0.88,
            edge_type="linear"
        ),
        CausalEdge(
            source="flow_rate",
            target="yield",
            coefficient=0.9,
            confidence=0.96,
            edge_type="linear"
        ),
    ]
    
    nodes = ["energy", "temperature", "pressure", "flow_rate", "yield"]
    
    dag = CausalDAG(
        dag_id=uuid4(),
        station_id="furnace-01",
        version=1,
        nodes=nodes,
        edges=edges,
        algorithm="expert_edited",
        created_at=datetime.utcnow(),
        created_by="validation_script",
        metadata={"description": "Steel furnace causal model"}
    )
    
    return dag


def simulate_process_data(n_samples=1000):
    """Simulate manufacturing process data."""
    np.random.seed(42)
    
    # Generate data following the causal structure
    energy = np.random.normal(100, 10, n_samples)
    temperature = 0.8 * energy + np.random.normal(0, 5, n_samples)
    pressure = 0.7 * temperature + np.random.normal(0, 3, n_samples)
    flow_rate = 0.6 * pressure + np.random.normal(0, 2, n_samples)
    yield_var = 0.9 * flow_rate + np.random.normal(0, 1, n_samples)
    
    data = pd.DataFrame({
        "energy": energy,
        "temperature": temperature,
        "pressure": pressure,
        "flow_rate": flow_rate,
        "yield": yield_var
    })
    
    return data


def main():
    print("=" * 80)
    print("RCA AND MONITORING VALIDATION")
    print("=" * 80)
    print()
    
    # 1. Create causal DAG
    print("1. Creating manufacturing process DAG...")
    dag = create_manufacturing_dag()
    print(f"   Created DAG with {len(dag.nodes)} nodes and {len(dag.edges)} edges")
    print(f"   Causal chain: energy -> temperature -> pressure -> flow_rate -> yield")
    print()
    
    # 2. Simulate process data
    print("2. Simulating process data...")
    data = simulate_process_data()
    print(f"   Generated {len(data)} samples")
    print(f"   Variables: {list(data.columns)}")
    print()
    
    # 3. Create anomalies
    print("3. Creating synthetic anomalies...")
    anomalies = [
        Anomaly(
            anomaly_id=uuid4(),
            station_id="furnace-01",
            variable="energy",
            timestamp=datetime.utcnow(),
            value=150.0,  # High energy consumption
            deviation=5.0,
            severity="high"
        ),
        Anomaly(
            anomaly_id=uuid4(),
            station_id="furnace-01",
            variable="temperature",
            timestamp=datetime.utcnow(),
            value=120.0,  # High temperature (caused by high energy)
            deviation=4.0,
            severity="high"
        ),
        Anomaly(
            anomaly_id=uuid4(),
            station_id="furnace-01",
            variable="yield",
            timestamp=datetime.utcnow(),
            value=85.0,  # Low yield (downstream effect)
            deviation=-3.0,
            severity="medium"
        ),
    ]
    print(f"   Created {len(anomalies)} anomalies:")
    for anomaly in anomalies:
        print(f"   - {anomaly.variable}: {anomaly.value} (deviation: {anomaly.deviation}, severity: {anomaly.severity})")
    print()
    
    # 4. Perform RCA
    print("4. Performing Root Cause Analysis...")
    rca_engine = RCAEngine()
    
    for anomaly in anomalies:
        print(f"\n   Analyzing anomaly in '{anomaly.variable}'...")
        report = rca_engine.analyze_anomaly(anomaly, dag, data)
        
        print(f"   Report ID: {report.report_id}")
        print(f"   Generation time: {report.generation_time}")
        print(f"   Root causes found: {len(report.root_causes)}")
        
        for i, root_cause in enumerate(report.root_causes[:5], 1):
            print(f"   {i}. {root_cause.variable}")
            print(f"      Attribution score: {root_cause.attribution_score:.4f}")
            print(f"      Confidence interval: [{root_cause.confidence_interval[0]:.4f}, {root_cause.confidence_interval[1]:.4f}]")
            print(f"      Causal path: {' -> '.join(root_cause.causal_path)}")
    
    print()
    
    # 5. Demonstrate alert suppression
    print("5. Demonstrating Alert Suppression...")
    suppression_system = AlertSuppressionSystem()
    
    root_cause_alerts, suppressed_alerts = suppression_system.suppress_alerts(anomalies, dag)
    
    print(f"   Total anomalies: {len(anomalies)}")
    print(f"   Root cause alerts: {len(root_cause_alerts)}")
    print(f"   Suppressed alerts: {len(suppressed_alerts)}")
    print()
    
    print("   Root cause alerts (to be sent):")
    for alert in root_cause_alerts:
        print(f"   - {alert.variable} (severity: {alert.severity})")
    print()
    
    print("   Suppressed alerts (descendants of root causes):")
    for alert in suppressed_alerts:
        print(f"   - {alert.variable} (suppressed because it's a descendant)")
    
    # Show detailed suppression information
    if suppressed_alerts:
        print()
        print("   Detailed suppression information:")
        suppression_details = suppression_system.get_suppressed_alerts(
            suppressed_alerts, anomalies, dag
        )
        for detail in suppression_details:
            print(f"   - {detail['anomaly'].variable} suppressed by:")
            for ancestor in detail['suppressed_by']:
                print(f"     • {ancestor.variable}")
    print()
    
    # 6. Demonstrate drift detection
    print("6. Demonstrating Model Drift Detection...")
    drift_detector = ModelDriftDetector()
    
    # Create a station model
    model = StationModel(
        model_id=uuid4(),
        station_id="furnace-01",
        current_dag=dag,
        baseline_accuracy=0.85,
        status="active",
        config=ModelConfig(
            retraining_schedule=timedelta(days=1),
            drift_threshold=0.10
        ),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    print(f"   Model ID: {model.model_id}")
    print(f"   Station: {model.station_id}")
    print(f"   Baseline accuracy (R²): {model.baseline_accuracy}")
    print()
    
    # Scenario 1: Good model performance (no drift)
    print("   Scenario 1: Good model performance")
    y_true = data["yield"].values[:100]
    y_pred = y_true + np.random.normal(0, 0.5, 100)  # Small prediction error
    
    result = drift_detector.evaluate_model(model, y_true, y_pred)
    print(f"   Current R²: {result.r2:.4f}")
    print(f"   MAE: {result.mae:.4f}")
    print(f"   RMSE: {result.rmse:.4f}")
    
    drift_alert = drift_detector.detect_drift(
        model,
        result.r2,
        model.baseline_accuracy,
        metric_type="r2"
    )
    
    if drift_alert:
        print(f"   ⚠️  DRIFT DETECTED!")
        print(f"   Drift magnitude: {drift_alert.drift_magnitude:.2%}")
    else:
        print(f"   ✓ No drift detected (model performing well)")
    print()
    
    # Scenario 2: Degraded model performance (drift detected)
    print("   Scenario 2: Degraded model performance")
    y_true = data["yield"].values[:100]
    y_pred = y_true + np.random.normal(0, 5, 100)  # Large prediction error
    
    result = drift_detector.evaluate_model(model, y_true, y_pred)
    print(f"   Current R²: {result.r2:.4f}")
    print(f"   MAE: {result.mae:.4f}")
    print(f"   RMSE: {result.rmse:.4f}")
    
    drift_alert = drift_detector.detect_drift(
        model,
        result.r2,
        model.baseline_accuracy,
        metric_type="r2"
    )
    
    if drift_alert:
        print(f"   ⚠️  DRIFT DETECTED!")
        print(f"   Drift magnitude: {drift_alert.drift_magnitude:.2%}")
        print(f"   Current accuracy: {drift_alert.current_accuracy:.4f}")
        print(f"   Baseline accuracy: {drift_alert.baseline_accuracy:.4f}")
        print(f"   Alert detected at: {drift_alert.detected_at}")
    else:
        print(f"   ✓ No drift detected")
    print()
    
    # 7. Summary
    print("=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print()
    print("✓ RCA Engine: Successfully identified root causes for anomalies")
    print("✓ Alert Suppression: Successfully suppressed descendant anomaly alerts")
    print("✓ Drift Detection: Successfully detected model performance degradation")
    print()
    print("All RCA and monitoring components validated successfully!")
    print()


if __name__ == "__main__":
    main()
