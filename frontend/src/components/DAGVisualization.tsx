import React, { useCallback, useMemo } from 'react';
import ReactFlow, {
  type Node,
  type Edge,
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  type Connection,
  BackgroundVariant,
  Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';
import type { CausalDAG, CausalEdge } from '../types';

interface DAGVisualizationProps {
  dag: CausalDAG | null;
  onNodeSelect?: (nodeId: string | null) => void;
  onEdgeSelect?: (edgeId: string | null) => void;
  onNodesChange?: (nodes: Node[]) => void;
  onEdgesChange?: (edges: Edge[]) => void;
  selectedNodes?: string[];
  selectedEdges?: string[];
  layout?: 'hierarchical' | 'force-directed' | 'circular';
}

// Layout algorithms
const calculateHierarchicalLayout = (
  nodes: string[],
  edges: CausalEdge[]
): Map<string, { x: number; y: number }> => {
  const positions = new Map<string, { x: number; y: number }>();
  const levels = new Map<string, number>();
  const inDegree = new Map<string, number>();

  // Initialize in-degree
  nodes.forEach((node) => inDegree.set(node, 0));
  edges.forEach((edge) => {
    inDegree.set(edge.target, (inDegree.get(edge.target) || 0) + 1);
  });

  // Topological sort to assign levels
  const queue: string[] = [];
  nodes.forEach((node) => {
    if (inDegree.get(node) === 0) {
      queue.push(node);
      levels.set(node, 0);
    }
  });

  while (queue.length > 0) {
    const current = queue.shift()!;
    const currentLevel = levels.get(current) || 0;

    edges.forEach((edge) => {
      if (edge.source === current) {
        const newDegree = (inDegree.get(edge.target) || 0) - 1;
        inDegree.set(edge.target, newDegree);

        const targetLevel = levels.get(edge.target) || 0;
        levels.set(edge.target, Math.max(targetLevel, currentLevel + 1));

        if (newDegree === 0) {
          queue.push(edge.target);
        }
      }
    });
  }

  // Position nodes by level
  const nodesByLevel = new Map<number, string[]>();
  levels.forEach((level, node) => {
    if (!nodesByLevel.has(level)) {
      nodesByLevel.set(level, []);
    }
    nodesByLevel.get(level)!.push(node);
  });

  const levelSpacing = 250;
  const nodeSpacing = 150;

  nodesByLevel.forEach((nodesInLevel, level) => {
    const startX = (-(nodesInLevel.length - 1) * nodeSpacing) / 2;
    nodesInLevel.forEach((node, index) => {
      positions.set(node, {
        x: startX + index * nodeSpacing,
        y: level * levelSpacing,
      });
    });
  });

  return positions;
};

const calculateCircularLayout = (nodes: string[]): Map<string, { x: number; y: number }> => {
  const positions = new Map<string, { x: number; y: number }>();
  const radius = Math.max(200, nodes.length * 30);
  const angleStep = (2 * Math.PI) / nodes.length;

  nodes.forEach((node, index) => {
    const angle = index * angleStep;
    positions.set(node, {
      x: radius * Math.cos(angle),
      y: radius * Math.sin(angle),
    });
  });

  return positions;
};

const calculateForceDirectedLayout = (
  nodes: string[],
  edges: CausalEdge[]
): Map<string, { x: number; y: number }> => {
  // Simple force-directed layout using spring forces
  const positions = new Map<string, { x: number; y: number }>();

  // Initialize random positions
  nodes.forEach((node, index) => {
    const angle = (index / nodes.length) * 2 * Math.PI;
    const radius = 300;
    positions.set(node, {
      x: radius * Math.cos(angle) + Math.random() * 50,
      y: radius * Math.sin(angle) + Math.random() * 50,
    });
  });

  // Simple spring simulation (limited iterations for performance)
  const iterations = 50;
  const k = 100; // Spring constant
  const repulsion = 5000;

  for (let iter = 0; iter < iterations; iter++) {
    const forces = new Map<string, { x: number; y: number }>();
    nodes.forEach((node) => forces.set(node, { x: 0, y: 0 }));

    // Repulsive forces between all nodes
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const node1 = nodes[i];
        const node2 = nodes[j];
        const pos1 = positions.get(node1)!;
        const pos2 = positions.get(node2)!;

        const dx = pos2.x - pos1.x;
        const dy = pos2.y - pos1.y;
        const distance = Math.sqrt(dx * dx + dy * dy) || 1;

        const force = repulsion / (distance * distance);
        const fx = (dx / distance) * force;
        const fy = (dy / distance) * force;

        const f1 = forces.get(node1)!;
        const f2 = forces.get(node2)!;
        f1.x -= fx;
        f1.y -= fy;
        f2.x += fx;
        f2.y += fy;
      }
    }

    // Attractive forces for edges
    edges.forEach((edge) => {
      const pos1 = positions.get(edge.source)!;
      const pos2 = positions.get(edge.target)!;

      const dx = pos2.x - pos1.x;
      const dy = pos2.y - pos1.y;
      const distance = Math.sqrt(dx * dx + dy * dy) || 1;

      const force = (distance - k) * 0.1;
      const fx = (dx / distance) * force;
      const fy = (dy / distance) * force;

      const f1 = forces.get(edge.source)!;
      const f2 = forces.get(edge.target)!;
      f1.x += fx;
      f1.y += fy;
      f2.x -= fx;
      f2.y -= fy;
    });

    // Apply forces
    nodes.forEach((node) => {
      const pos = positions.get(node)!;
      const force = forces.get(node)!;
      pos.x += force.x * 0.1;
      pos.y += force.y * 0.1;
    });
  }

  return positions;
};

export const DAGVisualization: React.FC<DAGVisualizationProps> = ({
  dag,
  onNodeSelect,
  onEdgeSelect,
  onNodesChange,
  onEdgesChange,
  selectedNodes = [],
  selectedEdges = [],
  layout = 'hierarchical',
}) => {
  // Convert DAG to React Flow nodes and edges
  const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
    if (!dag) {
      return { nodes: [], edges: [] };
    }

    // Calculate layout positions
    let positions: Map<string, { x: number; y: number }>;
    switch (layout) {
      case 'circular':
        positions = calculateCircularLayout(dag.nodes);
        break;
      case 'force-directed':
        positions = calculateForceDirectedLayout(dag.nodes, dag.edges);
        break;
      case 'hierarchical':
      default:
        positions = calculateHierarchicalLayout(dag.nodes, dag.edges);
        break;
    }

    const nodes: Node[] = dag.nodes.map((nodeId) => {
      const pos = positions.get(nodeId) || { x: 0, y: 0 };
      return {
        id: nodeId,
        type: 'default',
        position: pos,
        data: {
          label: nodeId,
          isSelected: selectedNodes.includes(nodeId),
        },
        style: {
          background: selectedNodes.includes(nodeId) ? '#4CAF50' : '#fff',
          border: selectedNodes.includes(nodeId) ? '2px solid #2E7D32' : '1px solid #ddd',
          borderRadius: '8px',
          padding: '10px',
          fontSize: '12px',
          fontWeight: selectedNodes.includes(nodeId) ? 'bold' : 'normal',
        },
      };
    });

    const edges: Edge[] = dag.edges.map((edge) => ({
      id: `${edge.source}-${edge.target}`,
      source: edge.source,
      target: edge.target,
      type: 'smoothstep',
      animated: selectedEdges.includes(`${edge.source}-${edge.target}`),
      style: {
        stroke: selectedEdges.includes(`${edge.source}-${edge.target}`) ? '#4CAF50' : '#999',
        strokeWidth: selectedEdges.includes(`${edge.source}-${edge.target}`) ? 3 : 2,
      },
      data: {
        coefficient: edge.coefficient,
        confidence: edge.confidence,
        edge_type: edge.edge_type,
      },
      label: `${edge.coefficient.toFixed(3)}`,
      labelStyle: {
        fontSize: 10,
        fill: selectedEdges.includes(`${edge.source}-${edge.target}`) ? '#2E7D32' : '#666',
        fontWeight: selectedEdges.includes(`${edge.source}-${edge.target}`) ? 'bold' : 'normal',
      },
    }));

    return { nodes, edges };
  }, [dag, selectedNodes, selectedEdges, layout]);

  const [nodes, setNodes, onNodesChangeInternal] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChangeInternal] = useEdgesState(initialEdges);

  // Update nodes and edges when DAG or selection changes
  React.useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  // Notify parent of changes
  React.useEffect(() => {
    if (onNodesChange) {
      onNodesChange(nodes);
    }
  }, [nodes, onNodesChange]);

  React.useEffect(() => {
    if (onEdgesChange) {
      onEdgesChange(edges);
    }
  }, [edges, onEdgesChange]);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      if (onNodeSelect) {
        onNodeSelect(node.id);
      }
    },
    [onNodeSelect]
  );

  const onEdgeClick = useCallback(
    (_event: React.MouseEvent, edge: Edge) => {
      if (onEdgeSelect) {
        onEdgeSelect(edge.id);
      }
    },
    [onEdgeSelect]
  );

  const onPaneClick = useCallback(() => {
    if (onNodeSelect) {
      onNodeSelect(null);
    }
    if (onEdgeSelect) {
      onEdgeSelect(null);
    }
  }, [onNodeSelect, onEdgeSelect]);

  if (!dag) {
    return (
      <div
        style={{
          width: '100%',
          height: '600px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#f5f5f5',
          borderRadius: '8px',
        }}
      >
        <p style={{ color: '#666' }}>
          No DAG selected. Please select a station model to visualize.
        </p>
      </div>
    );
  }

  return (
    <div style={{ width: '100%', height: '600px', border: '1px solid #ddd', borderRadius: '8px' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChangeInternal}
        onEdgesChange={onEdgesChangeInternal}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        onEdgeClick={onEdgeClick}
        onPaneClick={onPaneClick}
        fitView
        attributionPosition="bottom-left"
      >
        <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
        <Controls />
        <MiniMap
          nodeColor={(node) => (selectedNodes.includes(node.id) ? '#4CAF50' : '#fff')}
          style={{ background: '#f5f5f5' }}
        />
        <Panel
          position="top-right"
          style={{ background: 'white', padding: '10px', borderRadius: '4px', fontSize: '12px' }}
        >
          <div>
            <strong>Layout:</strong> {layout}
          </div>
          <div>
            <strong>Nodes:</strong> {dag.nodes.length}
          </div>
          <div>
            <strong>Edges:</strong> {dag.edges.length}
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
};
