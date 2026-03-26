"""Causal graph data models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4


@dataclass
class CausalEdge:
    """Directed edge representing causal relationship."""
    
    source: str
    target: str
    coefficient: float
    confidence: float  # 0.0 to 1.0
    edge_type: str  # "linear" or "nonlinear"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate edge properties."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")
        if self.edge_type not in ("linear", "nonlinear"):
            raise ValueError(f"Edge type must be 'linear' or 'nonlinear', got {self.edge_type}")


@dataclass
class CausalDAG:
    """Directed Acyclic Graph representing causal relationships."""
    
    dag_id: UUID
    station_id: str
    version: int
    nodes: List[str]
    edges: List[CausalEdge]
    algorithm: str  # "DirectLiNGAM", "RESIT", "expert_edited"
    created_at: datetime
    created_by: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate DAG properties."""
        if not self.is_acyclic():
            raise ValueError("Graph contains cycles - not a valid DAG")
    
    def to_dot(self) -> str:
        """Export to DOT format for Graphviz."""
        lines = ["digraph CausalDAG {"]
        lines.append(f'  label="Station: {self.station_id}, Version: {self.version}";')
        lines.append('  rankdir=LR;')
        lines.append('')
        
        # Add nodes
        for node in self.nodes:
            lines.append(f'  "{node}";')
        
        lines.append('')
        
        # Add edges with labels
        for edge in self.edges:
            label = f"{edge.coefficient:.3f} ({edge.confidence:.2f})"
            lines.append(f'  "{edge.source}" -> "{edge.target}" [label="{label}"];')
        
        lines.append('}')
        return '\n'.join(lines)
    
    def to_graphml(self) -> str:
        """Export to GraphML format."""
        lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        lines.append('<graphml xmlns="http://graphml.graphdrawing.org/xmlns">')
        lines.append('  <key id="coefficient" for="edge" attr.name="coefficient" attr.type="double"/>')
        lines.append('  <key id="confidence" for="edge" attr.name="confidence" attr.type="double"/>')
        lines.append('  <key id="edge_type" for="edge" attr.name="edge_type" attr.type="string"/>')
        lines.append('  <key id="station_id" for="graph" attr.name="station_id" attr.type="string"/>')
        lines.append('  <key id="version" for="graph" attr.name="version" attr.type="int"/>')
        lines.append('  <key id="algorithm" for="graph" attr.name="algorithm" attr.type="string"/>')
        lines.append('')
        lines.append('  <graph id="G" edgedefault="directed">')
        lines.append(f'    <data key="station_id">{self.station_id}</data>')
        lines.append(f'    <data key="version">{self.version}</data>')
        lines.append(f'    <data key="algorithm">{self.algorithm}</data>')
        lines.append('')
        
        # Add nodes
        for node in self.nodes:
            lines.append(f'    <node id="{node}"/>')
        
        lines.append('')
        
        # Add edges
        for i, edge in enumerate(self.edges):
            lines.append(f'    <edge id="e{i}" source="{edge.source}" target="{edge.target}">')
            lines.append(f'      <data key="coefficient">{edge.coefficient}</data>')
            lines.append(f'      <data key="confidence">{edge.confidence}</data>')
            lines.append(f'      <data key="edge_type">{edge.edge_type}</data>')
            lines.append('    </edge>')
        
        lines.append('  </graph>')
        lines.append('</graphml>')
        return '\n'.join(lines)
    
    def get_ancestors(self, node: str) -> Set[str]:
        """Get all causal ancestors of a node."""
        if node not in self.nodes:
            raise ValueError(f"Node '{node}' not in graph")
        
        ancestors = set()
        to_visit = [node]
        visited = set()
        
        while to_visit:
            current = to_visit.pop()
            if current in visited:
                continue
            visited.add(current)
            
            # Find all parents (sources that point to current)
            parents = [edge.source for edge in self.edges if edge.target == current]
            for parent in parents:
                if parent not in ancestors:
                    ancestors.add(parent)
                    to_visit.append(parent)
        
        return ancestors
    
    def get_descendants(self, node: str) -> Set[str]:
        """Get all causal descendants of a node."""
        if node not in self.nodes:
            raise ValueError(f"Node '{node}' not in graph")
        
        descendants = set()
        to_visit = [node]
        visited = set()
        
        while to_visit:
            current = to_visit.pop()
            if current in visited:
                continue
            visited.add(current)
            
            # Find all children (targets that current points to)
            children = [edge.target for edge in self.edges if edge.source == current]
            for child in children:
                if child not in descendants:
                    descendants.add(child)
                    to_visit.append(child)
        
        return descendants
    
    def is_acyclic(self) -> bool:
        """Validate DAG has no cycles using DFS."""
        # Build adjacency list
        adj_list: Dict[str, List[str]] = {node: [] for node in self.nodes}
        for edge in self.edges:
            adj_list[edge.source].append(edge.target)
        
        # Track visit states: 0=unvisited, 1=visiting, 2=visited
        state = {node: 0 for node in self.nodes}
        
        def has_cycle(node: str) -> bool:
            if state[node] == 1:  # Currently visiting - cycle detected
                return True
            if state[node] == 2:  # Already visited
                return False
            
            state[node] = 1  # Mark as visiting
            for neighbor in adj_list[node]:
                if has_cycle(neighbor):
                    return True
            state[node] = 2  # Mark as visited
            return False
        
        # Check all nodes
        for node in self.nodes:
            if state[node] == 0:
                if has_cycle(node):
                    return False
        
        return True
    
    def find_cycle(self) -> Optional[List[str]]:
        """Find a cycle in the graph if one exists.
        
        Returns:
            List of nodes forming a cycle, or None if graph is acyclic.
        """
        # Build adjacency list
        adj_list: Dict[str, List[str]] = {node: [] for node in self.nodes}
        for edge in self.edges:
            adj_list[edge.source].append(edge.target)
        
        # Track visit states and path
        state = {node: 0 for node in self.nodes}  # 0=unvisited, 1=visiting, 2=visited
        path: List[str] = []
        
        def find_cycle_dfs(node: str) -> Optional[List[str]]:
            if state[node] == 1:  # Currently visiting - cycle detected
                # Extract cycle from path
                cycle_start = path.index(node)
                return path[cycle_start:] + [node]
            if state[node] == 2:  # Already visited
                return None
            
            state[node] = 1  # Mark as visiting
            path.append(node)
            
            for neighbor in adj_list[node]:
                cycle = find_cycle_dfs(neighbor)
                if cycle:
                    return cycle
            
            path.pop()
            state[node] = 2  # Mark as visited
            return None
        
        # Check all nodes
        for node in self.nodes:
            if state[node] == 0:
                cycle = find_cycle_dfs(node)
                if cycle:
                    return cycle
        
        return None
    
    def find_path(self, source: str, target: str) -> Optional[List[str]]:
        """Find causal path between nodes using BFS."""
        if source not in self.nodes:
            raise ValueError(f"Source node '{source}' not in graph")
        if target not in self.nodes:
            raise ValueError(f"Target node '{target}' not in graph")
        
        if source == target:
            return [source]
        
        # Build adjacency list
        adj_list: Dict[str, List[str]] = {node: [] for node in self.nodes}
        for edge in self.edges:
            adj_list[edge.source].append(edge.target)
        
        # BFS to find path
        queue = [(source, [source])]
        visited = {source}
        
        while queue:
            current, path = queue.pop(0)
            
            for neighbor in adj_list[current]:
                if neighbor == target:
                    return path + [neighbor]
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return None  # No path found
