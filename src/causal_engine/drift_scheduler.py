"""Scheduler for automated model drift evaluation."""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional
from uuid import UUID

from src.models.station import StationModel
from src.causal_engine.drift_detector import ModelDriftDetector


logger = logging.getLogger(__name__)


class DriftEvaluationScheduler:
    """
    Scheduler for automated drift evaluation of station models.
    
    Supports cron-like scheduling with configurable evaluation frequency.
    Tracks last evaluation timestamp per model to avoid redundant evaluations.
    """
    
    def __init__(
        self,
        drift_detector: ModelDriftDetector,
        default_frequency: timedelta = timedelta(days=1)
    ):
        """
        Initialize the drift evaluation scheduler.
        
        Args:
            drift_detector: ModelDriftDetector instance to use for evaluations
            default_frequency: Default evaluation frequency (default: daily)
        """
        self.drift_detector = drift_detector
        self.default_frequency = default_frequency
        self.scheduled_models: Dict[UUID, StationModel] = {}
        self.model_frequencies: Dict[UUID, timedelta] = {}
        self.evaluation_callbacks: Dict[UUID, Callable] = {}
        
        self._running = False
        self._scheduler_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        logger.info(
            f"DriftEvaluationScheduler initialized with default frequency: "
            f"{default_frequency}"
        )
    
    def schedule_model(
        self,
        model: StationModel,
        evaluation_callback: Callable[[StationModel], None],
        frequency: Optional[timedelta] = None
    ) -> None:
        """
        Schedule a model for periodic drift evaluation.
        
        Args:
            model: Station model to schedule
            evaluation_callback: Callback function to invoke for evaluation.
                                Should accept the model and perform evaluation.
            frequency: Evaluation frequency (default: use scheduler default)
        """
        if frequency is None:
            frequency = self.default_frequency
        
        self.scheduled_models[model.model_id] = model
        self.model_frequencies[model.model_id] = frequency
        self.evaluation_callbacks[model.model_id] = evaluation_callback
        
        logger.info(
            f"Scheduled model {model.model_id} (station {model.station_id}) "
            f"for evaluation every {frequency}"
        )
    
    def unschedule_model(self, model_id: UUID) -> None:
        """
        Remove a model from the evaluation schedule.
        
        Args:
            model_id: Model identifier to unschedule
        """
        if model_id in self.scheduled_models:
            station_id = self.scheduled_models[model_id].station_id
            del self.scheduled_models[model_id]
            del self.model_frequencies[model_id]
            del self.evaluation_callbacks[model_id]
            
            logger.info(
                f"Unscheduled model {model_id} (station {station_id}) "
                "from drift evaluation"
            )
        else:
            logger.warning(f"Model {model_id} not found in schedule")
    
    def update_frequency(self, model_id: UUID, frequency: timedelta) -> None:
        """
        Update the evaluation frequency for a scheduled model.
        
        Args:
            model_id: Model identifier
            frequency: New evaluation frequency
        """
        if model_id in self.scheduled_models:
            self.model_frequencies[model_id] = frequency
            station_id = self.scheduled_models[model_id].station_id
            logger.info(
                f"Updated evaluation frequency for model {model_id} "
                f"(station {station_id}) to {frequency}"
            )
        else:
            logger.warning(f"Model {model_id} not found in schedule")
    
    def start(self, check_interval: timedelta = timedelta(minutes=5)) -> None:
        """
        Start the scheduler in a background thread.
        
        Args:
            check_interval: How often to check for models needing evaluation
        """
        if self._running:
            logger.warning("Scheduler is already running")
            return
        
        self._running = True
        self._stop_event.clear()
        
        self._scheduler_thread = threading.Thread(
            target=self._run_scheduler,
            args=(check_interval,),
            daemon=True,
            name="DriftEvaluationScheduler"
        )
        self._scheduler_thread.start()
        
        logger.info(
            f"Drift evaluation scheduler started with check interval: {check_interval}"
        )
    
    def stop(self, timeout: float = 10.0) -> None:
        """
        Stop the scheduler and wait for the background thread to finish.
        
        Args:
            timeout: Maximum time to wait for thread to stop (seconds)
        """
        if not self._running:
            logger.warning("Scheduler is not running")
            return
        
        logger.info("Stopping drift evaluation scheduler...")
        self._running = False
        self._stop_event.set()
        
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=timeout)
            if self._scheduler_thread.is_alive():
                logger.warning(
                    "Scheduler thread did not stop within timeout, "
                    "but will terminate when process exits"
                )
            else:
                logger.info("Drift evaluation scheduler stopped")
    
    def _run_scheduler(self, check_interval: timedelta) -> None:
        """
        Main scheduler loop (runs in background thread).
        
        Args:
            check_interval: How often to check for models needing evaluation
        """
        logger.info("Scheduler loop started")
        
        while self._running:
            try:
                self._check_and_evaluate_models()
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
            
            # Sleep for check interval or until stop event is set
            if self._stop_event.wait(timeout=check_interval.total_seconds()):
                break
        
        logger.info("Scheduler loop exited")
    
    def _check_and_evaluate_models(self) -> None:
        """Check all scheduled models and evaluate those that are due."""
        now = datetime.utcnow()
        
        for model_id, model in list(self.scheduled_models.items()):
            try:
                frequency = self.model_frequencies[model_id]
                
                # Check if evaluation is due
                if self.drift_detector.should_evaluate(model, frequency):
                    logger.info(
                        f"Evaluating model {model_id} (station {model.station_id})"
                    )
                    
                    # Invoke the evaluation callback
                    callback = self.evaluation_callbacks[model_id]
                    callback(model)
                    
            except Exception as e:
                logger.error(
                    f"Error evaluating model {model_id}: {e}",
                    exc_info=True
                )
    
    def get_scheduled_models(self) -> List[Dict]:
        """
        Get information about all scheduled models.
        
        Returns:
            List of dictionaries with model info and schedule details
        """
        result = []
        
        for model_id, model in self.scheduled_models.items():
            frequency = self.model_frequencies[model_id]
            last_eval = self.drift_detector.get_last_evaluation_time(model_id)
            
            next_eval = None
            if last_eval:
                next_eval = last_eval + frequency
            
            result.append({
                "model_id": str(model_id),
                "station_id": model.station_id,
                "frequency": str(frequency),
                "last_evaluation": last_eval.isoformat() if last_eval else None,
                "next_evaluation": next_eval.isoformat() if next_eval else "pending",
                "status": model.status
            })
        
        return result
    
    def is_running(self) -> bool:
        """Check if the scheduler is currently running."""
        return self._running
    
    def trigger_evaluation(self, model_id: UUID) -> None:
        """
        Manually trigger an evaluation for a specific model.
        
        Args:
            model_id: Model identifier to evaluate
            
        Raises:
            ValueError: If model is not scheduled
        """
        if model_id not in self.scheduled_models:
            raise ValueError(f"Model {model_id} is not scheduled")
        
        model = self.scheduled_models[model_id]
        callback = self.evaluation_callbacks[model_id]
        
        logger.info(
            f"Manually triggering evaluation for model {model_id} "
            f"(station {model.station_id})"
        )
        
        try:
            callback(model)
        except Exception as e:
            logger.error(
                f"Error in manual evaluation of model {model_id}: {e}",
                exc_info=True
            )
            raise
