"""Time-series and simulation data models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class TimeSeriesData:
    """Time-series data point from manufacturing process."""
    
    station_id: str
    variable: str
    timestamp: datetime
    value: float
    quality: str  # "good", "uncertain", "bad"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate time-series data properties."""
        valid_qualities = ("good", "uncertain", "bad")
        if self.quality not in valid_qualities:
            raise ValueError(f"Quality must be one of {valid_qualities}, got '{self.quality}'")


@dataclass
class SimulationScenario:
    """Counterfactual simulation scenario with interventions."""
    
    scenario_id: str
    station_id: str
    interventions: Dict[str, float]  # Variable -> intervention value
    factual_outcomes: Dict[str, float]  # Variable -> actual value
    counterfactual_outcomes: Dict[str, float]  # Variable -> predicted value
    differences: Dict[str, float]  # Variable -> (counterfactual - factual)
    confidence_intervals: Dict[str, tuple[float, float]] = field(default_factory=dict)  # Variable -> (lower, upper)
    timestamp: Optional[datetime] = None
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate simulation scenario properties."""
        # Ensure all outcome variables have corresponding differences
        for var in self.counterfactual_outcomes:
            if var in self.factual_outcomes:
                expected_diff = self.counterfactual_outcomes[var] - self.factual_outcomes[var]
                if var in self.differences:
                    actual_diff = self.differences[var]
                    # Allow small floating point errors
                    if abs(expected_diff - actual_diff) > 1e-6:
                        raise ValueError(
                            f"Difference for '{var}' ({actual_diff}) does not match "
                            f"counterfactual - factual ({expected_diff})"
                        )
