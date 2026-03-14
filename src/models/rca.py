"""Root Cause Analysis data models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Tuple
from uuid import UUID


@dataclass
class Anomaly:
    """Detected anomaly in manufacturing process."""
    
    anomaly_id: UUID
    station_id: str
    variable: str
    timestamp: datetime
    value: float
    deviation: float  # Standard deviations from normal
    severity: str  # "low", "medium", "high", "critical"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate anomaly properties."""
        valid_severities = ("low", "medium", "high", "critical")
        if self.severity not in valid_severities:
            raise ValueError(f"Severity must be one of {valid_severities}, got '{self.severity}'")


@dataclass
class RootCause:
    """Identified root cause for an anomaly."""
    
    variable: str
    attribution_score: float  # Causal attribution magnitude
    confidence_interval: Tuple[float, float]  # 95% CI
    causal_path: List[str]  # Path from root cause to anomaly
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate root cause properties."""
        if len(self.confidence_interval) != 2:
            raise ValueError("Confidence interval must be a tuple of (lower, upper)")
        if self.confidence_interval[0] > self.confidence_interval[1]:
            raise ValueError("Confidence interval lower bound must be <= upper bound")


@dataclass
class RCAReport:
    """Root Cause Analysis report for an anomaly."""
    
    report_id: UUID
    anomaly: Anomaly
    root_causes: List[RootCause]  # Ranked by attribution score
    suppressed_alerts: List[Anomaly]  # Descendant anomalies suppressed
    generation_time: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate RCA report properties."""
        # Ensure root causes are sorted by attribution score (descending)
        if len(self.root_causes) > 1:
            for i in range(len(self.root_causes) - 1):
                if self.root_causes[i].attribution_score < self.root_causes[i + 1].attribution_score:
                    raise ValueError("Root causes must be sorted by attribution score in descending order")
