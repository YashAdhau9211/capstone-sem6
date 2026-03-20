"""Data validation and quality checks for manufacturing data.

This module provides comprehensive data validation including:
- Schema-based validation
- Range checking for physical plausibility
- Flatline detection
- Duplicate timestamp detection
- Completeness calculation
- Data poisoning detection
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

import numpy as np
import pandas as pd
from scipy import stats


logger = logging.getLogger(__name__)


class Severity(Enum):
    """Severity levels for validation issues."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueType(Enum):
    """Types of validation issues."""
    
    OUT_OF_RANGE = "out_of_range"
    FLATLINE = "flatline"
    DUPLICATE_TIMESTAMP = "duplicate_timestamp"
    INCOMPLETE_DATA = "incomplete_data"
    DATA_POISONING = "data_poisoning"
    SCHEMA_VIOLATION = "schema_violation"


@dataclass
class DataSchema:
    """Schema definition for data validation."""
    
    required_columns: List[str]
    column_types: Dict[str, type]
    range_bounds: Dict[str, Tuple[float, float]]  # Variable -> (min, max)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Violation:
    """Data validation violation."""
    
    violation_id: UUID = field(default_factory=uuid4)
    issue_type: IssueType = IssueType.SCHEMA_VIOLATION
    variable: str = ""
    timestamp: Optional[datetime] = None
    value: Optional[float] = None
    expected_range: Optional[Tuple[float, float]] = None
    severity: Severity = Severity.MEDIUM
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationReport:
    """Comprehensive validation report."""
    
    report_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    violations: List[Violation] = field(default_factory=list)
    completeness: Dict[str, float] = field(default_factory=dict)
    quality_metrics: Dict[str, Any] = field(default_factory=dict)
    passed: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_violation(self, violation: Violation) -> None:
        """Add a violation to the report."""
        self.violations.append(violation)
        if violation.severity in (Severity.HIGH, Severity.CRITICAL):
            self.passed = False


@dataclass
class Distribution:
    """Statistical distribution baseline for poisoning detection."""
    
    mean: float
    std: float
    median: float
    q25: float
    q75: float
    skewness: float
    kurtosis: float
    last_updated: datetime = field(default_factory=datetime.utcnow)
    sample_size: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PoisoningReport:
    """Data poisoning detection report."""
    
    report_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    poisoned_variables: List[str] = field(default_factory=list)
    distribution_shifts: Dict[str, float] = field(default_factory=dict)  # Variable -> std deviations
    quarantined_data: Optional[pd.DataFrame] = None
    alert_generated: bool = False
    alert_timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class DataValidator:
    """Data validator with quality checks and poisoning detection.
    
    Implements comprehensive validation including:
    - Schema validation
    - Range checking
    - Flatline detection
    - Duplicate detection
    - Completeness calculation
    - Data poisoning detection
    """
    
    def __init__(
        self,
        completeness_window: timedelta = timedelta(hours=24),
        completeness_threshold: float = 0.85,
        flatline_window: int = 10,
        poisoning_threshold: float = 3.0
    ):
        """Initialize data validator.
        
        Args:
            completeness_window: Rolling window for completeness calculation
            completeness_threshold: Minimum acceptable completeness (0.0-1.0)
            flatline_window: Number of consecutive identical values to flag
            poisoning_threshold: Standard deviations for poisoning detection
        """
        self.completeness_window = completeness_window
        self.completeness_threshold = completeness_threshold
        self.flatline_window = flatline_window
        self.poisoning_threshold = poisoning_threshold
        self._baselines: Dict[str, Distribution] = {}
    
    def validate(self, data: pd.DataFrame, schema: DataSchema) -> ValidationReport:
        """Validate data against schema.
        
        Performs comprehensive validation including:
        - Required columns check
        - Data type validation
        - Range validation
        - Flatline detection
        - Duplicate detection
        - Completeness calculation
        
        Args:
            data: DataFrame to validate
            schema: Schema definition
            
        Returns:
            ValidationReport with all violations and metrics
            
        Requirements: 3.1, 3.2, 3.3, 3.4, 3.6, 3.7
        """
        report = ValidationReport()
        
        # Check required columns
        missing_cols = set(schema.required_columns) - set(data.columns)
        if missing_cols:
            report.add_violation(Violation(
                issue_type=IssueType.SCHEMA_VIOLATION,
                severity=Severity.CRITICAL,
                message=f"Missing required columns: {missing_cols}"
            ))
            return report
        
        # Validate column types
        for col, expected_type in schema.column_types.items():
            if col in data.columns:
                if not pd.api.types.is_dtype_equal(data[col].dtype, expected_type):
                    report.add_violation(Violation(
                        issue_type=IssueType.SCHEMA_VIOLATION,
                        variable=col,
                        severity=Severity.MEDIUM,
                        message=f"Column '{col}' has type {data[col].dtype}, expected {expected_type}"
                    ))
        
        # Range validation
        for variable, bounds in schema.range_bounds.items():
            if variable in data.columns:
                violations = self.check_range(data, variable, bounds)
                for violation in violations:
                    report.add_violation(violation)
        
        # Flatline detection
        for variable in data.columns:
            if pd.api.types.is_numeric_dtype(data[variable]):
                violations = self.detect_flatline(data, variable, self.flatline_window)
                for violation in violations:
                    report.add_violation(violation)
        
        # Duplicate detection
        duplicate_violations = self.detect_duplicates(data)
        for violation in duplicate_violations:
            report.add_violation(violation)
        
        # Completeness calculation
        completeness = self.calculate_completeness(data, self.completeness_window)
        report.completeness = completeness
        
        # Check completeness threshold
        for variable, comp_pct in completeness.items():
            if comp_pct < self.completeness_threshold:
                report.add_violation(Violation(
                    issue_type=IssueType.INCOMPLETE_DATA,
                    variable=variable,
                    severity=Severity.HIGH,
                    message=f"Completeness {comp_pct:.2%} below threshold {self.completeness_threshold:.2%}",
                    metadata={"completeness": comp_pct}
                ))
        
        # Quality metrics
        report.quality_metrics = {
            "total_records": len(data),
            "total_violations": len(report.violations),
            "critical_violations": sum(1 for v in report.violations if v.severity == Severity.CRITICAL),
            "high_violations": sum(1 for v in report.violations if v.severity == Severity.HIGH),
            "average_completeness": np.mean(list(completeness.values())) if completeness else 0.0
        }
        
        logger.info(
            f"Validation complete: {len(report.violations)} violations, "
            f"average completeness: {report.quality_metrics['average_completeness']:.2%}"
        )
        
        return report
    
    def check_range(
        self,
        data: pd.DataFrame,
        variable: str,
        bounds: Tuple[float, float]
    ) -> List[Violation]:
        """Check for values outside physically plausible ranges.
        
        Args:
            data: DataFrame to check
            variable: Variable name to check
            bounds: (min, max) tuple for valid range
            
        Returns:
            List of violations for out-of-range values
            
        Requirements: 3.1, 3.2
        """
        violations = []
        min_val, max_val = bounds
        
        if variable not in data.columns:
            return violations
        
        # Check for out-of-range values
        out_of_range = (data[variable] < min_val) | (data[variable] > max_val)
        
        # Create violations for each out-of-range value
        for idx in data[out_of_range].index:
            value = data.loc[idx, variable]
            timestamp = idx if isinstance(idx, datetime) else None
            
            violations.append(Violation(
                issue_type=IssueType.OUT_OF_RANGE,
                variable=variable,
                timestamp=timestamp,
                value=float(value),
                expected_range=bounds,
                severity=Severity.HIGH,
                message=f"Value {value} outside valid range [{min_val}, {max_val}]"
            ))
        
        return violations
    
    def detect_flatline(
        self,
        data: pd.DataFrame,
        variable: str,
        window: int = 10
    ) -> List[Violation]:
        """Detect sensor flatline conditions.
        
        Identifies sequences of identical values for more than the specified
        window size (default: 10 consecutive readings).
        
        Args:
            data: DataFrame to check
            variable: Variable name to check
            window: Number of consecutive identical values to flag
            
        Returns:
            List of violations for flatline conditions
            
        Requirements: 3.4
        """
        violations = []
        
        if variable not in data.columns:
            return violations
        
        series = data[variable].dropna()
        if len(series) < window:
            return violations
        
        # Find consecutive identical values
        # Compare each value with the next one
        is_same = series == series.shift(1)
        
        # Count consecutive True values
        consecutive_count = 0
        flatline_start_idx = None
        flatline_value = None
        
        for idx, same in is_same.items():
            if same:
                if consecutive_count == 0:
                    flatline_start_idx = idx
                    flatline_value = series.loc[idx]
                consecutive_count += 1
                
                # If we've reached the window threshold, create a violation
                if consecutive_count >= window:
                    timestamp = flatline_start_idx if isinstance(flatline_start_idx, datetime) else None
                    
                    violations.append(Violation(
                        issue_type=IssueType.FLATLINE,
                        variable=variable,
                        timestamp=timestamp,
                        value=float(flatline_value),
                        severity=Severity.MEDIUM,
                        message=f"Flatline detected: {consecutive_count} consecutive identical values ({flatline_value})",
                        metadata={"consecutive_count": consecutive_count}
                    ))
                    # Reset to avoid duplicate violations for the same flatline
                    consecutive_count = 0
                    flatline_start_idx = None
            else:
                consecutive_count = 0
                flatline_start_idx = None
        
        return violations
    
    def detect_duplicates(self, data: pd.DataFrame) -> List[Violation]:
        """Detect duplicate timestamps in time-series data.
        
        Args:
            data: DataFrame to check (should have DatetimeIndex or 'timestamp' column)
            
        Returns:
            List of violations for duplicate timestamps
            
        Requirements: 3.3
        """
        violations = []
        
        # Check if data has timestamp index or column
        if isinstance(data.index, pd.DatetimeIndex):
            timestamps = data.index
        elif 'timestamp' in data.columns:
            timestamps = data['timestamp']
        else:
            # No timestamp information available
            return violations
        
        # Find duplicate timestamps
        duplicates = timestamps[timestamps.duplicated(keep=False)]
        
        if len(duplicates) > 0:
            # Group by timestamp to count duplicates
            duplicate_counts = duplicates.value_counts()
            
            for timestamp, count in duplicate_counts.items():
                violations.append(Violation(
                    issue_type=IssueType.DUPLICATE_TIMESTAMP,
                    timestamp=timestamp if isinstance(timestamp, datetime) else None,
                    severity=Severity.MEDIUM,
                    message=f"Duplicate timestamp detected: {timestamp} appears {count} times"
                ))
        
        return violations
    
    def calculate_completeness(
        self,
        data: pd.DataFrame,
        window: timedelta
    ) -> Dict[str, float]:
        """Calculate completeness percentage over rolling window.
        
        Calculates the percentage of non-null values for each variable
        over the specified rolling time window.
        
        Args:
            data: DataFrame with DatetimeIndex
            window: Rolling window duration (default: 24 hours)
            
        Returns:
            Dictionary mapping variable names to completeness percentages (0.0-1.0)
            
        Requirements: 3.6, 3.7
        """
        completeness = {}
        
        # Ensure data has DatetimeIndex
        if not isinstance(data.index, pd.DatetimeIndex):
            # If no time information, calculate overall completeness
            for col in data.columns:
                if col != 'timestamp':
                    completeness[col] = data[col].notna().sum() / len(data) if len(data) > 0 else 0.0
            return completeness
        
        # Calculate completeness for each variable over the rolling window
        # Use the most recent window period
        if len(data) == 0:
            return completeness
        
        # Get the time range for the rolling window
        end_time = data.index.max()
        start_time = end_time - window
        
        # Filter data to the window
        window_data = data[data.index >= start_time]
        
        if len(window_data) == 0:
            return completeness
        
        # Calculate completeness for each column
        for col in window_data.columns:
            if col != 'timestamp':
                total_count = len(window_data)
                non_null_count = window_data[col].notna().sum()
                completeness[col] = non_null_count / total_count if total_count > 0 else 0.0
        
        return completeness
    
    def detect_poisoning(
        self,
        data: pd.DataFrame,
        variable: str,
        baseline: Optional[Distribution] = None
    ) -> PoisoningReport:
        """Detect potential data poisoning through distribution analysis.
        
        Compares incoming data distribution against historical baseline.
        Flags data when distribution shifts exceed the poisoning threshold
        (default: 3 standard deviations).
        
        Args:
            data: DataFrame with incoming data
            variable: Variable name to check
            baseline: Historical baseline distribution (if None, uses stored baseline)
            
        Returns:
            PoisoningReport with detection results
            
        Requirements: 20.1, 20.2, 20.3, 20.4, 20.5, 20.6
        """
        report = PoisoningReport()
        
        if variable not in data.columns:
            return report
        
        # Get baseline distribution
        if baseline is None:
            baseline = self._baselines.get(variable)
        
        if baseline is None:
            # No baseline available, cannot detect poisoning
            logger.warning(f"No baseline distribution available for variable '{variable}'")
            return report
        
        # Calculate current distribution statistics
        current_data = data[variable].dropna()
        
        if len(current_data) == 0:
            return report
        
        current_mean = current_data.mean()
        current_std = current_data.std()
        current_median = current_data.median()
        current_skewness = stats.skew(current_data)
        current_kurtosis = stats.kurtosis(current_data)
        
        # Calculate distribution shifts in standard deviations
        # Compare multiple statistical measures
        shifts = []
        
        # Mean shift
        if baseline.std > 0:
            mean_shift = abs(current_mean - baseline.mean) / baseline.std
            shifts.append(mean_shift)
        
        # Median shift
        if baseline.std > 0:
            median_shift = abs(current_median - baseline.median) / baseline.std
            shifts.append(median_shift)
        
        # Skewness shift (normalized by typical skewness variation)
        skewness_shift = abs(current_skewness - baseline.skewness)
        shifts.append(skewness_shift)
        
        # Kurtosis shift (normalized by typical kurtosis variation)
        kurtosis_shift = abs(current_kurtosis - baseline.kurtosis)
        shifts.append(kurtosis_shift)
        
        # Use maximum shift as the detection metric
        max_shift = max(shifts) if shifts else 0.0
        
        # Check if shift exceeds threshold
        if max_shift > self.poisoning_threshold:
            report.poisoned_variables.append(variable)
            report.distribution_shifts[variable] = max_shift
            
            # Quarantine the data
            report.quarantined_data = data[[variable]].copy()
            
            # Generate security alert
            report.alert_generated = True
            report.alert_timestamp = datetime.utcnow()
            
            logger.warning(
                f"Data poisoning detected for variable '{variable}': "
                f"distribution shift = {max_shift:.2f} standard deviations "
                f"(threshold: {self.poisoning_threshold})"
            )
        
        report.metadata = {
            "baseline_mean": baseline.mean,
            "baseline_std": baseline.std,
            "current_mean": current_mean,
            "current_std": current_std,
            "max_shift": max_shift,
            "threshold": self.poisoning_threshold
        }
        
        return report
    
    def update_baseline(
        self,
        data: pd.DataFrame,
        variable: str,
        validated: bool = True
    ) -> None:
        """Update baseline distribution for a variable.
        
        Should be called monthly with validated data to maintain
        up-to-date baselines for poisoning detection.
        
        Args:
            data: DataFrame with validated data
            variable: Variable name to update baseline for
            validated: Whether the data has been validated (default: True)
            
        Requirements: 20.6
        """
        if not validated:
            logger.warning(f"Attempting to update baseline with unvalidated data for '{variable}'")
            return
        
        if variable not in data.columns:
            logger.warning(f"Variable '{variable}' not found in data")
            return
        
        # Calculate distribution statistics
        series = data[variable].dropna()
        
        if len(series) < 10:
            logger.warning(f"Insufficient data to update baseline for '{variable}' (need at least 10 samples)")
            return
        
        baseline = Distribution(
            mean=series.mean(),
            std=series.std(),
            median=series.median(),
            q25=series.quantile(0.25),
            q75=series.quantile(0.75),
            skewness=stats.skew(series),
            kurtosis=stats.kurtosis(series),
            last_updated=datetime.utcnow(),
            sample_size=len(series)
        )
        
        self._baselines[variable] = baseline
        
        logger.info(
            f"Updated baseline distribution for '{variable}': "
            f"mean={baseline.mean:.2f}, std={baseline.std:.2f}, "
            f"sample_size={baseline.sample_size}"
        )
    
    def get_baseline(self, variable: str) -> Optional[Distribution]:
        """Get baseline distribution for a variable.
        
        Args:
            variable: Variable name
            
        Returns:
            Distribution baseline or None if not available
        """
        return self._baselines.get(variable)
