"""Station model data structures."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from .causal_graph import CausalDAG


@dataclass
class ModelConfig:
    """Configuration for station model training and monitoring."""
    
    retraining_schedule: timedelta  # e.g., timedelta(days=7) for weekly
    drift_threshold: float  # e.g., 0.10 for 10% degradation
    notification_settings: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate configuration."""
        if self.drift_threshold <= 0.0 or self.drift_threshold >= 1.0:
            raise ValueError(f"Drift threshold must be between 0.0 and 1.0, got {self.drift_threshold}")


@dataclass
class StationModel:
    """Causal model for a manufacturing station."""
    
    model_id: UUID
    station_id: str
    current_dag: Optional[CausalDAG]
    baseline_accuracy: Optional[float]
    status: str  # "active", "drifted", "training", "inactive"
    config: ModelConfig
    created_at: datetime
    updated_at: datetime
    last_evaluated: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate station model properties."""
        valid_statuses = ("active", "drifted", "training", "inactive")
        if self.status not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}, got '{self.status}'")
        
        if self.baseline_accuracy is not None:
            if not 0.0 <= self.baseline_accuracy <= 1.0:
                raise ValueError(f"Baseline accuracy must be between 0.0 and 1.0, got {self.baseline_accuracy}")
