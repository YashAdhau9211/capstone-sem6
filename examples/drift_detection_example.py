"""Example demonstrating model drift detection functionality."""

import numpy as np
from datetime import datetime, timedelta
from uuid import uuid4

from src.causal_engine.drift_detector import ModelDriftDetector, DriftAlert
from src.causal_engine.drift_scheduler import DriftEvaluationScheduler
from src.models.station import StationModel, ModelConfig


def alert_notification_callback(alert: DriftAlert):
    """
    Callback function to handle drift alerts.
    
    In production, this would send notifications via email, SMS, or webhooks
    within 60 seconds of drift detection.
    """
    print("\n" + "="*70)
    print("DRIFT ALERT NOTIFICATION")
    print("="*70)
    print(f"Station: {alert.station_id}")
    print(f"Model ID: {alert.station_model_id}")
    print(f"Metric: {alert.metric_type.upper()}")
    print(f"Current Accuracy: {alert.current_accuracy:.4f}")
    print(f"Baseline Accuracy: {alert.baseline_accuracy:.4f}")
    print(f"Drift Magnitude: {alert.drift_magnitude*100:.1f}%")
    print(f"Detected At: {alert.detected_at.isoformat()}")
    print("="*70 + "\n")


def simulate_model_evaluation(model: StationModel, detector: ModelDriftDetector):
    """
    Simulate evaluating a model's prediction accuracy.
    
    In production, this would:
    1. Load test data from the time-series database
    2. Generate predictions using the causal model
    3. Compute accuracy metrics (MAE, RMSE, R²)
    4. Check for drift against baseline
    """
    print(f"\nEvaluating model for station: {model.station_id}")
    
    # Simulate ground truth and predictions
    # In production, these would come from actual data and model predictions
    y_true = np.random.randn(1000) * 10 + 50
    
    # Simulate degraded model performance (adding noise)
    noise_level = 5.0  # Higher noise = worse predictions
    y_pred = y_true + np.random.randn(1000) * noise_level
    
    # Evaluate model
    result = detector.evaluate_model(model, y_true, y_pred)
    
    print(f"  MAE: {result.mae:.4f}")
    print(f"  RMSE: {result.rmse:.4f}")
    print(f"  R²: {result.r2:.4f}")
    print(f"  Sample Size: {result.sample_size}")
    
    # Check for drift using R² metric
    if model.baseline_accuracy is not None:
        alert = detector.detect_drift(
            model,
            current_accuracy=result.r2,
            baseline_accuracy=model.baseline_accuracy,
            metric_type="r2"
        )
        
        if alert:
            print(f"  ⚠️  DRIFT DETECTED: {alert.drift_magnitude*100:.1f}% degradation")
        else:
            print(f"  ✓ No drift detected")
    
    return result


def main():
    """Demonstrate model drift detection functionality."""
    
    print("="*70)
    print("Model Drift Detection Example")
    print("="*70)
    
    # Create drift detector with alert callback
    detector = ModelDriftDetector(alert_callback=alert_notification_callback)
    
    # Create sample station models
    models = [
        StationModel(
            model_id=uuid4(),
            station_id="furnace-01",
            current_dag=None,
            baseline_accuracy=0.92,  # High baseline accuracy
            status="active",
            config=ModelConfig(
                retraining_schedule=timedelta(days=7),
                drift_threshold=0.10  # 10% degradation threshold
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
        StationModel(
            model_id=uuid4(),
            station_id="mill-01",
            current_dag=None,
            baseline_accuracy=0.85,
            status="active",
            config=ModelConfig(
                retraining_schedule=timedelta(days=7),
                drift_threshold=0.10
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
        StationModel(
            model_id=uuid4(),
            station_id="anneal-01",
            current_dag=None,
            baseline_accuracy=0.88,
            status="active",
            config=ModelConfig(
                retraining_schedule=timedelta(days=7),
                drift_threshold=0.15  # More tolerant threshold
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    ]
    
    # Example 1: Manual evaluation and drift detection
    print("\n" + "="*70)
    print("Example 1: Manual Evaluation and Drift Detection")
    print("="*70)
    
    for model in models:
        simulate_model_evaluation(model, detector)
    
    # Example 2: View evaluation history
    print("\n" + "="*70)
    print("Example 2: Evaluation History")
    print("="*70)
    
    for model in models:
        history = detector.get_evaluation_history(model.model_id, limit=1)
        if history:
            result = history[0]
            print(f"\n{model.station_id}:")
            print(f"  Last Evaluated: {result.evaluated_at.isoformat()}")
            print(f"  R²: {result.r2:.4f}")
    
    # Example 3: View drift alert history
    print("\n" + "="*70)
    print("Example 3: Drift Alert History")
    print("="*70)
    
    alerts = detector.get_alert_history()
    print(f"\nTotal alerts generated: {len(alerts)}")
    
    for alert in alerts:
        print(f"\n  Station: {alert.station_id}")
        print(f"  Drift: {alert.drift_magnitude*100:.1f}%")
        print(f"  Detected: {alert.detected_at.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Example 4: Scheduled evaluation
    print("\n" + "="*70)
    print("Example 4: Scheduled Evaluation")
    print("="*70)
    
    # Create scheduler
    scheduler = DriftEvaluationScheduler(
        drift_detector=detector,
        default_frequency=timedelta(days=1)
    )
    
    # Schedule models for daily evaluation
    for model in models:
        scheduler.schedule_model(
            model,
            evaluation_callback=lambda m: simulate_model_evaluation(m, detector),
            frequency=timedelta(days=1)
        )
    
    # View scheduled models
    scheduled = scheduler.get_scheduled_models()
    print(f"\nScheduled {len(scheduled)} models for drift evaluation:")
    for info in scheduled:
        print(f"\n  Station: {info['station_id']}")
        print(f"  Frequency: {info['frequency']}")
        print(f"  Status: {info['status']}")
        print(f"  Last Evaluation: {info['last_evaluation']}")
    
    # Example 5: Manual trigger
    print("\n" + "="*70)
    print("Example 5: Manual Trigger")
    print("="*70)
    
    print("\nManually triggering evaluation for furnace-01...")
    scheduler.trigger_evaluation(models[0].model_id)
    
    # Example 6: Format alert message
    print("\n" + "="*70)
    print("Example 6: Formatted Alert Message")
    print("="*70)
    
    alerts = detector.get_alert_history(limit=1)
    if alerts:
        message = detector.format_alert_message(alerts[0])
        print("\n" + message)
    
    print("\n" + "="*70)
    print("Example Complete")
    print("="*70)
    print("\nKey Features Demonstrated:")
    print("  ✓ Model evaluation with MAE, RMSE, R² metrics")
    print("  ✓ Drift detection with configurable thresholds")
    print("  ✓ Alert generation and notification callbacks")
    print("  ✓ Evaluation history tracking")
    print("  ✓ Scheduled evaluations (daily, configurable)")
    print("  ✓ Manual evaluation triggers")
    print("  ✓ Alert history and reporting")
    print("\nProduction Deployment Notes:")
    print("  • Configure alert_callback to send email/SMS/webhooks")
    print("  • Start scheduler with scheduler.start()")
    print("  • Integrate with time-series database for test data")
    print("  • Integrate with causal inference engine for predictions")
    print("  • Store alerts in PostgreSQL for audit trail")
    print("  • Monitor scheduler health and uptime")


if __name__ == "__main__":
    main()
