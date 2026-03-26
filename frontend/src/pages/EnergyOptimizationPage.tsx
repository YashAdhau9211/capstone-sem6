import React, { useState } from 'react';
import { api } from '../services/api';
import type { OptimizationRecommendation } from '../types/api';

export const EnergyOptimizationPage: React.FC = () => {
  const [stationId, setStationId] = useState('furnace-01');
  const [energyVariable, setEnergyVariable] = useState('energy_consumption');
  const [recommendations, setRecommendations] = useState<OptimizationRecommendation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.optimization.energy({
        station_id: stationId,
        energy_variable: energyVariable,
      });
      setRecommendations(response.recommendations);
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to generate recommendations');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '1400px', margin: '0 auto' }}>
      <h1>Energy Optimization Dashboard</h1>
      <p style={{ color: '#666', marginBottom: '30px' }}>
        Identify variables with causal effects on energy consumption and get recommendations for
        reducing energy usage.
      </p>

      {/* Configuration Panel */}
      <div
        style={{
          backgroundColor: '#f8f9fa',
          padding: '20px',
          borderRadius: '8px',
          marginBottom: '30px',
        }}
      >
        <h3>Configuration</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              Station ID
            </label>
            <input
              type="text"
              value={stationId}
              onChange={(e) => setStationId(e.target.value)}
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
              Energy Variable
            </label>
            <input
              type="text"
              value={energyVariable}
              onChange={(e) => setEnergyVariable(e.target.value)}
              style={{
                width: '100%',
                padding: '8px',
                border: '1px solid #ddd',
                borderRadius: '4px',
              }}
            />
          </div>
        </div>
        <button
          onClick={handleAnalyze}
          disabled={loading}
          style={{
            marginTop: '20px',
            padding: '10px 20px',
            backgroundColor: loading ? '#ccc' : '#28a745',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: loading ? 'not-allowed' : 'pointer',
            fontSize: '16px',
          }}
        >
          {loading ? 'Analyzing...' : 'Analyze Energy Optimization'}
        </button>
      </div>

      {/* Error Display */}
      {error && (
        <div
          style={{
            backgroundColor: '#f8d7da',
            color: '#721c24',
            padding: '15px',
            borderRadius: '4px',
            marginBottom: '20px',
          }}
        >
          {error}
        </div>
      )}

      {/* Recommendations Table */}
      {recommendations.length > 0 && (
        <div>
          <h2>Recommendations (Ranked by Expected Savings)</h2>
          <p style={{ color: '#666', marginBottom: '15px' }}>
            {recommendations.length} variables identified with causal effects on energy consumption
          </p>
          <div style={{ overflowX: 'auto' }}>
            <table
              style={{
                width: '100%',
                borderCollapse: 'collapse',
                backgroundColor: 'white',
                boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
              }}
            >
              <thead>
                <tr style={{ backgroundColor: '#f8f9fa' }}>
                  <th style={tableHeaderStyle}>Rank</th>
                  <th style={tableHeaderStyle}>Variable</th>
                  <th style={tableHeaderStyle}>Current Value</th>
                  <th style={tableHeaderStyle}>Recommended Value</th>
                  <th style={tableHeaderStyle}>Direction</th>
                  <th style={tableHeaderStyle}>Causal Effect</th>
                  <th style={tableHeaderStyle}>Expected Savings</th>
                  <th style={tableHeaderStyle}>95% CI</th>
                  <th style={tableHeaderStyle}>Constraints</th>
                </tr>
              </thead>
              <tbody>
                {recommendations.map((rec, index) => (
                  <tr
                    key={rec.variable}
                    style={{
                      borderBottom: '1px solid #ddd',
                      backgroundColor: rec.constraint_violated ? '#fff3cd' : 'white',
                    }}
                  >
                    <td style={tableCellStyle}>{index + 1}</td>
                    <td style={{ ...tableCellStyle, fontWeight: 'bold' }}>{rec.variable}</td>
                    <td style={tableCellStyle}>{rec.current_value.toFixed(2)}</td>
                    <td style={tableCellStyle}>{rec.recommended_value.toFixed(2)}</td>
                    <td style={tableCellStyle}>
                      <span
                        style={{
                          padding: '4px 8px',
                          borderRadius: '4px',
                          backgroundColor: rec.direction === 'decrease' ? '#d4edda' : '#cce5ff',
                          color: rec.direction === 'decrease' ? '#155724' : '#004085',
                          fontSize: '12px',
                          fontWeight: 'bold',
                        }}
                      >
                        {rec.direction.toUpperCase()}
                      </span>
                    </td>
                    <td style={tableCellStyle}>{rec.causal_effect.toFixed(4)}</td>
                    <td style={{ ...tableCellStyle, fontWeight: 'bold', color: '#28a745' }}>
                      {rec.expected_savings.toFixed(2)}
                    </td>
                    <td style={tableCellStyle}>
                      [{rec.confidence_interval[0].toFixed(2)},{' '}
                      {rec.confidence_interval[1].toFixed(2)}]
                    </td>
                    <td style={tableCellStyle}>
                      {rec.constraint_violated ? (
                        <span style={{ color: '#856404', fontWeight: 'bold' }}>⚠ Violated</span>
                      ) : (
                        <span style={{ color: '#28a745' }}>✓ OK</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Summary Statistics */}
          <div
            style={{
              marginTop: '30px',
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
              gap: '20px',
            }}
          >
            <div style={summaryCardStyle}>
              <h4 style={{ margin: '0 0 10px 0', color: '#666' }}>Total Recommendations</h4>
              <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#007bff' }}>
                {recommendations.length}
              </div>
            </div>
            <div style={summaryCardStyle}>
              <h4 style={{ margin: '0 0 10px 0', color: '#666' }}>Total Expected Savings</h4>
              <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#28a745' }}>
                {recommendations.reduce((sum, r) => sum + r.expected_savings, 0).toFixed(2)}
              </div>
            </div>
            <div style={summaryCardStyle}>
              <h4 style={{ margin: '0 0 10px 0', color: '#666' }}>Constraint Violations</h4>
              <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#ffc107' }}>
                {recommendations.filter((r) => r.constraint_violated).length}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!loading && recommendations.length === 0 && !error && (
        <div
          style={{
            textAlign: 'center',
            padding: '60px 20px',
            color: '#666',
          }}
        >
          <p style={{ fontSize: '18px' }}>
            Configure the station and energy variable above, then click "Analyze Energy
            Optimization" to get recommendations.
          </p>
        </div>
      )}
    </div>
  );
};

// Styles
const tableHeaderStyle: React.CSSProperties = {
  padding: '12px',
  textAlign: 'left',
  fontWeight: 'bold',
  borderBottom: '2px solid #dee2e6',
};

const tableCellStyle: React.CSSProperties = {
  padding: '12px',
  textAlign: 'left',
};

const summaryCardStyle: React.CSSProperties = {
  backgroundColor: 'white',
  padding: '20px',
  borderRadius: '8px',
  boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
};
