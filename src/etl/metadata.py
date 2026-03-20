"""Metadata and data lineage tracking for ETL pipeline.

This module provides utilities for tracking data lineage, preserving original
timestamps, and maintaining audit trails for data transformations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

import pandas as pd
from pandas import DataFrame


class TransformationType(Enum):
    """Types of data transformations."""
    INGESTION = "ingestion"
    TIMESTAMP_SYNC = "timestamp_synchronization"
    RESAMPLING = "resampling"
    INTERPOLATION = "interpolation"
    VALIDATION = "validation"
    AGGREGATION = "aggregation"


@dataclass
class TransformationRecord:
    """Record of a single data transformation."""
    transformation_type: TransformationType
    timestamp: datetime
    parameters: Dict[str, Any]
    input_record_count: int
    output_record_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'transformation_type': self.transformation_type.value,
            'timestamp': self.timestamp.isoformat(),
            'parameters': self.parameters,
            'input_record_count': self.input_record_count,
            'output_record_count': self.output_record_count,
            'metadata': self.metadata
        }


@dataclass
class DataLineage:
    """Complete lineage tracking for a data batch.
    
    This class tracks the complete transformation history of data from
    ingestion through all processing steps.
    
    Requirements: 2.5, 2.6
    """
    source_id: str
    ingestion_timestamp: datetime
    transformations: List[TransformationRecord] = field(default_factory=list)
    original_timestamps: Optional[DataFrame] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_transformation(
        self,
        transformation_type: TransformationType,
        parameters: Dict[str, Any],
        input_count: int,
        output_count: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a transformation record to the lineage.
        
        Args:
            transformation_type: Type of transformation
            parameters: Transformation parameters
            input_count: Number of input records
            output_count: Number of output records
            metadata: Additional metadata
        """
        record = TransformationRecord(
            transformation_type=transformation_type,
            timestamp=datetime.utcnow(),
            parameters=parameters,
            input_record_count=input_count,
            output_record_count=output_count,
            metadata=metadata or {}
        )
        self.transformations.append(record)
    
    def get_transformation_summary(self) -> str:
        """Get human-readable summary of transformations.
        
        Returns:
            String summary of all transformations
        """
        lines = [
            f"Data Lineage for {self.source_id}",
            f"Ingested at: {self.ingestion_timestamp.isoformat()}",
            f"Total transformations: {len(self.transformations)}",
            ""
        ]
        
        for i, transform in enumerate(self.transformations, 1):
            lines.append(
                f"{i}. {transform.transformation_type.value} "
                f"({transform.input_record_count} → {transform.output_record_count} records)"
            )
            lines.append(f"   Timestamp: {transform.timestamp.isoformat()}")
            if transform.parameters:
                lines.append(f"   Parameters: {transform.parameters}")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert lineage to dictionary for serialization.
        
        Returns:
            Dictionary representation of lineage
        """
        return {
            'source_id': self.source_id,
            'ingestion_timestamp': self.ingestion_timestamp.isoformat(),
            'transformations': [t.to_dict() for t in self.transformations],
            'metadata': self.metadata
        }
    
    def calculate_alignment_error(self) -> Optional[float]:
        """Calculate timestamp alignment error in seconds.
        
        Compares original timestamps with synchronized timestamps to ensure
        alignment error is <1 second (Requirement 2.6).
        
        Returns:
            Maximum alignment error in seconds, or None if not applicable
        """
        if self.original_timestamps is None:
            return None
        
        # Find timestamp synchronization transformation
        sync_transform = None
        for transform in self.transformations:
            if transform.transformation_type == TransformationType.TIMESTAMP_SYNC:
                sync_transform = transform
                break
        
        if not sync_transform:
            return None
        
        # Calculate alignment error from metadata if available
        return sync_transform.metadata.get('max_alignment_error_seconds')


class MetadataTracker:
    """Utility class for tracking metadata throughout ETL pipeline.
    
    This class provides methods for preserving original timestamps,
    tracking data lineage, and ensuring audit compliance.
    
    Requirements: 2.5, 2.6
    """
    
    @staticmethod
    def preserve_original_timestamps(data: DataFrame) -> DataFrame:
        """Preserve original timestamps before synchronization.
        
        Creates a copy of the original timestamp data for audit purposes.
        
        Args:
            data: DataFrame with timestamp index or column
            
        Returns:
            DataFrame copy with original timestamps
            
        Requirements: 2.5
        """
        return data.copy()
    
    @staticmethod
    def calculate_alignment_error(
        original: DataFrame,
        synchronized: DataFrame
    ) -> float:
        """Calculate timestamp alignment error.
        
        Ensures alignment error is <1 second (Requirement 2.6).
        
        Args:
            original: DataFrame with original timestamps
            synchronized: DataFrame with synchronized timestamps
            
        Returns:
            Maximum alignment error in seconds
        """
        if not isinstance(original.index, pd.DatetimeIndex):
            raise ValueError("Original data must have DatetimeIndex")
        if not isinstance(synchronized.index, pd.DatetimeIndex):
            raise ValueError("Synchronized data must have DatetimeIndex")
        
        # Ensure both indices are timezone-aware for comparison
        orig_index = original.index
        sync_index = synchronized.index
        
        if orig_index.tz is None:
            orig_index = orig_index.tz_localize('UTC')
        if sync_index.tz is None:
            sync_index = sync_index.tz_localize('UTC')
        
        # Find common indices
        common_indices = orig_index.intersection(sync_index)
        
        if len(common_indices) == 0:
            # If no common indices, calculate based on nearest timestamps
            max_error = 0.0
            for orig_ts in orig_index:
                # Find nearest synchronized timestamp
                time_diffs = abs(sync_index - orig_ts)
                min_diff = time_diffs.min()
                error_seconds = min_diff.total_seconds()
                max_error = max(max_error, error_seconds)
            return max_error
        
        # Calculate time differences for common indices
        time_diffs = abs(orig_index[orig_index.isin(common_indices)] - 
                        sync_index[sync_index.isin(common_indices)])
        
        max_error = time_diffs.max().total_seconds()
        return max_error
    
    @staticmethod
    def create_lineage(
        source_id: str,
        original_data: DataFrame,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DataLineage:
        """Create initial data lineage for a batch.
        
        Args:
            source_id: Source identifier
            original_data: Original data before processing
            metadata: Additional metadata
            
        Returns:
            DataLineage object for tracking transformations
            
        Requirements: 2.6
        """
        lineage = DataLineage(
            source_id=source_id,
            ingestion_timestamp=datetime.utcnow(),
            original_timestamps=MetadataTracker.preserve_original_timestamps(original_data),
            metadata=metadata or {}
        )
        
        # Add ingestion transformation
        lineage.add_transformation(
            transformation_type=TransformationType.INGESTION,
            parameters={'source_id': source_id},
            input_count=len(original_data),
            output_count=len(original_data),
            metadata={'ingestion_timestamp': datetime.utcnow().isoformat()}
        )
        
        return lineage
    
    @staticmethod
    def validate_alignment_error(alignment_error: float) -> bool:
        """Validate that alignment error meets requirement.
        
        Requirement 2.6: Timestamp alignment error must be <1 second.
        
        Args:
            alignment_error: Alignment error in seconds
            
        Returns:
            True if alignment error is acceptable, False otherwise
        """
        return alignment_error < 1.0
    
    @staticmethod
    def enrich_metadata(
        metadata: Dict[str, Any],
        additional_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enrich metadata with additional information.
        
        Args:
            metadata: Existing metadata
            additional_metadata: Additional metadata to merge
            
        Returns:
            Enriched metadata dictionary
        """
        enriched = metadata.copy()
        enriched.update(additional_metadata)
        enriched['last_updated'] = datetime.utcnow().isoformat()
        return enriched
