import React, { useState, useEffect } from 'react';
import type { CausalDAG } from '../types';

interface InterventionPanelProps {
  dag: CausalDAG | null;
  factualValues: Record<string, number>;
  interventions: Record<string, number>;
  onInterventionChange: (variable: string, value: number | null) => void;
  onClearAll: () => void;
}

export const InterventionPanel: React.FC<InterventionPanelProps> = ({
  dag,
  factualValues,
  interventions,
  onInterventionChange,
  onClearAll,
}) => {
  const [selectedVariable, setSelectedVariable] = useState<string>('');

  if (!dag) {
    return (
      <div style={{ padding: '20px', border: '1px solid #ddd', borderRadius: '4px' }}>
        <h3>Intervention Specification</h3>
        <p style={{ color: '#666' }}>Select a station to begin</p>
      </div>
    );
  }

  const handleSliderChange = (variable: string, value: number) => {
    onInterventionChange(variable, value);
  };

  const handleRemoveIntervention = (variable: string) => {
    onInterventionChange(variable, null);
  };

  const availableVariables = dag.nodes.filter((node) => !interventions[node]);

  return (
    <div style={{ padding: '20px', border: '1px solid #ddd', borderRadius: '4px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h3 style={{ margin: 0 }}>Intervention Specification</h3>
        {Object.keys(interventions).length > 0 && (
          <button
            onClick={onClearAll}
            style={{
              padding: '6px 12px',
              backgroundColor: '#dc3545',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            Clear All
          </button>
        )}
      </div>

      {/* Active Interventions */}
      {Object.keys(interventions).length > 0 && (
        <div style={{ marginBottom: '20px' }}>
          <h4>Active Interventions</h4>
          {Object.entries(interventions).map(([variable, value]) => {
            const factual = factualValues[variable] || 0;
            const min = Math.min(factual * 0.5, factual * 1.5);
            const max = Math.max(factual * 0.5, factual * 1.5);
            const step = (max - min) / 100;

            return (
              <div
                key={variable}
                style={{
                  marginBottom: '15px',
                  padding: '15px',
                  backgroundColor: '#f8f9fa',
                  borderRadius: '4px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <strong>{variable}</strong>
                  <button
                    onClick={() => handleRemoveIntervention(variable)}
                    style={{
                      padding: '4px 8px',
                      backgroundColor: '#6c757d',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontSize: '12px',
                    }}
                  >
                    Remove
                  </button>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '8px' }}>
                  <div>
                    <span style={{ fontSize: '12px', color: '#666' }}>Factual:</span>
                    <div style={{ fontWeight: 'bold' }}>{factual.toFixed(2)}</div>
                  </div>
                  <div>
                    <span style={{ fontSize: '12px', color: '#666' }}>Intervention:</span>
                    <div style={{ fontWeight: 'bold', color: '#007bff' }}>{value.toFixed(2)}</div>
                  </div>
                </div>
                <input
                  type="range"
                  min={min}
                  max={max}
                  step={step}
                  value={value}
                  onChange={(e) => handleSliderChange(variable, parseFloat(e.target.value))}
                  style={{ width: '100%' }}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#666' }}>
                  <span>{min.toFixed(2)}</span>
                  <span>{max.toFixed(2)}</span>
                </div>
                <div style={{ marginTop: '8px' }}>
                  <input
                    type="number"
                    value={value}
                    onChange={(e) => handleSliderChange(variable, parseFloat(e.target.value))}
                    step={step}
                    style={{
                      width: '100%',
                      padding: '6px',
                      border: '1px solid #ddd',
                      borderRadius: '4px',
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Add New Intervention */}
      {availableVariables.length > 0 && (
        <div>
          <h4>Add Intervention</h4>
          <div style={{ display: 'flex', gap: '10px' }}>
            <select
              value={selectedVariable}
              onChange={(e) => setSelectedVariable(e.target.value)}
              style={{
                flex: 1,
                padding: '8px',
                border: '1px solid #ddd',
                borderRadius: '4px',
              }}
            >
              <option value="">Select variable...</option>
              {availableVariables.map((variable) => (
                <option key={variable} value={variable}>
                  {variable}
                </option>
              ))}
            </select>
            <button
              onClick={() => {
                if (selectedVariable) {
                  const factual = factualValues[selectedVariable] || 0;
                  onInterventionChange(selectedVariable, factual);
                  setSelectedVariable('');
                }
              }}
              disabled={!selectedVariable}
              style={{
                padding: '8px 16px',
                backgroundColor: selectedVariable ? '#007bff' : '#ccc',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: selectedVariable ? 'pointer' : 'not-allowed',
              }}
            >
              Add
            </button>
          </div>
        </div>
      )}

      {availableVariables.length === 0 && Object.keys(interventions).length === 0 && (
        <p style={{ color: '#666', fontStyle: 'italic' }}>No variables available for intervention</p>
      )}
    </div>
  );
};
