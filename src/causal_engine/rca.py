"""Root Cause Analysis Engine for manufacturing anomalies."""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import UUID, uuid4

import numpy as np
import pandas as pd

from src.models.causal_graph import CausalDAG
from src.models.rca import Anomaly, RCAReport, RootCause
from src.causal_engine.alert_suppression import AlertSuppressionSystem


class RCAEngine:
    """
    Root Cause Analysis engine that identifies causal ancestors
    and computes attribution scores for anomalies.
    """
    
    def __init__(self):
        """Initialize RCA engine."""
        self.alert_suppression = AlertSuppressionSystem()
    
    def analyze_anomaly(
        self,
        anomaly: Anomaly,
        dag: CausalDAG,
        data: pd.DataFrame,
        max_root_causes: int = 5
    ) -> RCAReport:
        """
        Analyze an anomaly and generate RCA report.
        
        Args:
            anomaly: Detected anomaly to analyze
            dag: Causal DAG for the station
            data: Historical time-series data for attribution computation
            max_root_causes: Maximum number of root causes to include (default: 5)
        
        Returns:
            RCAReport with ranked root causes and causal paths
        
        Raises:
            ValueError: If anomaly variable not in DAG
        """
        start_time = datetime.now()
        
        # Validate anomaly variable exists in DAG
        if anomaly.variable not in dag.nodes:
            raise ValueError(
                f"Anomaly variable '{anomaly.variable}' not found in DAG nodes"
            )
        
        # Step 1: Identify causal ancestors
        ancestors = dag.get_ancestors(anomaly.variable)
        
        if not ancestors:
            # No ancestors - this is a root cause itself
            root_cause = RootCause(
                variable=anomaly.variable,
                attribution_score=1.0,
                confidence_interval=(0.95, 1.0),
                causal_path=[anomaly.variable],
                metadata={"note": "No causal ancestors found"}
            )
            
            generation_time = datetime.now()
            return RCAReport(
                report_id=uuid4(),
                anomaly=anomaly,
                root_causes=[root_cause],
                suppressed_alerts=[],
                generation_time=generation_time,
                metadata={
                    "processing_time_ms": (generation_time - start_time).total_seconds() * 1000
                }
            )
        
        # Step 2: Compute attribution scores for each ancestor
        attribution_scores = self.compute_attribution_scores(
            anomaly=anomaly,
            ancestors=list(ancestors),
            dag=dag,
            data=data
        )
        
        # Step 3: Rank root causes by attribution score
        ranked_root_causes = self.rank_root_causes(
            attribution_scores=attribution_scores,
            anomaly_variable=anomaly.variable,
            dag=dag,
            max_causes=max_root_causes
        )
        
        generation_time = datetime.now()
        processing_time_ms = (generation_time - start_time).total_seconds() * 1000
        
        return RCAReport(
            report_id=uuid4(),
            anomaly=anomaly,
            root_causes=ranked_root_causes,
            suppressed_alerts=[],  # Will be populated by AlertSuppressionSystem
            generation_time=generation_time,
            metadata={
                "processing_time_ms": processing_time_ms,
                "num_ancestors_analyzed": len(ancestors)
            }
        )
    
    def analyze_anomalies_with_suppression(
        self,
        anomalies: List[Anomaly],
        dag: CausalDAG,
        data: pd.DataFrame,
        max_root_causes: int = 5
    ) -> List[RCAReport]:
        """
        Analyze multiple anomalies and apply alert suppression.
        
        This method identifies causal relationships between anomalies and
        suppresses descendant alerts, generating reports only for root cause anomalies.
        
        Args:
            anomalies: List of detected anomalies to analyze
            dag: Causal DAG for the station
            data: Historical time-series data for attribution computation
            max_root_causes: Maximum number of root causes per report (default: 5)
        
        Returns:
            List of RCAReport objects for root cause anomalies, with suppressed
            alerts included in the suppressed_alerts field
        
        Requirements:
            - 13.1: Identify causal relationships between anomalies using DAG
            - 13.2: Suppress descendant anomaly alerts
            - 13.3: Generate alerts only for root cause anomalies
            - 13.4: Include suppressed alerts in secondary notification list
        """
        if not anomalies:
            return []
        
        # Step 1: Apply alert suppression to identify root cause anomalies
        root_cause_anomalies, suppressed_anomalies = self.alert_suppression.suppress_alerts(
            anomalies=anomalies,
            dag=dag
        )
        
        # Step 2: Generate RCA reports for root cause anomalies
        reports = []
        
        for anomaly in root_cause_anomalies:
            # Generate standard RCA report
            report = self.analyze_anomaly(
                anomaly=anomaly,
                dag=dag,
                data=data,
                max_root_causes=max_root_causes
            )
            
            # Add suppressed alerts that are descendants of this anomaly
            descendants = dag.get_descendants(anomaly.variable)
            anomaly_suppressed = [
                supp for supp in suppressed_anomalies
                if supp.variable in descendants
            ]
            
            # Update report with suppressed alerts
            report.suppressed_alerts = anomaly_suppressed
            
            reports.append(report)
        
        return reports
    
    def compute_attribution_scores(
        self,
        anomaly: Anomaly,
        ancestors: List[str],
        dag: CausalDAG,
        data: pd.DataFrame
    ) -> Dict[str, Tuple[float, Tuple[float, float]]]:
        """
        Compute causal attribution scores for potential root causes.
        
        Uses causal effect magnitudes from the DAG to compute attribution.
        For each ancestor, computes the total causal effect on the anomaly
        variable by multiplying coefficients along the causal path.
        
        Args:
            anomaly: Detected anomaly
            ancestors: List of causal ancestor variables
            dag: Causal DAG
            data: Historical data for confidence interval estimation
        
        Returns:
            Dictionary mapping variable name to (attribution_score, confidence_interval)
        """
        attribution_scores = {}
        
        for ancestor in ancestors:
            # Find causal path from ancestor to anomaly
            path = self.find_causal_path(dag, ancestor, anomaly.variable)
            
            if path is None:
                # No path found (shouldn't happen if ancestor is valid)
                continue
            
            # Compute total causal effect along path
            total_effect = self._compute_path_effect(dag, path)
            
            # Use absolute value for attribution score
            attribution_score = abs(total_effect)
            
            # Estimate confidence interval using bootstrap if data available
            if ancestor in data.columns and anomaly.variable in data.columns:
                ci = self._estimate_confidence_interval(
                    data=data,
                    source=ancestor,
                    target=anomaly.variable,
                    path_effect=total_effect
                )
            else:
                # Default confidence interval based on edge confidences
                avg_confidence = self._compute_path_confidence(dag, path)
                ci_width = (1.0 - avg_confidence) * abs(total_effect)
                ci = (
                    max(0.0, attribution_score - ci_width),
                    attribution_score + ci_width
                )
            
            attribution_scores[ancestor] = (attribution_score, ci)
        
        return attribution_scores
    
    def rank_root_causes(
        self,
        attribution_scores: Dict[str, Tuple[float, Tuple[float, float]]],
        anomaly_variable: str,
        dag: CausalDAG,
        max_causes: int = 5
    ) -> List[RootCause]:
        """
        Rank potential root causes by attribution score.
        
        Args:
            attribution_scores: Dictionary of attribution scores and CIs
            anomaly_variable: Variable with detected anomaly
            dag: Causal DAG
            max_causes: Maximum number of root causes to return
        
        Returns:
            List of RootCause objects sorted by attribution score (descending)
        """
        # Sort by attribution score (descending)
        sorted_causes = sorted(
            attribution_scores.items(),
            key=lambda x: x[1][0],
            reverse=True
        )
        
        # Take top N causes
        top_causes = sorted_causes[:max_causes]
        
        # Create RootCause objects
        root_causes = []
        for variable, (score, ci) in top_causes:
            path = self.find_causal_path(dag, variable, anomaly_variable)
            
            root_cause = RootCause(
                variable=variable,
                attribution_score=score,
                confidence_interval=ci,
                causal_path=path if path else [variable, anomaly_variable],
                metadata={}
            )
            root_causes.append(root_cause)
        
        return root_causes
    
    def find_causal_path(
        self,
        dag: CausalDAG,
        source: str,
        target: str
    ) -> Optional[List[str]]:
        """
        Find causal path from source to target in DAG.
        
        Args:
            dag: Causal DAG
            source: Source variable (potential root cause)
            target: Target variable (anomaly)
        
        Returns:
            List of variables in path from source to target, or None if no path
        """
        return dag.find_path(source, target)
    
    def _compute_path_effect(self, dag: CausalDAG, path: List[str]) -> float:
        """
        Compute total causal effect along a path by multiplying edge coefficients.
        
        Args:
            dag: Causal DAG
            path: List of variables in path
        
        Returns:
            Total causal effect (product of coefficients)
        """
        if len(path) < 2:
            return 1.0
        
        total_effect = 1.0
        
        for i in range(len(path) - 1):
            source = path[i]
            target = path[i + 1]
            
            # Find edge coefficient
            edge = next(
                (e for e in dag.edges if e.source == source and e.target == target),
                None
            )
            
            if edge:
                total_effect *= edge.coefficient
            else:
                # Edge not found (shouldn't happen with valid path)
                return 0.0
        
        return total_effect
    
    def _compute_path_confidence(self, dag: CausalDAG, path: List[str]) -> float:
        """
        Compute average confidence along a path.
        
        Args:
            dag: Causal DAG
            path: List of variables in path
        
        Returns:
            Average confidence of edges in path
        """
        if len(path) < 2:
            return 1.0
        
        confidences = []
        
        for i in range(len(path) - 1):
            source = path[i]
            target = path[i + 1]
            
            # Find edge confidence
            edge = next(
                (e for e in dag.edges if e.source == source and e.target == target),
                None
            )
            
            if edge:
                confidences.append(edge.confidence)
        
        return np.mean(confidences) if confidences else 0.5
    
    def _estimate_confidence_interval(
        self,
        data: pd.DataFrame,
        source: str,
        target: str,
        path_effect: float,
        n_bootstrap: int = 100
    ) -> Tuple[float, float]:
        """
        Estimate confidence interval for attribution score using bootstrap.
        
        Args:
            data: Historical time-series data
            source: Source variable
            target: Target variable
            path_effect: Computed path effect
            n_bootstrap: Number of bootstrap iterations
        
        Returns:
            95% confidence interval (lower, upper)
        """
        try:
            # Extract relevant columns
            source_data = data[source].dropna()
            target_data = data[target].dropna()
            
            # Align data
            common_idx = source_data.index.intersection(target_data.index)
            if len(common_idx) < 10:
                # Not enough data for bootstrap
                return (abs(path_effect) * 0.8, abs(path_effect) * 1.2)
            
            source_aligned = source_data.loc[common_idx].values
            target_aligned = target_data.loc[common_idx].values
            
            # Bootstrap sampling
            bootstrap_effects = []
            n_samples = len(source_aligned)
            
            for _ in range(n_bootstrap):
                # Resample with replacement
                indices = np.random.choice(n_samples, size=n_samples, replace=True)
                source_sample = source_aligned[indices]
                target_sample = target_aligned[indices]
                
                # Compute correlation as proxy for effect
                if np.std(source_sample) > 0 and np.std(target_sample) > 0:
                    corr = np.corrcoef(source_sample, target_sample)[0, 1]
                    bootstrap_effects.append(abs(corr * path_effect))
            
            if bootstrap_effects:
                # Compute 95% CI
                lower = np.percentile(bootstrap_effects, 2.5)
                upper = np.percentile(bootstrap_effects, 97.5)
                return (float(lower), float(upper))
            else:
                # Fallback
                return (abs(path_effect) * 0.8, abs(path_effect) * 1.2)
                
        except Exception:
            # Fallback to simple CI
            return (abs(path_effect) * 0.8, abs(path_effect) * 1.2)
