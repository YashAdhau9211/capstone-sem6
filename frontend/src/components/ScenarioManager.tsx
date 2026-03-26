import React, { useState } from 'react';
import type { SimulationScenario } from '../types';

interface ScenarioManagerProps {
  scenarios: SimulationScenario[];
  currentScenario: {
    interventions: Record<string, number>;
    result: any;
  } | null;
  onSaveScenario: (name: string, description: string) => void;
  onLoadScenario: (scenario: SimulationScenario) => void;
  onDeleteScenario: (scenarioId: string) => void;
  onCompareScenarios: (scenarioIds: string[]) => void;
}

export const ScenarioManager: React.FC<ScenarioManagerProps> = ({
  scenarios,
  currentScenario,
  onSaveScenario,
  onLoadScenario,
  onDeleteScenario,
  onCompareScenarios,
}) => {
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [scenarioName, setScenarioName] = useState('');
  const [scenarioDescription, setScenarioDescription] = useState('');
  const [selectedForComparison, setSelectedForComparison] = useState<Set<string>>(new Set());

  const handleSave = () => {
    if (scenarioName.trim()) {
      onSaveScenario(scenarioName, scenarioDescription);
      setScenarioName('');
      setScenarioDescription('');
      setShowSaveDialog(false);
    }
  };

  const toggleComparisonSelection = (scenarioId: string) => {
    const newSelection = new Set(selectedForComparison);
    if (newSelection.has(scenarioId)) {
      newSelection.delete(scenarioId);
    } else {
      newSelection.add(scenarioId);
    }
    setSelectedForComparison(newSelection);
  };

  const handleCompare = () => {
    if (selectedForComparison.size >= 2) {
      onCompareScenarios(Array.from(selectedForComparison));
    }
  };

  return (
    <div style={{ padding: '20px', border: '1px solid #ddd', borderRadius: '4px' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '20px',
        }}
      >
        <h3 style={{ margin: 0 }}>Scenario Management</h3>
        <div style={{ display: 'flex', gap: '10px' }}>
          {selectedForComparison.size >= 2 && (
            <button
              onClick={handleCompare}
              style={{
                padding: '8px 16px',
                backgroundColor: '#17a2b8',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              Compare ({selectedForComparison.size})
            </button>
          )}
          <button
            onClick={() => setShowSaveDialog(true)}
            disabled={!currentScenario}
            style={{
              padding: '8px 16px',
              backgroundColor: currentScenario ? '#28a745' : '#ccc',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: currentScenario ? 'pointer' : 'not-allowed',
            }}
          >
            Save Current
          </button>
        </div>
      </div>

      {/* Save Dialog */}
      {showSaveDialog && (
        <div
          style={{
            marginBottom: '20px',
            padding: '15px',
            backgroundColor: '#f8f9fa',
            borderRadius: '4px',
            border: '1px solid #dee2e6',
          }}
        >
          <h4 style={{ marginTop: 0 }}>Save Scenario</h4>
          <div style={{ marginBottom: '10px' }}>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              Name *
            </label>
            <input
              type="text"
              value={scenarioName}
              onChange={(e) => setScenarioName(e.target.value)}
              placeholder="e.g., High Temperature Test"
              style={{
                width: '100%',
                padding: '8px',
                border: '1px solid #ddd',
                borderRadius: '4px',
              }}
            />
          </div>
          <div style={{ marginBottom: '15px' }}>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              Description
            </label>
            <textarea
              value={scenarioDescription}
              onChange={(e) => setScenarioDescription(e.target.value)}
              placeholder="Optional description of this scenario"
              rows={3}
              style={{
                width: '100%',
                padding: '8px',
                border: '1px solid #ddd',
                borderRadius: '4px',
                resize: 'vertical',
              }}
            />
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              onClick={handleSave}
              disabled={!scenarioName.trim()}
              style={{
                padding: '8px 16px',
                backgroundColor: scenarioName.trim() ? '#28a745' : '#ccc',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: scenarioName.trim() ? 'pointer' : 'not-allowed',
              }}
            >
              Save
            </button>
            <button
              onClick={() => {
                setShowSaveDialog(false);
                setScenarioName('');
                setScenarioDescription('');
              }}
              style={{
                padding: '8px 16px',
                backgroundColor: '#6c757d',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Saved Scenarios List */}
      {scenarios.length === 0 ? (
        <p style={{ color: '#666', fontStyle: 'italic' }}>No saved scenarios yet</p>
      ) : (
        <div style={{ display: 'grid', gap: '10px' }}>
          {scenarios.map((scenario) => (
            <div
              key={scenario.scenario_id}
              style={{
                padding: '15px',
                border: '1px solid #dee2e6',
                borderRadius: '4px',
                backgroundColor: selectedForComparison.has(scenario.scenario_id)
                  ? '#e7f3ff'
                  : 'white',
              }}
            >
              <div
                style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}
              >
                <div style={{ flex: 1 }}>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px',
                      marginBottom: '5px',
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={selectedForComparison.has(scenario.scenario_id)}
                      onChange={() => toggleComparisonSelection(scenario.scenario_id)}
                      style={{ cursor: 'pointer' }}
                    />
                    <h4 style={{ margin: 0 }}>{scenario.name}</h4>
                  </div>
                  {scenario.description && (
                    <p style={{ margin: '5px 0', color: '#666', fontSize: '14px' }}>
                      {scenario.description}
                    </p>
                  )}
                  <div style={{ fontSize: '12px', color: '#999', marginTop: '5px' }}>
                    <div>Interventions: {Object.keys(scenario.interventions).join(', ')}</div>
                    <div>Created: {new Date(scenario.created_at).toLocaleString()}</div>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '5px' }}>
                  <button
                    onClick={() => onLoadScenario(scenario)}
                    style={{
                      padding: '6px 12px',
                      backgroundColor: '#007bff',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontSize: '12px',
                    }}
                  >
                    Load
                  </button>
                  <button
                    onClick={() => onDeleteScenario(scenario.scenario_id)}
                    style={{
                      padding: '6px 12px',
                      backgroundColor: '#dc3545',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontSize: '12px',
                    }}
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
