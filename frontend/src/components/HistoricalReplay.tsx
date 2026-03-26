import React, { useState } from 'react';
import { api } from '../services/api';

interface HistoricalReplayProps {
  stationId: string;
  onRunReplay: (
    timeRange: { start: string; end: string },
    interventions: Record<string, number>
  ) => void;
  replayResult: any | null;
  loading: boolean;
}

export const HistoricalReplay: React.FC<HistoricalReplayProps> = ({
  stationId,
  onRunReplay,
  replayResult,
  loading,
}) => {
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [interventions, setInterventions] = useState<Record<string, number>>({});
  const [newVariable, setNewVariable] = useState('');
  const [newValue, setNewValue] = useState('');

  const handleAddIntervention = () => {
    if (newVariable && newValue) {
      setInterventions({
        ...interventions,
        [newVariable]: parseFloat(newValue),
      });
      setNewVariable('');
      setNewValue('');
    }
  };

  const handleRemoveIntervention = (variable: string) => {
    const updated = { ...interventions };
    delete updated[variable];
    setInterventions(updated);
  };

  const handleRunReplay = () => {
    if (startDate && endDate) {
      onRunReplay(
        {
          start: new Date(startDate).toISOString(),
          end: new Date(endDate).toISOString(),
        },
        interventions
      );
    }
  };

  const canRun = startDate && endDate && Object.keys(interventions).length > 0;

  return (
    <div style={{ padding: '20px', border: '1px solid #ddd', borderRadius: '4px' }}>
      <h3 style={{ marginBottom: '20px' }}>Historical Scenario Replay</h3>

      {/* Time Range Selection */}
      <div
        style={{
          marginBottom: '20px',
          padding: '15px',
          backgroundColor: '#f8f9fa',
          borderRadius: '4px',
        }}
      >
        <h4 style={{ marginTop: 0 }}>Time Range</h4>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              Start Date
            </label>
            <input
              type="datetime-local"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              style={{
                width: '100%',
                padding: '8px',
                border: '1px solid #ddd',
                borderRadius: '4px',
              }}
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              End Date
            </label>
            <input
              type="datetime-local"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              style={{
                width: '100%',
                padding: '8px',
                border: '1px solid #ddd',
                borderRadius: '4px',
              }}
            />
          </div>
        </div>
      </div>

      {/* Interventions */}
      <div
        style={{
          marginBottom: '20px',
          padding: '15px',
          backgroundColor: '#f8f9fa',
          borderRadius: '4px',
        }}
      >
        <h4 style={{ marginTop: 0 }}>Counterfactual Interventions</h4>

        {Object.keys(interventions).length > 0 && (
          <div style={{ marginBottom: '15px' }}>
            {Object.entries(interventions).map(([variable, value]) => (
              <div
                key={variable}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '10px',
                  backgroundColor: 'white',
                  borderRadius: '4px',
                  marginBottom: '8px',
                }}
              >
                <div>
                  <strong>{variable}</strong>: {value}
                </div>
                <button
                  onClick={() => handleRemoveIntervention(variable)}
                  style={{
                    padding: '4px 8px',
                    backgroundColor: '#dc3545',
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
            ))}
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr auto', gap: '10px' }}>
          <input
            type="text"
            value={newVariable}
            onChange={(e) => setNewVariable(e.target.value)}
            placeholder="Variable name"
            style={{
              padding: '8px',
              border: '1px solid #ddd',
              borderRadius: '4px',
            }}
          />
          <input
            type="number"
            value={newValue}
            onChange={(e) => setNewValue(e.target.value)}
            placeholder="Value"
            step="0.01"
            style={{
              padding: '8px',
              border: '1px solid #ddd',
              borderRadius: '4px',
            }}
          />
          <button
            onClick={handleAddIntervention}
            disabled={!newVariable || !newValue}
            style={{
              padding: '8px 16px',
              backgroundColor: newVariable && newValue ? '#007bff' : '#ccc',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: newVariable && newValue ? 'pointer' : 'not-allowed',
            }}
          >
            Add
          </button>
        </div>
      </div>

      {/* Run Button */}
      <button
        onClick={handleRunReplay}
        disabled={!canRun || loading}
        style={{
          width: '100%',
          padding: '12px',
          backgroundColor: canRun && !loading ? '#28a745' : '#ccc',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: canRun && !loading ? 'pointer' : 'not-allowed',
          fontSize: '16px',
          fontWeight: 'bold',
        }}
      >
        {loading ? 'Running Replay...' : 'Run Historical Replay'}
      </button>

      {/* Results */}
      {replayResult && (
        <div style={{ marginTop: '20px' }}>
          <h4>Replay Results</h4>

          {/* Aggregate Metrics */}
          {replayResult.aggregate_metrics && (
            <div style={{ marginBottom: '20px' }}>
              <h5>Aggregate Metrics</h5>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ backgroundColor: '#f8f9fa', borderBottom: '2px solid #dee2e6' }}>
                      <th style={{ padding: '12px', textAlign: 'left' }}>Variable</th>
                      <th style={{ padding: '12px', textAlign: 'right' }}>Mean</th>
                      <th style={{ padding: '12px', textAlign: 'right' }}>Std Dev</th>
                      <th style={{ padding: '12px', textAlign: 'right' }}>25th %ile</th>
                      <th style={{ padding: '12px', textAlign: 'right' }}>50th %ile</th>
                      <th style={{ padding: '12px', textAlign: 'right' }}>75th %ile</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(replayResult.aggregate_metrics).map(
                      ([variable, metrics]: [string, any]) => (
                        <tr key={variable} style={{ borderBottom: '1px solid #dee2e6' }}>
                          <td style={{ padding: '12px', fontWeight: 'bold' }}>{variable}</td>
                          <td style={{ padding: '12px', textAlign: 'right' }}>
                            {metrics.mean.toFixed(3)}
                          </td>
                          <td style={{ padding: '12px', textAlign: 'right' }}>
                            {metrics.std.toFixed(3)}
                          </td>
                          <td style={{ padding: '12px', textAlign: 'right' }}>
                            {metrics.p25.toFixed(3)}
                          </td>
                          <td style={{ padding: '12px', textAlign: 'right' }}>
                            {metrics.p50.toFixed(3)}
                          </td>
                          <td style={{ padding: '12px', textAlign: 'right' }}>
                            {metrics.p75.toFixed(3)}
                          </td>
                        </tr>
                      )
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Export Button */}
          <button
            onClick={async () => {
              try {
                // Export to CSV via backend API
                const blob = await api.simulation.exportHistoricalReplay(
                  stationId,
                  { start: startDate, end: endDate },
                  interventions
                );
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `historical_replay_${stationId}_${Date.now()}.csv`;
                a.click();
                window.URL.revokeObjectURL(url);
              } catch (err) {
                console.error('Failed to export CSV:', err);
              }
            }}
            style={{
              padding: '8px 16px',
              backgroundColor: '#17a2b8',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            Export to CSV
          </button>

          {/* Time Series Visualization Placeholder */}
          <div
            style={{
              marginTop: '20px',
              padding: '20px',
              backgroundColor: '#f8f9fa',
              borderRadius: '4px',
              textAlign: 'center',
            }}
          >
            <p style={{ color: '#666' }}>
              Time series visualization: Factual vs Counterfactual outcomes over time
            </p>
            <p style={{ fontSize: '12px', color: '#999' }}>
              (Chart visualization would be implemented here using a charting library like Chart.js
              or Recharts)
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
