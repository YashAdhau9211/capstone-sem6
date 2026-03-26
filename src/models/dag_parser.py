"""DAG import/export parsers for DOT and GraphML formats."""

import re
import xml.etree.ElementTree as ET
from typing import List, Tuple, Optional
from uuid import uuid4
from datetime import datetime

from .causal_graph import CausalDAG, CausalEdge


class DAGParser:
    """Parser for importing DAGs from external formats."""
    
    @staticmethod
    def parse_dot(dot_content: str, station_id: str, created_by: str) -> CausalDAG:
        """Parse DOT format into CausalDAG.
        
        Args:
            dot_content: DOT format string
            station_id: Station identifier
            created_by: User identifier
            
        Returns:
            CausalDAG object
            
        Raises:
            ValueError: If parsing fails or graph is invalid
        """
        nodes = []
        edges = []
        
        # Remove comments
        dot_content = re.sub(r'//.*?\n', '\n', dot_content)
        dot_content = re.sub(r'/\*.*?\*/', '', dot_content, flags=re.DOTALL)
        
        # Remove label and other graph attributes
        dot_content = re.sub(r'label\s*=\s*"[^"]*"\s*;', '', dot_content)
        dot_content = re.sub(r'rankdir\s*=\s*\w+\s*;', '', dot_content)
        
        # Extract node declarations
        node_pattern = r'"([^"]+)"\s*;'
        for match in re.finditer(node_pattern, dot_content):
            node_name = match.group(1)
            if node_name not in nodes:
                nodes.append(node_name)
        
        # Extract edge declarations
        edge_pattern = r'"([^"]+)"\s*->\s*"([^"]+)"\s*(?:\[label="([^"]+)"\])?'
        for match in re.finditer(edge_pattern, dot_content):
            source = match.group(1)
            target = match.group(2)
            label = match.group(3)
            
            # Add nodes if not already present
            if source not in nodes:
                nodes.append(source)
            if target not in nodes:
                nodes.append(target)
            
            # Parse coefficient and confidence from label
            coefficient = 0.0
            confidence = 1.0
            
            if label:
                # Expected format: "0.123 (0.95)"
                parts = label.split()
                if len(parts) >= 1:
                    try:
                        coefficient = float(parts[0])
                    except ValueError:
                        pass
                if len(parts) >= 2:
                    conf_str = parts[1].strip('()')
                    try:
                        confidence = float(conf_str)
                    except ValueError:
                        pass
            
            edges.append(
                CausalEdge(
                    source=source,
                    target=target,
                    coefficient=coefficient,
                    confidence=confidence,
                    edge_type="linear",
                    metadata={}
                )
            )
        
        # Create DAG
        dag = CausalDAG(
            dag_id=uuid4(),
            station_id=station_id,
            version=0,
            nodes=nodes,
            edges=edges,
            algorithm="imported_dot",
            created_at=datetime.utcnow(),
            created_by=created_by,
            metadata={"import_format": "dot"}
        )
        
        return dag
    
    @staticmethod
    def parse_graphml(graphml_content: str, station_id: str, created_by: str) -> CausalDAG:
        """Parse GraphML format into CausalDAG.
        
        Args:
            graphml_content: GraphML XML string
            station_id: Station identifier
            created_by: User identifier
            
        Returns:
            CausalDAG object
            
        Raises:
            ValueError: If parsing fails or graph is invalid
        """
        try:
            root = ET.fromstring(graphml_content)
        except ET.ParseError as e:
            raise ValueError(f"Invalid GraphML XML: {e}")
        
        # Define namespace
        ns = {'gml': 'http://graphml.graphdrawing.org/xmlns'}
        
        # Find graph element
        graph = root.find('.//gml:graph', ns)
        if graph is None:
            raise ValueError("No graph element found in GraphML")
        
        # Extract nodes
        nodes = []
        node_elements = graph.findall('.//gml:node', ns)
        for node_elem in node_elements:
            node_id = node_elem.get('id')
            if node_id:
                nodes.append(node_id)
        
        # Extract edges
        edges = []
        edge_elements = graph.findall('.//gml:edge', ns)
        for edge_elem in edge_elements:
            source = edge_elem.get('source')
            target = edge_elem.get('target')
            
            if not source or not target:
                continue
            
            # Extract edge attributes
            coefficient = 0.0
            confidence = 1.0
            edge_type = "linear"
            
            for data_elem in edge_elem.findall('.//gml:data', ns):
                key = data_elem.get('key')
                value = data_elem.text
                
                if key == 'coefficient' and value:
                    try:
                        coefficient = float(value)
                    except ValueError:
                        pass
                elif key == 'confidence' and value:
                    try:
                        confidence = float(value)
                    except ValueError:
                        pass
                elif key == 'edge_type' and value:
                    edge_type = value
            
            edges.append(
                CausalEdge(
                    source=source,
                    target=target,
                    coefficient=coefficient,
                    confidence=confidence,
                    edge_type=edge_type,
                    metadata={}
                )
            )
        
        # Create DAG
        dag = CausalDAG(
            dag_id=uuid4(),
            station_id=station_id,
            version=0,
            nodes=nodes,
            edges=edges,
            algorithm="imported_graphml",
            created_at=datetime.utcnow(),
            created_by=created_by,
            metadata={"import_format": "graphml"}
        )
        
        return dag
    
    @staticmethod
    def validate_against_schema(dag: CausalDAG, known_variables: List[str]) -> Tuple[bool, List[str]]:
        """Validate that all DAG nodes match known variables.
        
        Args:
            dag: CausalDAG to validate
            known_variables: List of known variable names
            
        Returns:
            Tuple of (is_valid, unknown_variables)
        """
        unknown = []
        for node in dag.nodes:
            if node not in known_variables:
                unknown.append(node)
        
        return len(unknown) == 0, unknown
