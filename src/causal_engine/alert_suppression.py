"""Alert Suppression System for manufacturing anomalies."""

from typing import Dict, List, Set, Tuple

from src.models.causal_graph import CausalDAG
from src.models.rca import Anomaly


class AlertSuppressionSystem:
    """
    Alert suppression system that identifies causal relationships between
    anomalies and suppresses descendant alerts to focus on root causes.
    
    Implements Requirement 13: Alert Suppression for Redundant Notifications
    """
    
    def __init__(self):
        """Initialize alert suppression system."""
        pass
    
    def suppress_alerts(
        self,
        anomalies: List[Anomaly],
        dag: CausalDAG
    ) -> Tuple[List[Anomaly], List[Anomaly]]:
        """
        Identify causal relationships between anomalies and suppress descendants.
        
        Args:
            anomalies: List of detected anomalies
            dag: Causal DAG for the station
        
        Returns:
            Tuple of (root_cause_anomalies, suppressed_anomalies)
            - root_cause_anomalies: Anomalies that should generate alerts
            - suppressed_anomalies: Anomalies suppressed due to causal relationships
        
        Requirements:
            - 13.1: Identify causal relationships between anomalies using DAG
            - 13.2: Suppress descendant anomaly alerts when ancestor exists
            - 13.3: Generate alerts only for root cause anomalies
            - 13.4: Include suppressed alerts in secondary notification list
        """
        if not anomalies:
            return [], []
        
        # Validate all anomaly variables exist in DAG
        for anomaly in anomalies:
            if anomaly.variable not in dag.nodes:
                raise ValueError(
                    f"Anomaly variable '{anomaly.variable}' not found in DAG nodes"
                )
        
        # Build causal relationship map between anomalies
        causal_relationships = self._identify_causal_relationships(anomalies, dag)
        
        # Identify which anomalies should be suppressed
        suppressed_set = self._identify_suppressed_anomalies(
            anomalies, causal_relationships
        )
        
        # Partition anomalies into root causes and suppressed
        root_cause_anomalies = []
        suppressed_anomalies = []
        
        for anomaly in anomalies:
            if anomaly.anomaly_id in suppressed_set:
                suppressed_anomalies.append(anomaly)
            else:
                root_cause_anomalies.append(anomaly)
        
        return root_cause_anomalies, suppressed_anomalies
    
    def get_suppressed_alerts(
        self,
        suppressed_anomalies: List[Anomaly],
        all_anomalies: List[Anomaly],
        dag: CausalDAG
    ) -> List[Dict]:
        """
        Get suppressed alerts with their causal relationships for viewing.
        
        Args:
            suppressed_anomalies: List of suppressed anomalies
            all_anomalies: List of all detected anomalies (for finding ancestors)
            dag: Causal DAG for the station
        
        Returns:
            List of dictionaries containing suppressed alert details with:
            - anomaly: The suppressed anomaly
            - suppressed_by: List of ancestor anomalies that caused suppression
            - causal_paths: List of causal paths from ancestors to this anomaly
        
        Requirements:
            - 13.5: Allow users to view suppressed alerts with causal relationships
        """
        result = []
        
        # Build map of anomaly variables to anomalies
        anomaly_map = {a.variable: a for a in all_anomalies}
        
        for suppressed in suppressed_anomalies:
            # Find which anomalies caused this suppression
            suppressed_by = []
            causal_paths = []
            
            for other in all_anomalies:
                if other.anomaly_id == suppressed.anomaly_id:
                    continue
                
                # Check if other is an ancestor of suppressed
                if self._is_ancestor(other.variable, suppressed.variable, dag):
                    suppressed_by.append(other)
                    
                    # Find causal path
                    path = dag.find_path(other.variable, suppressed.variable)
                    if path:
                        causal_paths.append({
                            "from": other.variable,
                            "to": suppressed.variable,
                            "path": path
                        })
            
            result.append({
                "anomaly": suppressed,
                "suppressed_by": suppressed_by,
                "causal_paths": causal_paths
            })
        
        return result
    
    def _identify_causal_relationships(
        self,
        anomalies: List[Anomaly],
        dag: CausalDAG
    ) -> Dict[str, Set[str]]:
        """
        Identify causal relationships between anomaly variables.
        
        Args:
            anomalies: List of detected anomalies
            dag: Causal DAG
        
        Returns:
            Dictionary mapping each anomaly variable to set of its ancestor variables
            that also have anomalies
        """
        # Get set of all anomaly variables
        anomaly_vars = {a.variable for a in anomalies}
        
        # For each anomaly, find which other anomalies are its ancestors
        relationships = {}
        
        for anomaly in anomalies:
            # Get all ancestors of this variable
            all_ancestors = dag.get_ancestors(anomaly.variable)
            
            # Filter to only ancestors that also have anomalies
            anomaly_ancestors = all_ancestors.intersection(anomaly_vars)
            
            relationships[anomaly.variable] = anomaly_ancestors
        
        return relationships
    
    def _identify_suppressed_anomalies(
        self,
        anomalies: List[Anomaly],
        causal_relationships: Dict[str, Set[str]]
    ) -> Set:
        """
        Identify which anomalies should be suppressed based on causal relationships.
        
        An anomaly is suppressed if it has at least one ancestor anomaly.
        
        Args:
            anomalies: List of detected anomalies
            causal_relationships: Map of variable to its ancestor variables with anomalies
        
        Returns:
            Set of anomaly_ids that should be suppressed
        """
        suppressed_ids = set()
        
        # Build map from variable to anomaly
        var_to_anomaly = {a.variable: a for a in anomalies}
        
        for variable, ancestors in causal_relationships.items():
            if ancestors:
                # This anomaly has ancestor anomalies, so it should be suppressed
                anomaly = var_to_anomaly[variable]
                suppressed_ids.add(anomaly.anomaly_id)
        
        return suppressed_ids
    
    def _is_ancestor(self, potential_ancestor: str, node: str, dag: CausalDAG) -> bool:
        """
        Check if potential_ancestor is an ancestor of node in the DAG.
        
        Args:
            potential_ancestor: Variable that might be an ancestor
            node: Target variable
            dag: Causal DAG
        
        Returns:
            True if potential_ancestor is an ancestor of node
        """
        ancestors = dag.get_ancestors(node)
        return potential_ancestor in ancestors
