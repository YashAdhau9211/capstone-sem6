import React from 'react';
import type { CounterfactualResponse } from '../types';

interface CounterfactualDisplayProps {
  result: CounterfactualResponse | null;
  loading: boolean;
  error: string | null;
  latency?: number | null;
  wsConnected?: boolean;
}

export const CounterfactualDisplay: React.FC<CounterfactualDisplayProps> = ({
  result,
  loading,
  error,
  latency,
  wsConnected,
}) => {
  if (loading) {
    return (
      <div
        style={{
          padding: '20px',
          border: '1px solid #ddd',
          borderRadius: '4px',
          textAlign: 'center',
        }}
      >
        <div style={{ fontSize: '18px', color: '#666' }}>
          Computing counterfactual predictions...
        </div>
        <div style={{ marginTop: '10px', fontSize: '14px', color: '#999' }}>
          Target: &lt;500ms at 95th percentile
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        style={{
          padding: '20px',
          border: '1px solid #dc3545',
          borderRadius: '4px',
          backgroundColor: '#f8d7da',
        }}
      >
        <h3 style={{ color: '#721c24', margin: '0 0 10px 0' }}>Error</h3>
        <p style={{ color: '#721c24', margin: 0 }}>{error}</p>
      </div>
    );
  }

  if (!result) {
    return (
      <div style={{ padding: '20px', border: '1px solid #ddd', borderRadius: '4px' }}>
        <h3>Counterfactual Predictions</h3>
        <p style={{ color: '#666' }}>Specify interventions to see predictions</p>
      </div>
    );
  }

  const variables = Object.keys(result.counterfactual);

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
        <h3 style={{ margin: 0 }}>Counterfactual Predictions</h3>
        <div style={{ display: 'flex', gap: '15px', alignItems: 'center' }}>
          {wsConnected !== undefined && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '12px' }}>
              <div
                style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  backgroundColor: wsConnected ? '#28a745' : '#dc3545',
                }}
              />
              <span style={{ color: '#666' }}>{wsConnected ? 'Real-time' : 'Disconnected'}</span>
            </div>
          )}
          {latency !== null && latency !== undefined && (
            <div style={{ fontSize: '12px', color: '#666' }}>
              Latency:{' '}
              <strong style={{ color: latency < 500 ? '#28a745' : '#dc3545' }}>
                {latency.toFixed(0)}ms
              </strong>
              {latency < 500 && ' ✓'}
            </div>
          )}
        </div>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ backgroundColor: '#f8f9fa', borderBottom: '2px solid #dee2e6' }}>
              <th style={{ padding: '12px', textAlign: 'left' }}>Variable</th>
              <th style={{ padding: '12px', textAlign: 'right' }}>Factual</th>
              <th style={{ padding: '12px', textAlign: 'right' }}>Counterfactual</th>
              <th style={{ padding: '12px', textAlign: 'right' }}>Difference</th>
              <th style={{ padding: '12px', textAlign: 'right' }}>95% CI</th>
            </tr>
          </thead>
          <tbody>
            {variables.map((variable) => {
              const factual = result.factual[variable] || 0;
              const counterfactual = result.counterfactual[variable];
              const difference = result.difference[variable];
              const ci = result.confidence_intervals[variable];
              const percentChange = factual !== 0 ? (difference / factual) * 100 : 0;

              const getDifferenceColor = (diff: number) => {
                if (Math.abs(diff) < 0.01) return '#6c757d';
                return diff > 0 ? '#28a745' : '#dc3545';
              };

              return (
                <tr key={variable} style={{ borderBottom: '1px solid #dee2e6' }}>
                  <td style={{ padding: '12px', fontWeight: 'bold' }}>{variable}</td>
                  <td style={{ padding: '12px', textAlign: 'right' }}>{factual.toFixed(3)}</td>
                  <td
                    style={{
                      padding: '12px',
                      textAlign: 'right',
                      fontWeight: 'bold',
                      color: '#007bff',
                    }}
                  >
                    {counterfactual.toFixed(3)}
                  </td>
                  <td
                    style={{
                      padding: '12px',
                      textAlign: 'right',
                      fontWeight: 'bold',
                      color: getDifferenceColor(difference),
                    }}
                  >
                    {difference > 0 ? '+' : ''}
                    {difference.toFixed(3)}
                    <span style={{ fontSize: '12px', marginLeft: '4px' }}>
                      ({percentChange > 0 ? '+' : ''}
                      {percentChange.toFixed(1)}%)
                    </span>
                  </td>
                  <td
                    style={{ padding: '12px', textAlign: 'right', fontSize: '12px', color: '#666' }}
                  >
                    [{ci[0].toFixed(3)}, {ci[1].toFixed(3)}]
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div
        style={{
          marginTop: '20px',
          padding: '15px',
          backgroundColor: '#e7f3ff',
          borderRadius: '4px',
        }}
      >
        <h4 style={{ margin: '0 0 10px 0', fontSize: '14px' }}>Legend</h4>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '10px',
            fontSize: '13px',
          }}
        >
          <div>
            <strong>Factual:</strong> Current/observed values
          </div>
          <div>
            <strong>Counterfactual:</strong> Predicted values with interventions
          </div>
          <div>
            <strong>Difference:</strong> Change from factual to counterfactual
          </div>
          <div>
            <strong>95% CI:</strong> Confidence interval for predictions
          </div>
        </div>
      </div>
    </div>
  );
};
