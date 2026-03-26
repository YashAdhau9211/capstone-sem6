import React from 'react';
import type { SimulationScenario } from '../types';

interface ScenarioComparisonProps {
  scenarios: SimulationScenario[];
  onClose: () => void;
}

export const ScenarioComparison: React.FC<ScenarioComparisonProps> = ({ scenarios, onClose }) => {
  if (scenarios.length < 2) {
    return null;
  }

  // Get all unique variables across scenarios
  const allVariables = new Set<string>();
  scenarios.forEach((scenario) => {
    Object.keys(scenario.counterfactual_outcomes).forEach((v) => allVariables.add(v));
  });
  const variables = Array.from(allVariables).sort();

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
      onClick={onClose}
    >
      <div
        style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          padding: '30px',
          maxWidth: '90%',
          maxHeight: '90%',
          overflow: 'auto',
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '20px',
          }}
        >
          <h2 style={{ margin: 0 }}>Scenario Comparison</h2>
          <button
            onClick={onClose}
            style={{
              padding: '8px 16px',
              backgroundColor: '#6c757d',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            Close
          </button>
        </div>

        {/* Scenario Headers */}
        <div
          style={{
            marginBottom: '20px',
            display: 'grid',
            gridTemplateColumns: `200px repeat(${scenarios.length}, 1fr)`,
            gap: '10px',
          }}
        >
          <div></div>
          {scenarios.map((scenario) => (
            <div
              key={scenario.scenario_id}
              style={{
                padding: '15px',
                backgroundColor: '#f8f9fa',
                borderRadius: '4px',
                border: '1px solid #dee2e6',
              }}
            >
              <h4 style={{ margin: '0 0 5px 0' }}>{scenario.name}</h4>
              <div style={{ fontSize: '12px', color: '#666' }}>
                {scenario.description && <div>{scenario.description}</div>}
                <div style={{ marginTop: '5px' }}>
                  {new Date(scenario.created_at).toLocaleDateString()}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Interventions Comparison */}
        <div style={{ marginBottom: '30px' }}>
          <h3>Interventions</h3>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ backgroundColor: '#f8f9fa', borderBottom: '2px solid #dee2e6' }}>
                  <th style={{ padding: '12px', textAlign: 'left' }}>Variable</th>
                  {scenarios.map((scenario) => (
                    <th key={scenario.scenario_id} style={{ padding: '12px', textAlign: 'right' }}>
                      {scenario.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Array.from(new Set(scenarios.flatMap((s) => Object.keys(s.interventions)))).map(
                  (variable) => (
                    <tr key={variable} style={{ borderBottom: '1px solid #dee2e6' }}>
                      <td style={{ padding: '12px', fontWeight: 'bold' }}>{variable}</td>
                      {scenarios.map((scenario) => (
                        <td
                          key={scenario.scenario_id}
                          style={{
                            padding: '12px',
                            textAlign: 'right',
                            color:
                              scenario.interventions[variable] !== undefined ? '#007bff' : '#999',
                          }}
                        >
                          {scenario.interventions[variable] !== undefined
                            ? scenario.interventions[variable].toFixed(3)
                            : '—'}
                        </td>
                      ))}
                    </tr>
                  )
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Outcomes Comparison */}
        <div style={{ marginBottom: '30px' }}>
          <h3>Counterfactual Outcomes</h3>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ backgroundColor: '#f8f9fa', borderBottom: '2px solid #dee2e6' }}>
                  <th style={{ padding: '12px', textAlign: 'left' }}>Variable</th>
                  {scenarios.map((scenario) => (
                    <th key={scenario.scenario_id} style={{ padding: '12px', textAlign: 'right' }}>
                      {scenario.name}
                    </th>
                  ))}
                  <th style={{ padding: '12px', textAlign: 'right' }}>Range</th>
                </tr>
              </thead>
              <tbody>
                {variables.map((variable) => {
                  const values = scenarios.map((s) => s.counterfactual_outcomes[variable] || 0);
                  const min = Math.min(...values);
                  const max = Math.max(...values);
                  const range = max - min;

                  return (
                    <tr key={variable} style={{ borderBottom: '1px solid #dee2e6' }}>
                      <td style={{ padding: '12px', fontWeight: 'bold' }}>{variable}</td>
                      {scenarios.map((scenario) => {
                        const value = scenario.counterfactual_outcomes[variable];
                        return (
                          <td
                            key={scenario.scenario_id}
                            style={{
                              padding: '12px',
                              textAlign: 'right',
                            }}
                          >
                            {value !== undefined ? value.toFixed(3) : '—'}
                          </td>
                        );
                      })}
                      <td
                        style={{
                          padding: '12px',
                          textAlign: 'right',
                          color: '#666',
                          fontSize: '12px',
                        }}
                      >
                        ±{(range / 2).toFixed(3)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Differences Comparison */}
        <div>
          <h3>Differences (vs Factual)</h3>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ backgroundColor: '#f8f9fa', borderBottom: '2px solid #dee2e6' }}>
                  <th style={{ padding: '12px', textAlign: 'left' }}>Variable</th>
                  {scenarios.map((scenario) => (
                    <th key={scenario.scenario_id} style={{ padding: '12px', textAlign: 'right' }}>
                      {scenario.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {variables.map((variable) => {
                  return (
                    <tr key={variable} style={{ borderBottom: '1px solid #dee2e6' }}>
                      <td style={{ padding: '12px', fontWeight: 'bold' }}>{variable}</td>
                      {scenarios.map((scenario) => {
                        const diff = scenario.differences[variable];
                        const getDiffColor = (d: number) => {
                          if (Math.abs(d) < 0.01) return '#6c757d';
                          return d > 0 ? '#28a745' : '#dc3545';
                        };

                        return (
                          <td
                            key={scenario.scenario_id}
                            style={{
                              padding: '12px',
                              textAlign: 'right',
                              color: diff !== undefined ? getDiffColor(diff) : '#999',
                              fontWeight: 'bold',
                            }}
                          >
                            {diff !== undefined ? `${diff > 0 ? '+' : ''}${diff.toFixed(3)}` : '—'}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        <div
          style={{
            marginTop: '20px',
            padding: '15px',
            backgroundColor: '#fff3cd',
            borderRadius: '4px',
          }}
        >
          <strong>Trade-offs Analysis:</strong>
          <p style={{ margin: '10px 0 0 0', fontSize: '14px' }}>
            Compare the differences to identify trade-offs between scenarios. Green values indicate
            improvements, red values indicate degradation. Consider which scenario best balances
            your optimization objectives.
          </p>
        </div>
      </div>
    </div>
  );
};
