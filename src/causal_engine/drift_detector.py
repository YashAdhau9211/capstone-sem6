"""Model drift detection for monitoring causal model accuracy degradation."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import UUID, uuid4
import logging

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from src.models.station import StationModel


logger = logging.getLogger(__name__)


@dataclass
class DriftAlert:
    """Alert generated when model drift is detected."""
    
    alert_id: UUID
    station_model_id: UUID
    station_id: str
    current_accuracy: float
    baseline_accuracy: float
    drift_magnitude: float
    metric_type: str  # "mae", "rmse", "r2"
    detected_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelEvaluationResult:
    """Result of model evaluation."""
    
    station_model_id: UUID
    station_id: str
    mae: float
    rmse: float
    r2: float
    evaluated_at: datetime
    sample_size: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class ModelDriftDetector:
    """
    Monitors causal model accuracy and detects drift.
    
    Evaluates model prediction accuracy using MAE, RMSE, and R² metrics,
    comparing current performance against baseline to detect degradation.
    """
    
    def __init__(self, alert_callback: Optional[Callable[[DriftAlert], None]] = None):
        """
        Initialize the drift detector.
        
        Args:
            alert_callback: Optional callback function to invoke when drift is detected.
                           Should accept a DriftAlert and send notifications within 60 seconds.
        """
        self.evaluation_history: Dict[UUID, List[ModelEvaluationResult]] = {}
        self.last_evaluation: Dict[UUID, datetime] = {}
        self.alert_callback = alert_callback
        self.alert_history: List[DriftAlert] = []
        logger.info("ModelDriftDetector initialized")
    
    def evaluate_model(
        self,
        model: StationModel,
        y_true: np.ndarray,
        y_pred: np.ndarray
    ) -> ModelEvaluationResult:
        """
        Evaluate model prediction accuracy using multiple metrics.
        
        Args:
            model: Station model to evaluate
            y_true: True values (ground truth)
            y_pred: Predicted values from the model
            
        Returns:
            ModelEvaluationResult with MAE, RMSE, and R² metrics
            
        Raises:
            ValueError: If input arrays have mismatched shapes or invalid values
        """
        if len(y_true) != len(y_pred):
            raise ValueError(
                f"Shape mismatch: y_true has {len(y_true)} samples, "
                f"y_pred has {len(y_pred)} samples"
            )
        
        if len(y_true) == 0:
            raise ValueError("Cannot evaluate model with empty arrays")
        
        # Check for NaN or infinite values
        if np.any(np.isnan(y_true)) or np.any(np.isnan(y_pred)):
            raise ValueError("Input arrays contain NaN values")
        
        if np.any(np.isinf(y_true)) or np.any(np.isinf(y_pred)):
            raise ValueError("Input arrays contain infinite values")
        
        # Compute metrics
        mae = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        r2 = r2_score(y_true, y_pred)
        
        result = ModelEvaluationResult(
            station_model_id=model.model_id,
            station_id=model.station_id,
            mae=mae,
            rmse=rmse,
            r2=r2,
            evaluated_at=datetime.utcnow(),
            sample_size=len(y_true),
            metadata={
                "model_status": model.status,
                "baseline_accuracy": model.baseline_accuracy
            }
        )
        
        # Store evaluation result
        if model.model_id not in self.evaluation_history:
            self.evaluation_history[model.model_id] = []
        self.evaluation_history[model.model_id].append(result)
        self.last_evaluation[model.model_id] = result.evaluated_at
        
        logger.info(
            f"Evaluated model {model.model_id} for station {model.station_id}: "
            f"MAE={mae:.4f}, RMSE={rmse:.4f}, R²={r2:.4f}"
        )
        
        return result
    
    def detect_drift(
        self,
        model: StationModel,
        current_accuracy: float,
        baseline_accuracy: float,
        metric_type: str = "r2"
    ) -> Optional[DriftAlert]:
        """
        Detect model drift by comparing current vs baseline accuracy.
        
        Drift is detected when accuracy degrades by more than the configured
        threshold (default 10%).
        
        Args:
            model: Station model being evaluated
            current_accuracy: Current model accuracy metric
            baseline_accuracy: Baseline accuracy established during validation
            metric_type: Type of metric being compared ("mae", "rmse", "r2")
            
        Returns:
            DriftAlert if drift detected, None otherwise
            
        Raises:
            ValueError: If accuracy values are invalid
        """
        if baseline_accuracy is None:
            logger.warning(
                f"Cannot detect drift for model {model.model_id}: "
                "baseline accuracy not set"
            )
            return None
        
        # Validate accuracy values based on metric type
        if metric_type == "r2":
            # R² can be negative for very poor models, but typically 0-1
            if current_accuracy > 1.0 or baseline_accuracy > 1.0:
                raise ValueError(f"R² values should not exceed 1.0")
        elif metric_type in ("mae", "rmse"):
            # MAE and RMSE should be non-negative
            if current_accuracy < 0 or baseline_accuracy < 0:
                raise ValueError(f"{metric_type.upper()} values must be non-negative")
        else:
            raise ValueError(
                f"Unknown metric type: {metric_type}. "
                "Must be one of: 'mae', 'rmse', 'r2'"
            )
        
        # Calculate drift magnitude
        # For R², higher is better, so drift = (baseline - current) / baseline
        # For MAE/RMSE, lower is better, so drift = (current - baseline) / baseline
        if metric_type == "r2":
            if baseline_accuracy == 0:
                logger.warning(
                    f"Baseline R² is 0 for model {model.model_id}, "
                    "cannot compute drift magnitude"
                )
                return None
            drift_magnitude = (baseline_accuracy - current_accuracy) / baseline_accuracy
        else:  # mae or rmse
            if baseline_accuracy == 0:
                # If baseline is 0, any non-zero current value is drift
                drift_magnitude = float('inf') if current_accuracy > 0 else 0.0
            else:
                drift_magnitude = (current_accuracy - baseline_accuracy) / baseline_accuracy
        
        # Check if drift exceeds threshold
        drift_threshold = model.config.drift_threshold
        
        if drift_magnitude > drift_threshold:
            alert = DriftAlert(
                alert_id=uuid4(),
                station_model_id=model.model_id,
                station_id=model.station_id,
                current_accuracy=current_accuracy,
                baseline_accuracy=baseline_accuracy,
                drift_magnitude=drift_magnitude,
                metric_type=metric_type,
                detected_at=datetime.utcnow(),
                metadata={
                    "drift_threshold": drift_threshold,
                    "model_status": model.status
                }
            )
            
            logger.warning(
                f"Drift detected for model {model.model_id} (station {model.station_id}): "
                f"{metric_type.upper()} degraded by {drift_magnitude*100:.1f}% "
                f"(threshold: {drift_threshold*100:.1f}%)"
            )
            
            # Store alert in history
            self.alert_history.append(alert)
            
            # Send alert notification if callback is configured
            if self.alert_callback:
                try:
                    self.alert_callback(alert)
                    logger.info(f"Drift alert sent for model {model.model_id}")
                except Exception as e:
                    logger.error(
                        f"Failed to send drift alert for model {model.model_id}: {e}",
                        exc_info=True
                    )
            
            return alert
        
        logger.info(
            f"No drift detected for model {model.model_id}: "
            f"drift magnitude {drift_magnitude*100:.1f}% "
            f"below threshold {drift_threshold*100:.1f}%"
        )
        return None
    
    def should_evaluate(
        self,
        model: StationModel,
        evaluation_frequency: Optional[timedelta] = None
    ) -> bool:
        """
        Check if model should be evaluated based on schedule.
        
        Args:
            model: Station model to check
            evaluation_frequency: How often to evaluate (default: daily)
            
        Returns:
            True if model should be evaluated, False otherwise
        """
        if evaluation_frequency is None:
            evaluation_frequency = timedelta(days=1)
        
        last_eval = self.last_evaluation.get(model.model_id)
        
        if last_eval is None:
            # Never evaluated, should evaluate now
            return True
        
        time_since_eval = datetime.utcnow() - last_eval
        return time_since_eval >= evaluation_frequency
    
    def get_evaluation_history(
        self,
        model_id: UUID,
        limit: Optional[int] = None
    ) -> List[ModelEvaluationResult]:
        """
        Get evaluation history for a model.
        
        Args:
            model_id: Model identifier
            limit: Maximum number of results to return (most recent first)
            
        Returns:
            List of evaluation results, sorted by timestamp (newest first)
        """
        history = self.evaluation_history.get(model_id, [])
        
        # Sort by timestamp descending (newest first)
        sorted_history = sorted(history, key=lambda x: x.evaluated_at, reverse=True)
        
        if limit is not None:
            return sorted_history[:limit]
        
        return sorted_history
    
    def get_last_evaluation_time(self, model_id: UUID) -> Optional[datetime]:
        """
        Get the timestamp of the last evaluation for a model.
        
        Args:
            model_id: Model identifier
            
        Returns:
            Timestamp of last evaluation, or None if never evaluated
        """
        return self.last_evaluation.get(model_id)
    
    def get_alert_history(
        self,
        model_id: Optional[UUID] = None,
        station_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[DriftAlert]:
        """
        Get drift alert history.
        
        Args:
            model_id: Filter by model ID (optional)
            station_id: Filter by station ID (optional)
            limit: Maximum number of alerts to return (most recent first)
            
        Returns:
            List of drift alerts, sorted by timestamp (newest first)
        """
        alerts = self.alert_history
        
        # Apply filters
        if model_id is not None:
            alerts = [a for a in alerts if a.station_model_id == model_id]
        
        if station_id is not None:
            alerts = [a for a in alerts if a.station_id == station_id]
        
        # Sort by timestamp descending (newest first)
        sorted_alerts = sorted(alerts, key=lambda x: x.detected_at, reverse=True)
        
        if limit is not None:
            return sorted_alerts[:limit]
        
        return sorted_alerts
    
    def format_alert_message(self, alert: DriftAlert) -> str:
        """
        Format a drift alert as a human-readable message.
        
        Args:
            alert: Drift alert to format
            
        Returns:
            Formatted alert message string
        """
        return (
            f"Model Drift Alert\n"
            f"=================\n"
            f"Station: {alert.station_id}\n"
            f"Model ID: {alert.station_model_id}\n"
            f"Metric: {alert.metric_type.upper()}\n"
            f"Current Accuracy: {alert.current_accuracy:.4f}\n"
            f"Baseline Accuracy: {alert.baseline_accuracy:.4f}\n"
            f"Drift Magnitude: {alert.drift_magnitude*100:.1f}%\n"
            f"Detected At: {alert.detected_at.isoformat()}\n"
        )
