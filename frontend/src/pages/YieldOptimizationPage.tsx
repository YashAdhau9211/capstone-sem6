import React, { useState } from 'react';
import { api } from '../services/api';
import type { OptimizationRecommendation } from '../types/api';

export const YieldOptimizationPage: React.FC = () => {
  const [stationId, setStationId] = useState('furnace-01');
  const [yieldVariable, setYieldVariable] = useState('yield');
  const [energyVariable, setEnergyVariable] = useState('energy_consumption');
  const [qualityVariable, setQualityVariable] = useState('quality_score');
  const [includeTradeoffs, setIncludeTradeoffs] = useState(true);
  const [yieldWeight, setYieldWeight] = useState(1.0);
  const [energyWeight, setEnergyWeight] = useState(0.3);
  const [qualityWeight, setQualityWeight] = useState(0.3);
  const [recommendations, setRecommendations] = useState<OptimizationRecommendation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.optimization.yield({
        station_id: stationId,
        yield_variable: yieldVariable,
        energy_variable: includeTradeoffs ? energyVariable : undefined,
        quality_variable: includeTradeoffs ? qualityVariable : undefined,
        optimization_weights:
          includeTradeoffs && (energyWeight > 0 || qualityWeight > 0)
            ? {
                yield: yieldWeight,
                energy: energyWeight,
                quality: qualityWeight,
              }
            : undefined,
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
      <h1>Yield Optimization Dashboard</h1>
      <p style={{ color: '#666', marginBottom: '30px' }}>
        Identify variables with causal effects on yield and get recommendations for maximizing
        production output with trade-off analysis.
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
              style={inputStyle}
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
              Yield Variable
            </label>
            <input
              type="text"
              value={yieldVariable}
              onChange={(e) => setYieldVariable(e.target.value)}
              style={inputStyle}
            />
          </div>
        </div>

        {/* Trade-off Analysis */}
        <div style={{ marginTop: '20px' }}>
          <label style={{ display: 'flex', alignItems: 'center', marginBottom: '15px' }}>
            <input
              type="checkbox"
              checked={includeTradeoffs}
              onChange={(e) => setIncludeTradeoffs(e.target.checked)}
              style={{ marginRight: '8px' }}
            />
            <span style={{ fontWeight: 'bold' }}>Include Trade-off Analysis</span>
          </label>

          {includeTradeoffs && (
            <div
              style={{
                backgroundColor: 'white',
                padding: '15px',
                borderRadius: '4px',
                border: '1px solid #ddd',
              }}
            >
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                    Energy Variable
                  </label>
                  <input
                    type="text"
                    value={energyVariable}
                    onChange={(e) => setEnergyVariable(e.target.value)}
                    style={inputStyle}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                    Quality Variable
                  </label>
                  <input
                    type="text"
                    value={qualityVariable}
                    onChange={(e) => setQualityVariable(e.target.value)}
                    style={inputStyle}
                  />
                </div>
              </div>

              {/* Multi-objective Weights */}
              <div style={{ marginTop: '20px' }}>
                <h4 style={{ marginBottom: '10px' }}>Multi-Objective Optimization Weights</h4>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '15px' }}>
                  <div>
                    <label style={{ display: 'block', marginBottom: '5px' }}>
                      Yield Weight: {yieldWeight.toFixed(1)}
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.1"
                      value={yieldWeight}
                      onChange={(e) => setYieldWeight(parseFloat(e.target.value))}
                      style={{ width: '100%' }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', marginBottom: '5px' }}>
                      Energy Weight: {energyWeight.toFixed(1)}
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.1"
                      value={energyWeight}
                      onChange={(e) => setEnergyWeight(parseFloat(e.target.value))}
                      style={{ width: '100%' }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', marginBottom: '5px' }}>
                      Quality Weight: {qualityWeight.toFixed(1)}
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.1"
                      value={qualityWeight}
                      onChange={(e) => setQualityWeight(parseFloat(e.target.value))}
                      style={{ width: '100%' }}
                    />
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        <button
          onClick={handleAnalyze}
          disabled={loading}
          style={{
            marginTop: '20px',
            padding: '10px 20px',
            backgroundColor: loading ? '#ccc' : '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: loading ? 'not-allowed' : 'pointer',
            fontSize: '16px',
          }}
        >
          {loading ? 'Analyzing...' : 'Analyze Yield Optimization'}
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
          <h2>Recommendations (Ranked by Expected Improvement)</h2>
          <p style={{ color: '#666', marginBottom: '15px' }}>
            {recommendations.length} variables identified with causal effects on yield
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
                  <th style={tableHeaderStyle}>Yield Effect</th>
                  <th style={tableHeaderStyle}>Expected Improvement</th>
                  <th style={tableHeaderStyle}>95% CI</th>
                  {includeTradeoffs && <th style={tableHeaderStyle}>Energy Trade-off</th>}
                  {includeTradeoffs && <th style={tableHeaderStyle}>Quality Trade-off</th>}
                  {includeTradeoffs && energyWeight + qualityWeight > 0 && (
                    <th style={tableHeaderStyle}>Weighted Score</th>
                  )}
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
                          backgroundColor: rec.direction === 'increase' ? '#d4edda' : '#cce5ff',
                          color: rec.direction === 'increase' ? '#155724' : '#004085',
                          fontSize: '12px',
                          fontWeight: 'bold',
                        }}
                      >
                        {rec.direction.toUpperCase()}
                      </span>
                    </td>
                    <td style={tableCellStyle}>{rec.causal_effect.toFixed(4)}</td>
                    <td style={{ ...tableCellStyle, fontWeight: 'bold', color: '#007bff' }}>
                      {rec.expected_savings.toFixed(2)}
                    </td>
                    <td style={tableCellStyle}>
                      [{rec.confidence_interval[0].toFixed(2)},{' '}
                      {rec.confidence_interval[1].toFixed(2)}]
                    </td>
                    {includeTradeoffs && (
                      <td
                        style={{
                          ...tableCellStyle,
                          color:
                            rec.energy_tradeoff && rec.energy_tradeoff < 0 ? '#28a745' : '#dc3545',
                        }}
                      >
                        {rec.energy_tradeoff !== null && rec.energy_tradeoff !== undefined
                          ? rec.energy_tradeoff.toFixed(4)
                          : 'N/A'}
                      </td>
                    )}
                    {includeTradeoffs && (
                      <td
                        style={{
                          ...tableCellStyle,
                          color:
                            rec.quality_tradeoff && rec.quality_tradeoff > 0
                              ? '#28a745'
                              : '#dc3545',
                        }}
                      >
                        {rec.quality_tradeoff !== null && rec.quality_tradeoff !== undefined
                          ? rec.quality_tradeoff.toFixed(4)
                          : 'N/A'}
                      </td>
                    )}
                    {includeTradeoffs && energyWeight + qualityWeight > 0 && (
                      <td style={{ ...tableCellStyle, fontWeight: 'bold' }}>
                        {rec.weighted_score?.toFixed(4) || 'N/A'}
                      </td>
                    )}
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
              <h4 style={{ margin: '0 0 10px 0', color: '#666' }}>Total Expected Improvement</h4>
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
            Configure the station and yield variable above, then click "Analyze Yield Optimization"
            to get recommendations.
          </p>
        </div>
      )}
    </div>
  );
};

// Styles
const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '8px',
  border: '1px solid #ddd',
  borderRadius: '4px',
};

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
