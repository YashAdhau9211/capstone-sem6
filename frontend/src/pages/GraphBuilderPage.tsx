import React, { useState, useEffect, useCallback } from 'react';
import { DAGVisualization } from '../components/DAGVisualization';
import { NodeTooltip } from '../components/NodeTooltip';
import { EdgeTooltip } from '../components/EdgeTooltip';
import { SaveDAGDialog } from '../components/SaveDAGDialog';
import { VersionHistoryDialog } from '../components/VersionHistoryDialog';
import { ImportExportDialog } from '../components/ImportExportDialog';
import { api } from '../services/api';
import type { CausalDAG, StationModel } from '../types';

export const GraphBuilderPage: React.FC = () => {
  const [models, setModels] = useState<StationModel[]>([]);
  const [selectedModel, setSelectedModel] = useState<StationModel | null>(null);
  const [dag, setDag] = useState<CausalDAG | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Selection state
  const [selectedNodes, setSelectedNodes] = useState<string[]>([]);
  const [selectedEdges, setSelectedEdges] = useState<string[]>([]);

  // Tooltip state
  const [nodeTooltip, setNodeTooltip] = useState<{
    nodeId: string;
    position: { x: number; y: number };
  } | null>(null);
  const [edgeTooltip, setEdgeTooltip] = useState<{
    source: string;
    target: string;
    coefficient: number;
    confidence: number;
    edgeType: 'linear' | 'nonlinear';
    position: { x: number; y: number };
  } | null>(null);

  // Layout state
  const [layout, setLayout] = useState<'hierarchical' | 'force-directed' | 'circular'>(
    'hierarchical'
  );

  // Multi-select mode
  const [multiSelectMode, setMultiSelectMode] = useState(false);

  // Edge manipulation state
  const [edgeMode, setEdgeMode] = useState<'select' | 'add' | 'delete' | 'reverse'>('select');
  const [pendingEdge, setPendingEdge] = useState<{ source: string } | null>(null);
  const [operationStatus, setOperationStatus] = useState<{
    type: 'success' | 'error' | 'info';
    message: string;
  } | null>(null);

  // Dialog state
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [showVersionHistory, setShowVersionHistory] = useState(false);
  const [showImportExport, setShowImportExport] = useState(false);

  // Load station models
  useEffect(() => {
    const loadModels = async () => {
      try {
        setLoading(true);
        const data = await api.models.list();
        setModels(data);
        if (data.length > 0) {
          setSelectedModel(data[0]);
        }
      } catch (err) {
        setError('Failed to load station models');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    loadModels();
  }, []);

  // Load DAG when model changes
  useEffect(() => {
    const loadDAG = async () => {
      if (!selectedModel) {
        setDag(null);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const dagData = await api.dags.get(selectedModel.current_dag_id);
        setDag(dagData);
        // Reset selections when loading new DAG
        setSelectedNodes([]);
        setSelectedEdges([]);
      } catch (err) {
        setError('Failed to load DAG');
        console.error(err);
        setDag(null);
      } finally {
        setLoading(false);
      }
    };

    loadDAG();
  }, [selectedModel]);

  // Handle node selection
  const handleNodeSelect = useCallback(
    (nodeId: string | null) => {
      if (!nodeId) {
        setSelectedNodes([]);
        setSelectedEdges([]);
        setPendingEdge(null);
        return;
      }

      // Handle edge add mode
      if (edgeMode === 'add') {
        if (!pendingEdge) {
          // First node selected - set as source
          setPendingEdge({ source: nodeId });
          setSelectedNodes([nodeId]);
          setOperationStatus({
            type: 'info',
            message: `Source node "${nodeId}" selected. Click target node to add edge.`,
          });
        } else {
          // Second node selected - create edge
          if (pendingEdge.source === nodeId) {
            setOperationStatus({
              type: 'error',
              message: 'Cannot create self-loop edge.',
            });
            return;
          }
          handleAddEdge(pendingEdge.source, nodeId);
          setPendingEdge(null);
        }
        return;
      }

      if (multiSelectMode) {
        setSelectedNodes((prev) =>
          prev.includes(nodeId) ? prev.filter((id) => id !== nodeId) : [...prev, nodeId]
        );
      } else {
        setSelectedNodes([nodeId]);

        // Highlight connected edges
        if (dag) {
          const connectedEdges = dag.edges
            .filter((edge) => edge.source === nodeId || edge.target === nodeId)
            .map((edge) => `${edge.source}-${edge.target}`);
          setSelectedEdges(connectedEdges);
        }
      }
    },
    [multiSelectMode, dag, edgeMode, pendingEdge]
  );

  // Handle edge selection
  const handleEdgeSelect = useCallback(
    (edgeId: string | null) => {
      if (!edgeId) {
        setSelectedEdges([]);
        return;
      }

      // Handle delete mode
      if (edgeMode === 'delete') {
        const [source, target] = edgeId.split('-');
        handleDeleteEdge(source, target);
        return;
      }

      // Handle reverse mode
      if (edgeMode === 'reverse') {
        const [source, target] = edgeId.split('-');
        handleReverseEdge(source, target);
        return;
      }

      if (multiSelectMode) {
        setSelectedEdges((prev) =>
          prev.includes(edgeId) ? prev.filter((id) => id !== edgeId) : [...prev, edgeId]
        );
      } else {
        setSelectedEdges([edgeId]);

        // Highlight connected nodes
        const [source, target] = edgeId.split('-');
        setSelectedNodes([source, target]);
      }
    },
    [multiSelectMode, edgeMode]
  );

  // Handle mouse move for tooltips
  const handleMouseMove = useCallback(
    (event: React.MouseEvent) => {
      const target = event.target as HTMLElement;

      // Check if hovering over a node
      const nodeElement = target.closest('[data-id]');
      if (nodeElement && nodeElement.classList.contains('react-flow__node')) {
        const nodeId = nodeElement.getAttribute('data-id');
        if (nodeId && dag) {
          setNodeTooltip({
            nodeId,
            position: { x: event.clientX, y: event.clientY },
          });
          setEdgeTooltip(null);
          return;
        }
      }

      // Check if hovering over an edge
      const edgeElement = target.closest('.react-flow__edge');
      if (edgeElement && dag) {
        const edgeId = edgeElement.getAttribute('data-id');
        if (edgeId) {
          const [source, target] = edgeId.split('-');
          const edge = dag.edges.find((e) => e.source === source && e.target === target);

          if (edge) {
            setEdgeTooltip({
              source: edge.source,
              target: edge.target,
              coefficient: edge.coefficient,
              confidence: edge.confidence,
              edgeType: edge.edge_type,
              position: { x: event.clientX, y: event.clientY },
            });
            setNodeTooltip(null);
            return;
          }
        }
      }

      // Clear tooltips if not hovering over node or edge
      setNodeTooltip(null);
      setEdgeTooltip(null);
    },
    [dag]
  );

  // Highlight neighbors of selected nodes
  const getHighlightedElements = useCallback(() => {
    if (!dag || selectedNodes.length === 0) {
      return { nodes: selectedNodes, edges: selectedEdges };
    }

    const neighborNodes = new Set<string>(selectedNodes);
    const neighborEdges = new Set<string>(selectedEdges);

    // Add neighbors
    selectedNodes.forEach((nodeId) => {
      dag.edges.forEach((edge) => {
        if (edge.source === nodeId) {
          neighborNodes.add(edge.target);
          neighborEdges.add(`${edge.source}-${edge.target}`);
        }
        if (edge.target === nodeId) {
          neighborNodes.add(edge.source);
          neighborEdges.add(`${edge.source}-${edge.target}`);
        }
      });
    });

    return {
      nodes: Array.from(neighborNodes),
      edges: Array.from(neighborEdges),
    };
  }, [dag, selectedNodes, selectedEdges]);

  const highlighted = getHighlightedElements();

  // Edge manipulation functions
  const handleAddEdge = async (source: string, target: string) => {
    if (!selectedModel) return;

    try {
      setLoading(true);
      setOperationStatus(null);

      await api.dags.modifyEdges(selectedModel.station_id, {
        operations: [
          {
            operation: 'add',
            source,
            target,
            coefficient: 0.0,
            confidence: 1.0,
            edge_type: 'linear',
          },
        ],
        created_by: 'current_user', // TODO: Get from auth context
      });

      setOperationStatus({
        type: 'success',
        message: `Edge added: ${source} → ${target}`,
      });

      // Reload DAG
      const dagData = await api.dags.get(selectedModel.current_dag_id);
      setDag(dagData);
      setSelectedNodes([]);
      setSelectedEdges([]);
    } catch (err: any) {
      const errorDetail = err.response?.data?.detail;
      let errorMessage = err.response?.data?.message || 'Failed to add edge';
      
      if (errorDetail?.cycle_path && errorDetail.cycle_path.length > 0) {
        errorMessage += ` - Cycle detected: ${errorDetail.cycle_path.join(' → ')}`;
      }
      
      setOperationStatus({
        type: 'error',
        message: errorMessage,
      });
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteEdge = async (source: string, target: string) => {
    if (!selectedModel) return;

    try {
      setLoading(true);
      setOperationStatus(null);

      await api.dags.modifyEdges(selectedModel.station_id, {
        operations: [
          {
            operation: 'delete',
            source,
            target,
          },
        ],
        created_by: 'current_user', // TODO: Get from auth context
      });

      setOperationStatus({
        type: 'success',
        message: `Edge deleted: ${source} → ${target}`,
      });

      // Reload DAG
      const dagData = await api.dags.get(selectedModel.current_dag_id);
      setDag(dagData);
      setSelectedNodes([]);
      setSelectedEdges([]);
    } catch (err: any) {
      setOperationStatus({
        type: 'error',
        message: err.response?.data?.message || 'Failed to delete edge',
      });
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleReverseEdge = async (source: string, target: string) => {
    if (!selectedModel) return;

    try {
      setLoading(true);
      setOperationStatus(null);

      await api.dags.modifyEdges(selectedModel.station_id, {
        operations: [
          {
            operation: 'reverse',
            source,
            target,
          },
        ],
        created_by: 'current_user', // TODO: Get from auth context
      });

      setOperationStatus({
        type: 'success',
        message: `Edge reversed: ${source} → ${target} became ${target} → ${source}`,
      });

      // Reload DAG
      const dagData = await api.dags.get(selectedModel.current_dag_id);
      setDag(dagData);
      setSelectedNodes([]);
      setSelectedEdges([]);
    } catch (err: any) {
      const errorDetail = err.response?.data?.detail;
      let errorMessage = err.response?.data?.message || 'Failed to reverse edge';
      
      if (errorDetail?.cycle_path && errorDetail.cycle_path.length > 0) {
        errorMessage += ` - Cycle detected: ${errorDetail.cycle_path.join(' → ')}`;
      }
      
      setOperationStatus({
        type: 'error',
        message: errorMessage,
      });
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Save DAG with name and description
  const handleSaveDAG = async (name: string, description: string) => {
    if (!selectedModel || !dag) return;

    const startTime = Date.now();

    try {
      await api.dags.create({
        station_id: selectedModel.station_id,
        nodes: dag.nodes,
        edges: dag.edges.map((e) => ({
          source: e.source,
          target: e.target,
          coefficient: e.coefficient,
          confidence: e.confidence,
          edge_type: e.edge_type,
        })),
        algorithm: 'expert_edited',
        created_by: 'current_user', // TODO: Get from auth context
        metadata: {
          name,
          description,
          parent_version: dag.version,
        },
      });

      const saveTime = Date.now() - startTime;

      setOperationStatus({
        type: 'success',
        message: `DAG saved successfully as "${name}" (${saveTime}ms)`,
      });

      // Reload DAG to get new version
      const dagData = await api.dags.get(selectedModel.current_dag_id);
      setDag(dagData);
    } catch (err: any) {
      throw new Error(err.response?.data?.message || 'Failed to save DAG');
    }
  };

  // Load specific version
  const handleLoadVersion = async (version: number) => {
    if (!selectedModel) return;

    try {
      const dagData = await api.dags.getVersion(selectedModel.station_id, version);
      setDag(dagData);
      setOperationStatus({
        type: 'success',
        message: `Loaded version ${version}`,
      });
    } catch (err: any) {
      throw new Error(err.response?.data?.message || 'Failed to load version');
    }
  };

  // Handle import success
  const handleImportSuccess = async () => {
    if (!selectedModel) return;

    try {
      const dagData = await api.dags.get(selectedModel.current_dag_id);
      setDag(dagData);
      setOperationStatus({
        type: 'success',
        message: 'DAG imported successfully',
      });
    } catch (err: any) {
      setError('Failed to reload DAG after import');
    }
  };

  return (
    <div style={{ padding: '20px', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <div style={{ marginBottom: '20px' }}>
        <h1 style={{ margin: '0 0 10px 0' }}>Graph Builder</h1>
        <p style={{ margin: '0 0 20px 0', color: '#666' }}>
          Interactive causal DAG visualization and editing
        </p>

        {/* Controls */}
        <div
          style={{
            display: 'flex',
            gap: '20px',
            alignItems: 'center',
            padding: '15px',
            background: '#f5f5f5',
            borderRadius: '8px',
            flexWrap: 'wrap',
          }}
        >
          {/* Station Model Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <label htmlFor="model-select" style={{ fontWeight: 'bold' }}>
              Station Model:
            </label>
            <select
              id="model-select"
              value={selectedModel?.station_id || ''}
              onChange={(e) => {
                const model = models.find((m) => m.station_id === e.target.value);
                setSelectedModel(model || null);
              }}
              style={{
                padding: '8px 12px',
                borderRadius: '4px',
                border: '1px solid #ddd',
                fontSize: '14px',
                minWidth: '200px',
              }}
              disabled={loading || models.length === 0}
            >
              {models.length === 0 ? (
                <option>No models available</option>
              ) : (
                models.map((model) => (
                  <option key={model.station_id} value={model.station_id}>
                    {model.station_id}
                  </option>
                ))
              )}
            </select>
          </div>

          {/* Layout Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <label htmlFor="layout-select" style={{ fontWeight: 'bold' }}>
              Layout:
            </label>
            <select
              id="layout-select"
              value={layout}
              onChange={(e) =>
                setLayout(e.target.value as 'hierarchical' | 'force-directed' | 'circular')
              }
              style={{
                padding: '8px 12px',
                borderRadius: '4px',
                border: '1px solid #ddd',
                fontSize: '14px',
              }}
              disabled={!dag}
            >
              <option value="hierarchical">Hierarchical</option>
              <option value="force-directed">Force-Directed</option>
              <option value="circular">Circular</option>
            </select>
          </div>

          {/* Edge Mode Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <label htmlFor="edge-mode-select" style={{ fontWeight: 'bold' }}>
              Edge Mode:
            </label>
            <select
              id="edge-mode-select"
              value={edgeMode}
              onChange={(e) => {
                setEdgeMode(e.target.value as 'select' | 'add' | 'delete' | 'reverse');
                setPendingEdge(null);
                setOperationStatus(null);
              }}
              style={{
                padding: '8px 12px',
                borderRadius: '4px',
                border: '1px solid #ddd',
                fontSize: '14px',
              }}
              disabled={!dag}
            >
              <option value="select">Select</option>
              <option value="add">Add Edge</option>
              <option value="delete">Delete Edge</option>
              <option value="reverse">Reverse Edge</option>
            </select>
          </div>

          {/* Multi-select Toggle */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={multiSelectMode}
                onChange={(e) => setMultiSelectMode(e.target.checked)}
                disabled={!dag}
              />
              <span style={{ fontWeight: 'bold' }}>Multi-select Mode</span>
            </label>
          </div>

          {/* Clear Selection */}
          {(selectedNodes.length > 0 || selectedEdges.length > 0) && (
            <button
              onClick={() => {
                setSelectedNodes([]);
                setSelectedEdges([]);
              }}
              style={{
                padding: '8px 16px',
                borderRadius: '4px',
                border: '1px solid #ddd',
                background: 'white',
                cursor: 'pointer',
                fontSize: '14px',
              }}
            >
              Clear Selection
            </button>
          )}

          {/* Save DAG Button */}
          <button
            onClick={() => setShowSaveDialog(true)}
            disabled={!dag}
            style={{
              padding: '8px 16px',
              borderRadius: '4px',
              border: 'none',
              background: dag ? '#4CAF50' : '#ccc',
              color: 'white',
              cursor: dag ? 'pointer' : 'not-allowed',
              fontSize: '14px',
              fontWeight: 'bold',
            }}
          >
            Save DAG
          </button>

          {/* Version History Button */}
          <button
            onClick={() => setShowVersionHistory(true)}
            disabled={!dag}
            style={{
              padding: '8px 16px',
              borderRadius: '4px',
              border: '1px solid #4CAF50',
              background: 'white',
              color: dag ? '#4CAF50' : '#ccc',
              cursor: dag ? 'pointer' : 'not-allowed',
              fontSize: '14px',
            }}
          >
            Version History
          </button>

          {/* Import/Export Button */}
          <button
            onClick={() => setShowImportExport(true)}
            disabled={!selectedModel}
            style={{
              padding: '8px 16px',
              borderRadius: '4px',
              border: '1px solid #2196F3',
              background: 'white',
              color: selectedModel ? '#2196F3' : '#ccc',
              cursor: selectedModel ? 'pointer' : 'not-allowed',
              fontSize: '14px',
            }}
          >
            Import/Export
          </button>
        </div>

        {/* Selection Info */}
        {(selectedNodes.length > 0 || selectedEdges.length > 0) && (
          <div
            style={{
              marginTop: '10px',
              padding: '10px 15px',
              background: '#e3f2fd',
              borderRadius: '4px',
              fontSize: '14px',
            }}
          >
            <strong>Selected:</strong>{' '}
            {selectedNodes.length > 0 && `${selectedNodes.length} node(s)`}
            {selectedNodes.length > 0 && selectedEdges.length > 0 && ', '}
            {selectedEdges.length > 0 && `${selectedEdges.length} edge(s)`}
            {highlighted.nodes.length > selectedNodes.length && (
              <span style={{ marginLeft: '10px', color: '#666' }}>
                (+ {highlighted.nodes.length - selectedNodes.length} neighbor(s) highlighted)
              </span>
            )}
          </div>
        )}

        {/* Operation Status */}
        {operationStatus && (
          <div
            style={{
              marginTop: '10px',
              padding: '10px 15px',
              background:
                operationStatus.type === 'success'
                  ? '#e8f5e9'
                  : operationStatus.type === 'error'
                    ? '#ffebee'
                    : '#e3f2fd',
              color:
                operationStatus.type === 'success'
                  ? '#2e7d32'
                  : operationStatus.type === 'error'
                    ? '#c62828'
                    : '#1565c0',
              borderRadius: '4px',
              fontSize: '14px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <span>{operationStatus.message}</span>
            <button
              onClick={() => setOperationStatus(null)}
              style={{
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                fontSize: '18px',
                padding: '0 5px',
              }}
            >
              ×
            </button>
          </div>
        )}
      </div>

      {/* Error Display */}
      {error && (
        <div
          style={{
            padding: '15px',
            background: '#ffebee',
            color: '#c62828',
            borderRadius: '4px',
            marginBottom: '20px',
          }}
        >
          {error}
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div
          style={{
            padding: '20px',
            textAlign: 'center',
            color: '#666',
          }}
        >
          Loading...
        </div>
      )}

      {/* DAG Visualization */}
      {!loading && (
        <div
          style={{ flex: 1, position: 'relative' }}
          onMouseMove={handleMouseMove}
          onMouseLeave={() => {
            setNodeTooltip(null);
            setEdgeTooltip(null);
          }}
        >
          <DAGVisualization
            dag={dag}
            onNodeSelect={handleNodeSelect}
            onEdgeSelect={handleEdgeSelect}
            selectedNodes={highlighted.nodes}
            selectedEdges={highlighted.edges}
            layout={layout}
          />

          {/* Tooltips */}
          {nodeTooltip && (
            <NodeTooltip
              nodeId={nodeTooltip.nodeId}
              statistics={{
                mean: Math.random() * 100,
                std: Math.random() * 20,
                min: Math.random() * 50,
                max: 50 + Math.random() * 100,
                count: Math.floor(Math.random() * 10000) + 1000,
              }}
              position={nodeTooltip.position}
            />
          )}

          {edgeTooltip && (
            <EdgeTooltip
              source={edgeTooltip.source}
              target={edgeTooltip.target}
              coefficient={edgeTooltip.coefficient}
              confidence={edgeTooltip.confidence}
              edgeType={edgeTooltip.edgeType}
              position={edgeTooltip.position}
            />
          )}
        </div>
      )}

      {/* DAG Info */}
      {dag && !loading && (
        <div
          style={{
            marginTop: '20px',
            padding: '15px',
            background: '#f5f5f5',
            borderRadius: '8px',
            fontSize: '13px',
          }}
        >
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '15px',
            }}
          >
            <div>
              <strong>DAG ID:</strong> {dag.dag_id.substring(0, 8)}...
            </div>
            <div>
              <strong>Algorithm:</strong> {dag.algorithm}
            </div>
            <div>
              <strong>Version:</strong> {dag.version}
            </div>
            <div>
              <strong>Created:</strong> {new Date(dag.created_at).toLocaleString()}
            </div>
            <div>
              <strong>Created By:</strong> {dag.created_by}
            </div>
          </div>
        </div>
      )}

      {/* Save DAG Dialog */}
      <SaveDAGDialog
        isOpen={showSaveDialog}
        onClose={() => setShowSaveDialog(false)}
        onSave={handleSaveDAG}
      />

      {/* Version History Dialog */}
      {selectedModel && dag && (
        <VersionHistoryDialog
          isOpen={showVersionHistory}
          onClose={() => setShowVersionHistory(false)}
          stationId={selectedModel.station_id}
          currentVersion={dag.version}
          onLoadVersion={handleLoadVersion}
        />
      )}

      {/* Import/Export Dialog */}
      {selectedModel && (
        <ImportExportDialog
          isOpen={showImportExport}
          onClose={() => setShowImportExport(false)}
          stationId={selectedModel.station_id}
          onImportSuccess={handleImportSuccess}
        />
      )}
    </div>
  );
};
