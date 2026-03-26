import React, { useState } from 'react';
import type { CausalDAG } from '../types';

interface VariableSelectorProps {
  dag: CausalDAG | null;
  selectedVariables: string[];
  onSelectionChange: (variables: string[]) => void;
  mode?: 'checkbox' | 'drag-drop';
  title?: string;
  description?: string;
}

/**
 * Visual variable selection interface for Citizen Data Scientists
 * Supports both checkbox and drag-and-drop modes
 * **Validates: Requirements 15.1**
 */
export const VariableSelector: React.FC<VariableSelectorProps> = ({
  dag,
  selectedVariables,
  onSelectionChange,
  mode = 'checkbox',
  title = 'Select Variables',
  description = 'Choose variables for your analysis',
}) => {
  const [draggedVariable, setDraggedVariable] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  if (!dag) {
    return (
      <div style={{ padding: '20px', border: '1px solid #ddd', borderRadius: '4px' }}>
        <h3>{title}</h3>
        <p style={{ color: '#666' }}>No causal model available. Please select a station first.</p>
      </div>
    );
  }

  const availableVariables = dag.nodes.filter(
    (node) =>
      !selectedVariables.includes(node) && node.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleCheckboxToggle = (variable: string) => {
    if (selectedVariables.includes(variable)) {
      onSelectionChange(selectedVariables.filter((v) => v !== variable));
    } else {
      onSelectionChange([...selectedVariables, variable]);
    }
  };

  const handleSelectAll = () => {
    onSelectionChange([...dag.nodes]);
  };

  const handleClearAll = () => {
    onSelectionChange([]);
  };

  const handleDragStart = (variable: string) => {
    setDraggedVariable(variable);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (draggedVariable && !selectedVariables.includes(draggedVariable)) {
      onSelectionChange([...selectedVariables, draggedVariable]);
    }
    setDraggedVariable(null);
  };

  const handleRemoveVariable = (variable: string) => {
    onSelectionChange(selectedVariables.filter((v) => v !== variable));
  };

  return (
    <div style={{ padding: '20px', border: '1px solid #ddd', borderRadius: '4px' }}>
      <div style={{ marginBottom: '15px' }}>
        <h3 style={{ margin: '0 0 8px 0' }}>{title}</h3>
        <p style={{ color: '#666', fontSize: '14px', margin: 0 }}>{description}</p>
      </div>

      {/* Search Bar */}
      <div style={{ marginBottom: '15px' }}>
        <input
          type="text"
          placeholder="Search variables..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{
            width: '100%',
            padding: '8px',
            border: '1px solid #ddd',
            borderRadius: '4px',
            fontSize: '14px',
          }}
        />
      </div>

      {/* Action Buttons */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '15px' }}>
        <button
          onClick={handleSelectAll}
          style={{
            padding: '6px 12px',
            backgroundColor: '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '14px',
          }}
        >
          Select All
        </button>
        <button
          onClick={handleClearAll}
          disabled={selectedVariables.length === 0}
          style={{
            padding: '6px 12px',
            backgroundColor: selectedVariables.length > 0 ? '#6c757d' : '#ccc',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: selectedVariables.length > 0 ? 'pointer' : 'not-allowed',
            fontSize: '14px',
          }}
        >
          Clear All
        </button>
      </div>

      {mode === 'checkbox' ? (
        /* Checkbox Mode */
        <div>
          <div style={{ marginBottom: '15px' }}>
            <h4 style={{ margin: '0 0 10px 0', fontSize: '14px', fontWeight: 'bold' }}>
              Available Variables ({availableVariables.length})
            </h4>
            <div
              style={{
                maxHeight: '200px',
                overflowY: 'auto',
                border: '1px solid #e0e0e0',
                borderRadius: '4px',
                padding: '10px',
              }}
            >
              {availableVariables.length > 0 ? (
                availableVariables.map((variable) => (
                  <label
                    key={variable}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      padding: '8px',
                      cursor: 'pointer',
                      borderRadius: '4px',
                      transition: 'background-color 0.2s',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#f8f9fa')}
                    onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                  >
                    <input
                      type="checkbox"
                      checked={selectedVariables.includes(variable)}
                      onChange={() => handleCheckboxToggle(variable)}
                      style={{ marginRight: '10px', cursor: 'pointer' }}
                    />
                    <span>{variable}</span>
                  </label>
                ))
              ) : (
                <p style={{ color: '#666', fontStyle: 'italic', margin: 0 }}>
                  {searchTerm ? 'No variables match your search' : 'All variables selected'}
                </p>
              )}
            </div>
          </div>

          {selectedVariables.length > 0 && (
            <div>
              <h4 style={{ margin: '0 0 10px 0', fontSize: '14px', fontWeight: 'bold' }}>
                Selected Variables ({selectedVariables.length})
              </h4>
              <div
                style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: '8px',
                  padding: '10px',
                  border: '1px solid #e0e0e0',
                  borderRadius: '4px',
                  minHeight: '50px',
                }}
              >
                {selectedVariables.map((variable) => (
                  <div
                    key={variable}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      padding: '6px 12px',
                      backgroundColor: '#007bff',
                      color: 'white',
                      borderRadius: '20px',
                      fontSize: '14px',
                    }}
                  >
                    <span>{variable}</span>
                    <button
                      onClick={() => handleRemoveVariable(variable)}
                      style={{
                        marginLeft: '8px',
                        background: 'none',
                        border: 'none',
                        color: 'white',
                        cursor: 'pointer',
                        fontSize: '16px',
                        padding: 0,
                        lineHeight: 1,
                      }}
                      title="Remove"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Drag-and-Drop Mode */
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
          <div>
            <h4 style={{ margin: '0 0 10px 0', fontSize: '14px', fontWeight: 'bold' }}>
              Available Variables
            </h4>
            <div
              style={{
                minHeight: '200px',
                maxHeight: '300px',
                overflowY: 'auto',
                border: '2px dashed #ddd',
                borderRadius: '4px',
                padding: '10px',
              }}
            >
              {availableVariables.map((variable) => (
                <div
                  key={variable}
                  draggable
                  onDragStart={() => handleDragStart(variable)}
                  style={{
                    padding: '10px',
                    marginBottom: '8px',
                    backgroundColor: '#f8f9fa',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    cursor: 'grab',
                    transition: 'all 0.2s',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = '#e9ecef';
                    e.currentTarget.style.transform = 'translateX(5px)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = '#f8f9fa';
                    e.currentTarget.style.transform = 'translateX(0)';
                  }}
                >
                  {variable}
                </div>
              ))}
              {availableVariables.length === 0 && (
                <p
                  style={{
                    color: '#666',
                    fontStyle: 'italic',
                    textAlign: 'center',
                    marginTop: '50px',
                  }}
                >
                  {searchTerm ? 'No variables match your search' : 'All variables selected'}
                </p>
              )}
            </div>
          </div>

          <div>
            <h4 style={{ margin: '0 0 10px 0', fontSize: '14px', fontWeight: 'bold' }}>
              Selected Variables ({selectedVariables.length})
            </h4>
            <div
              onDragOver={handleDragOver}
              onDrop={handleDrop}
              style={{
                minHeight: '200px',
                maxHeight: '300px',
                overflowY: 'auto',
                border: '2px dashed #007bff',
                borderRadius: '4px',
                padding: '10px',
                backgroundColor: selectedVariables.length === 0 ? '#f8f9fa' : 'white',
              }}
            >
              {selectedVariables.length > 0 ? (
                selectedVariables.map((variable) => (
                  <div
                    key={variable}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: '10px',
                      marginBottom: '8px',
                      backgroundColor: '#007bff',
                      color: 'white',
                      borderRadius: '4px',
                    }}
                  >
                    <span>{variable}</span>
                    <button
                      onClick={() => handleRemoveVariable(variable)}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: 'white',
                        cursor: 'pointer',
                        fontSize: '18px',
                        padding: 0,
                        lineHeight: 1,
                      }}
                      title="Remove"
                    >
                      ×
                    </button>
                  </div>
                ))
              ) : (
                <p
                  style={{
                    color: '#666',
                    fontStyle: 'italic',
                    textAlign: 'center',
                    marginTop: '50px',
                  }}
                >
                  Drag variables here to select them
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
