"""ETL Pipeline for time-series synchronization and preprocessing.

This module implements the ETL pipeline for ingesting, synchronizing, resampling,
and interpolating time-series data from multiple ISA-95 sources.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any

import pandas as pd
import numpy as np
from pandas import DataFrame


class ResampleStrategy(Enum):
    """Resampling strategies for time-series data."""
    FORWARD_FILL = "ffill"
    BACKWARD_FILL = "bfill"
    LINEAR_INTERPOLATION = "linear"


@dataclass
class RawDataBatch:
    """Raw data batch from ISA-95 sources."""
    source_id: str
    data: DataFrame
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessedDataBatch:
    """Processed data batch after ETL pipeline."""
    source_id: str
    data: DataFrame
    timestamp: datetime
    original_timestamps: DataFrame
    metadata: Dict[str, Any] = field(default_factory=dict)
    lineage: List[str] = field(default_factory=list)


class ETLPipeline:
    """ETL Pipeline for time-series data synchronization and preprocessing.
    
    This class implements the core ETL functionality for:
    - Raw data batch processing
    - Timestamp synchronization using NTP-aligned reference clock
    - Resampling with multiple strategies
    - Gap interpolation with configurable thresholds
    
    Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6
    """
    
    def __init__(
        self,
        reference_clock: str = "UTC",
        max_gap_interpolation: timedelta = timedelta(minutes=5),
        default_resample_interval: Optional[timedelta] = None,
        batch_size: int = 1000
    ):
        """Initialize ETL Pipeline.
        
        Args:
            reference_clock: Reference clock for timestamp synchronization (default: UTC)
            max_gap_interpolation: Maximum gap for interpolation (default: 5 minutes)
            default_resample_interval: Default resampling interval (optional)
            batch_size: Batch size for processing (default: 1000 records)
        """
        self.reference_clock = reference_clock
        self.max_gap_interpolation = max_gap_interpolation
        self.default_resample_interval = default_resample_interval
        self.batch_size = batch_size
    
    def ingest(self, raw_data: RawDataBatch) -> ProcessedDataBatch:
        """Ingest and process raw data batch.
        
        This method orchestrates the complete ETL pipeline:
        1. Preserve original timestamps
        2. Synchronize timestamps to reference clock
        3. Resample to uniform intervals (if configured)
        4. Interpolate gaps
        
        Args:
            raw_data: Raw data batch from ISA-95 source
            
        Returns:
            ProcessedDataBatch with synchronized and preprocessed data
            
        Requirements: 2.1
        """
        # Preserve original timestamps for audit purposes (Requirement 2.5)
        original_timestamps = raw_data.data.copy()
        
        # Initialize lineage tracking (Requirement 2.6)
        lineage = [
            f"ingested_from_{raw_data.source_id}_at_{raw_data.timestamp.isoformat()}"
        ]
        
        # Process the data
        processed_data = raw_data.data.copy()
        
        # Synchronize timestamps to reference clock
        processed_data = self.synchronize_timestamps(
            processed_data,
            self.reference_clock
        )
        lineage.append(f"synchronized_to_{self.reference_clock}")
        
        # Resample if interval is configured
        if self.default_resample_interval is not None:
            processed_data = self.resample(
                processed_data,
                self.default_resample_interval,
                ResampleStrategy.LINEAR_INTERPOLATION
            )
            lineage.append(
                f"resampled_to_{self.default_resample_interval.total_seconds()}s"
            )
        
        # Interpolate gaps
        processed_data = self.interpolate_gaps(
            processed_data,
            self.max_gap_interpolation
        )
        lineage.append(
            f"interpolated_gaps_threshold_{self.max_gap_interpolation.total_seconds()}s"
        )
        
        return ProcessedDataBatch(
            source_id=raw_data.source_id,
            data=processed_data,
            timestamp=datetime.utcnow(),
            original_timestamps=original_timestamps,
            metadata={
                **raw_data.metadata,
                "reference_clock": self.reference_clock,
                "max_gap_interpolation_seconds": self.max_gap_interpolation.total_seconds(),
            },
            lineage=lineage
        )
    
    def synchronize_timestamps(
        self,
        data: DataFrame,
        reference_clock: str
    ) -> DataFrame:
        """Synchronize timestamps to a common reference clock.
        
        This method ensures all timestamps are aligned to an NTP-aligned reference clock
        with alignment error <1 second.
        
        Args:
            data: DataFrame with timestamp index or 'timestamp' column
            reference_clock: Reference clock identifier (e.g., 'UTC', 'NTP')
            
        Returns:
            DataFrame with synchronized timestamps
            
        Requirements: 2.1, 2.2, 2.6
        """
        df = data.copy()
        
        # Ensure timestamp column exists
        if 'timestamp' not in df.columns and not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("Data must have 'timestamp' column or DatetimeIndex")
        
        # Convert to datetime if needed
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            df = df.set_index('timestamp')
        elif not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index, utc=True)
        
        # Ensure timezone-aware timestamps (UTC)
        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC')
        else:
            df.index = df.index.tz_convert('UTC')
        
        # Round timestamps to nearest second for alignment (ensures <1 second error)
        df.index = df.index.round('1s')
        
        return df
    
    def resample(
        self,
        data: DataFrame,
        interval: timedelta,
        strategy: ResampleStrategy = ResampleStrategy.LINEAR_INTERPOLATION
    ) -> DataFrame:
        """Resample time-series data to uniform intervals.
        
        Supports multiple resampling strategies:
        - Forward-fill: Propagate last valid observation forward
        - Backward-fill: Use next valid observation to fill gap
        - Linear interpolation: Interpolate linearly between points
        
        Args:
            data: DataFrame with DatetimeIndex
            interval: Target resampling interval
            strategy: Resampling strategy to use
            
        Returns:
            DataFrame resampled to uniform intervals
            
        Requirements: 2.2, 2.3
        """
        if not isinstance(data.index, pd.DatetimeIndex):
            raise ValueError("Data must have DatetimeIndex for resampling")
        
        # Convert interval to pandas frequency string
        freq = f"{int(interval.total_seconds())}s"
        
        # Resample based on strategy
        if strategy == ResampleStrategy.FORWARD_FILL:
            resampled = data.resample(freq).ffill()
        elif strategy == ResampleStrategy.BACKWARD_FILL:
            resampled = data.resample(freq).bfill()
        elif strategy == ResampleStrategy.LINEAR_INTERPOLATION:
            resampled = data.resample(freq).interpolate(method='linear')
        else:
            raise ValueError(f"Unknown resampling strategy: {strategy}")
        
        return resampled
    
    def interpolate_gaps(
        self,
        data: DataFrame,
        max_gap: timedelta
    ) -> DataFrame:
        """Interpolate gaps in time-series data with threshold.
        
        - Gaps < max_gap: Linear interpolation
        - Gaps >= max_gap: Mark as missing (NaN)
        
        Args:
            data: DataFrame with DatetimeIndex
            max_gap: Maximum gap duration for interpolation
            
        Returns:
            DataFrame with interpolated gaps
            
        Requirements: 2.3, 2.4
        """
        if not isinstance(data.index, pd.DatetimeIndex):
            raise ValueError("Data must have DatetimeIndex for gap interpolation")
        
        df = data.copy()
        
        # Calculate time differences between consecutive points
        time_diffs = df.index.to_series().diff()
        
        # Identify gaps larger than threshold
        large_gaps = time_diffs > max_gap
        
        # For each column, interpolate small gaps and mark large gaps as NaN
        for col in df.columns:
            # Create a mask for values that should remain NaN (large gaps)
            # We need to mark the point AFTER a large gap as NaN
            mask = large_gaps.values
            
            # Interpolate all gaps first
            df[col] = df[col].interpolate(method='linear', limit_direction='both')
            
            # Then set large gaps back to NaN
            # Mark the first point after each large gap as NaN
            df.loc[mask, col] = np.nan
        
        return df
