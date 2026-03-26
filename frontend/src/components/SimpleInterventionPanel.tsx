import React, { useState } from 'react';
import type { CausalDAG } from '../types';

interface SimpleInterventionPanelProps {
  dag: CausalDAG | null;
  factualValues: Record<string, number>;
  interventions: Record<string, number>;
  onInterventionChange: (variable: string, value: number | null) => void;
  onClearAll: () => void;
  showNaturalLanguage?: boolean;
}

/**
 * Simplified intervention specification interface for Citizen Data Scientists
 * Provides sliders, dropdowns, and input fields without requiring code
 * **Validates: Requirements 15.2**
 */
export const SimpleInterventionPanel: React.FC<SimpleInterventionPanelProps> = ({
  dag,
  factualValues,
  interventions,
  onInterventionChange,
  onClearAll,
  showNaturalLanguage = true,
}) => {
  const [selectedVariable, setSelectedVariable] = useState<string>('');
  const [inputMode, setInputMode] = useState<'slider' | 'input' | 'percentage'>('slider');

  if (!dag) {
    return (
      <div style={{ padding: '20px', border: '1px solid #ddd', borderRadius: '4px' }}>
        <h3>Set Interventions</h3>
        <p style={{ color: '#666' }}>Select a station to begin</p>
      </div>
    );
  }

  const handleSliderChange = (variable: string, value: number) => {
    onInterventionChange(variable, value);
  };

  const handlePercentageChange = (variable: string, percentage: number) => {
    const factual = factualValues[variable] || 0;
    const value = factual * (1 + percentage / 100);
    onInterventionChange(variable, value);
  };

  const handleRemoveIntervention = (variable: string) => {
    onInterventionChange(variable, null);
  };

  const availableVariables = dag.nodes.filter((node) => !interventions[node]);

  const generateNaturalLanguageDescription = () => {
    if (Object.keys(interventions).length === 0) {
      return 'No interventions set. Add an intervention to see what would happen if you changed a variable.';
    }

    const descriptions = Object.entries(interventions).map(([variable, value]) => {
      const factual = factualValues[variable] || 0;
      const diff = value - factual;
      const percentChange = ((diff / factual) * 100).toFixed(1);
      const direction = diff > 0 ? 'increase' : 'decrease';

      return `${variable} ${direction}s by ${Math.abs(parseFloat(percentChange))}% (from ${factual.toFixed(2)} to ${value.toFixed(2)})`;
    });

    return `You are testing what happens when: ${descriptions.join(', ')}.`;
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
        <div>
          <h3 style={{ margin: 0 }}>Set Interventions</h3>
          <p style={{ color: '#666', fontSize: '14px', margin: '5px 0 0 0' }}>
            Change variable values to see predicted outcomes
          </p>
        </div>
        {Object.keys(interventions).length > 0 && (
          <button
            onClick={onClearAll}
            style={{
              padding: '8px 16px',
              backgroundColor: '#dc3545',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px',
            }}
          >
            Clear All
          </button>
        )}
      </div>

      {/* Natural Language Description */}
      {showNaturalLanguage && (
        <div
          style={{
            padding: '15px',
            backgroundColor: '#e7f3ff',
            border: '1px solid #b3d9ff',
            borderRadius: '4px',
            marginBottom: '20px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'flex-start' }}>
            <span style={{ fontSize: '20px', marginRight: '10px' }}>💡</span>
            <div>
              <strong style={{ display: 'block', marginBottom: '5px' }}>
                What you're testing:
              </strong>
              <p style={{ margin: 0, fontSize: '14px' }}>{generateNaturalLanguageDescription()}</p>
            </div>
          </div>
        </div>
      )}

      {/* Input Mode Selector */}
      <div style={{ marginBottom: '20px' }}>
        <label
          style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold', fontSize: '14px' }}
        >
          Input Method:
        </label>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={() => setInputMode('slider')}
            style={{
              padding: '8px 16px',
              backgroundColor: inputMode === 'slider' ? '#007bff' : '#f8f9fa',
              color: inputMode === 'slider' ? 'white' : '#333',
              border: '1px solid #ddd',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px',
            }}
          >
            Slider
          </button>
          <button
            onClick={() => setInputMode('percentage')}
            style={{
              padding: '8px 16px',
              backgroundColor: inputMode === 'percentage' ? '#007bff' : '#f8f9fa',
              color: inputMode === 'percentage' ? 'white' : '#333',
              border: '1px solid #ddd',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px',
            }}
          >
            Percentage
          </button>
          <button
            onClick={() => setInputMode('input')}
            style={{
              padding: '8px 16px',
              backgroundColor: inputMode === 'input' ? '#007bff' : '#f8f9fa',
              color: inputMode === 'input' ? 'white' : '#333',
              border: '1px solid #ddd',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px',
            }}
          >
            Direct Input
          </button>
        </div>
      </div>

      {/* Active Interventions */}
      {Object.keys(interventions).length > 0 && (
        <div style={{ marginBottom: '20px' }}>
          <h4 style={{ marginBottom: '15px' }}>
            Active Interventions ({Object.keys(interventions).length})
          </h4>
          {Object.entries(interventions).map(([variable, value]) => {
            const factual = factualValues[variable] || 0;
            const min = Math.min(factual * 0.5, factual * 1.5);
            const max = Math.max(factual * 0.5, factual * 1.5);
            const step = (max - min) / 100;
            const percentChange = ((value - factual) / factual) * 100;

            return (
              <div
                key={variable}
                style={{
                  marginBottom: '20px',
                  padding: '15px',
                  backgroundColor: '#f8f9fa',
                  borderRadius: '8px',
                  border: '1px solid #e0e0e0',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '12px',
                  }}
                >
                  <strong style={{ fontSize: '16px' }}>{variable}</strong>
                  <button
                    onClick={() => handleRemoveIntervention(variable)}
                    style={{
                      padding: '6px 12px',
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

                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr 1fr',
                    gap: '10px',
                    marginBottom: '12px',
                  }}
                >
                  <div
                    style={{
                      textAlign: 'center',
                      padding: '10px',
                      backgroundColor: 'white',
                      borderRadius: '4px',
                    }}
                  >
                    <span style={{ fontSize: '12px', color: '#666', display: 'block' }}>
                      Current Value
                    </span>
                    <div style={{ fontWeight: 'bold', fontSize: '18px', marginTop: '5px' }}>
                      {factual.toFixed(2)}
                    </div>
                  </div>
                  <div
                    style={{
                      textAlign: 'center',
                      padding: '10px',
                      backgroundColor: '#007bff',
                      color: 'white',
                      borderRadius: '4px',
                    }}
                  >
                    <span style={{ fontSize: '12px', display: 'block' }}>New Value</span>
                    <div style={{ fontWeight: 'bold', fontSize: '18px', marginTop: '5px' }}>
                      {value.toFixed(2)}
                    </div>
                  </div>
                  <div
                    style={{
                      textAlign: 'center',
                      padding: '10px',
                      backgroundColor: percentChange >= 0 ? '#28a745' : '#dc3545',
                      color: 'white',
                      borderRadius: '4px',
                    }}
                  >
                    <span style={{ fontSize: '12px', display: 'block' }}>Change</span>
                    <div style={{ fontWeight: 'bold', fontSize: '18px', marginTop: '5px' }}>
                      {percentChange >= 0 ? '+' : ''}
                      {percentChange.toFixed(1)}%
                    </div>
                  </div>
                </div>

                {inputMode === 'slider' && (
                  <div>
                    <input
                      type="range"
                      min={min}
                      max={max}
                      step={step}
                      value={value}
                      onChange={(e) => handleSliderChange(variable, parseFloat(e.target.value))}
                      style={{ width: '100%', cursor: 'pointer' }}
                    />
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        fontSize: '12px',
                        color: '#666',
                        marginTop: '5px',
                      }}
                    >
                      <span>{min.toFixed(2)}</span>
                      <span>{max.toFixed(2)}</span>
                    </div>
                  </div>
                )}

                {inputMode === 'percentage' && (
                  <div>
                    <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px' }}>
                      Adjust by percentage:
                    </label>
                    <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                      <input
                        type="range"
                        min={-50}
                        max={50}
                        step={1}
                        value={percentChange}
                        onChange={(e) =>
                          handlePercentageChange(variable, parseFloat(e.target.value))
                        }
                        style={{ flex: 1, cursor: 'pointer' }}
                      />
                      <input
                        type="number"
                        value={percentChange.toFixed(1)}
                        onChange={(e) =>
                          handlePercentageChange(variable, parseFloat(e.target.value))
                        }
                        style={{
                          width: '80px',
                          padding: '6px',
                          border: '1px solid #ddd',
                          borderRadius: '4px',
                          textAlign: 'center',
                        }}
                      />
                      <span>%</span>
                    </div>
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        fontSize: '12px',
                        color: '#666',
                        marginTop: '5px',
                      }}
                    >
                      <span>-50%</span>
                      <span>+50%</span>
                    </div>
                  </div>
                )}

                {inputMode === 'input' && (
                  <div>
                    <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px' }}>
                      Enter exact value:
                    </label>
                    <input
                      type="number"
                      value={value}
                      onChange={(e) => handleSliderChange(variable, parseFloat(e.target.value))}
                      step={step}
                      style={{
                        width: '100%',
                        padding: '10px',
                        border: '1px solid #ddd',
                        borderRadius: '4px',
                        fontSize: '16px',
                      }}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Add New Intervention */}
      {availableVariables.length > 0 && (
        <div>
          <h4 style={{ marginBottom: '10px' }}>Add New Intervention</h4>
          <div style={{ display: 'flex', gap: '10px' }}>
            <select
              value={selectedVariable}
              onChange={(e) => setSelectedVariable(e.target.value)}
              style={{
                flex: 1,
                padding: '10px',
                border: '1px solid #ddd',
                borderRadius: '4px',
                fontSize: '14px',
              }}
            >
              <option value="">Select a variable to change...</option>
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
                padding: '10px 20px',
                backgroundColor: selectedVariable ? '#007bff' : '#ccc',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: selectedVariable ? 'pointer' : 'not-allowed',
                fontSize: '14px',
                fontWeight: 'bold',
              }}
            >
              Add
            </button>
          </div>
        </div>
      )}

      {availableVariables.length === 0 && Object.keys(interventions).length === 0 && (
        <p style={{ color: '#666', fontStyle: 'italic', textAlign: 'center', padding: '20px' }}>
          No variables available for intervention
        </p>
      )}
    </div>
  );
};
