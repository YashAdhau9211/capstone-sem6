import React, { useMemo, useState } from 'react';
import type { CausalDAG } from '../types';
import { VariableSelector } from './VariableSelector';

interface AnalysisTemplate {
  id: string;
  name: string;
  description: string;
  icon: string;
  steps: WizardStep[];
  category: 'discovery' | 'inference' | 'simulation' | 'optimization';
}

interface WizardStep {
  title: string;
  description: string;
  guidance: string;
  component: 'variable-selection' | 'intervention-setup' | 'constraint-setup' | 'review';
}

interface AnalysisWizardProps {
  dag: CausalDAG | null;
  factualValues?: Record<string, number>;
  onComplete: (config: AnalysisConfig) => void;
  onCancel: () => void;
}

interface AnalysisConfig {
  template: string;
  variables: string[];
  interventions: Record<string, number>;
  constraints: Record<string, [number, number]>;
  objective?: string;
}

/**
 * Pre-built templates and guided wizards for common causal analysis workflows
 * Provides step-by-step guidance with natural language descriptions
 * **Validates: Requirements 15.3, 15.4, 15.5**
 */
export const AnalysisWizard: React.FC<AnalysisWizardProps> = ({
  dag,
  factualValues,
  onComplete,
  onCancel,
}) => {
  const [selectedTemplate, setSelectedTemplate] = useState<AnalysisTemplate | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [config, setConfig] = useState<AnalysisConfig>({
    template: '',
    variables: [],
    interventions: {},
    constraints: {},
  });

  const templates: AnalysisTemplate[] = [
    {
      id: 'energy-optimization',
      name: 'Energy Optimization',
      description: 'Find ways to reduce energy consumption while maintaining quality',
      icon: '⚡',
      category: 'optimization',
      steps: [
        {
          title: 'Select Energy Variable',
          description: 'Choose the variable that represents energy consumption',
          guidance:
            'Look for variables like "power_consumption", "energy_usage", or "electricity_kwh"',
          component: 'variable-selection',
        },
        {
          title: 'Set Constraints',
          description: 'Define acceptable ranges for quality and output variables',
          guidance:
            'Make sure quality metrics stay within acceptable limits while optimizing energy',
          component: 'constraint-setup',
        },
        {
          title: 'Review & Run',
          description: 'Review your configuration and run the analysis',
          guidance:
            'The system will identify which variables to adjust to reduce energy consumption',
          component: 'review',
        },
      ],
    },
    {
      id: 'yield-improvement',
      name: 'Yield Improvement',
      description: 'Identify factors that can increase production yield',
      icon: '📈',
      category: 'optimization',
      steps: [
        {
          title: 'Select Yield Variable',
          description: 'Choose the variable that represents production yield or output',
          guidance:
            'Look for variables like "yield_percentage", "output_rate", or "production_volume"',
          component: 'variable-selection',
        },
        {
          title: 'Set Constraints',
          description: 'Define acceptable ranges for cost and quality variables',
          guidance: 'Balance yield improvement with energy costs and quality requirements',
          component: 'constraint-setup',
        },
        {
          title: 'Review & Run',
          description: 'Review your configuration and run the analysis',
          guidance: 'The system will recommend adjustments to maximize yield',
          component: 'review',
        },
      ],
    },
    {
      id: 'what-if-simulation',
      name: 'What-If Simulation',
      description: 'Test the impact of changing process variables',
      icon: '🔮',
      category: 'simulation',
      steps: [
        {
          title: 'Select Variables to Change',
          description: 'Choose which process variables you want to modify',
          guidance:
            'Select variables you have control over, like temperature, pressure, or flow rate',
          component: 'variable-selection',
        },
        {
          title: 'Set New Values',
          description: 'Specify the new values for your selected variables',
          guidance: 'Try different values to see how they affect downstream outcomes',
          component: 'intervention-setup',
        },
        {
          title: 'Review & Simulate',
          description: 'Review your changes and run the simulation',
          guidance: 'The system will predict what would happen with your changes',
          component: 'review',
        },
      ],
    },
    {
      id: 'root-cause-analysis',
      name: 'Root Cause Analysis',
      description: 'Identify the root causes of quality issues or anomalies',
      icon: '🔍',
      category: 'inference',
      steps: [
        {
          title: 'Select Problem Variable',
          description: 'Choose the variable showing the quality issue or anomaly',
          guidance: 'Select the variable where you observed unexpected behavior',
          component: 'variable-selection',
        },
        {
          title: 'Review & Analyze',
          description: 'Review your selection and run the analysis',
          guidance:
            'The system will identify which upstream variables are likely causing the issue',
          component: 'review',
        },
      ],
    },
    {
      id: 'causal-discovery',
      name: 'Discover Relationships',
      description: 'Automatically discover cause-and-effect relationships in your data',
      icon: '🧠',
      category: 'discovery',
      steps: [
        {
          title: 'Select Variables',
          description: 'Choose which variables to include in the analysis',
          guidance:
            'Include all variables you think might be related. The system will find the connections.',
          component: 'variable-selection',
        },
        {
          title: 'Review & Discover',
          description: 'Review your selection and start discovery',
          guidance: 'The system will analyze your data and create a causal model',
          component: 'review',
        },
      ],
    },
  ];

  const handleTemplateSelect = (template: AnalysisTemplate) => {
    setSelectedTemplate(template);
    setConfig({ ...config, template: template.id });
    setCurrentStep(0);
  };

  const handleNext = () => {
    if (selectedTemplate && currentStep < selectedTemplate.steps.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const resolvedInterventions = useMemo(() => {
    if (config.variables.length === 0) return config.interventions;
    const next = { ...config.interventions };
    config.variables.forEach((variable) => {
      if (next[variable] === undefined) {
        const base = factualValues?.[variable] ?? 50;
        next[variable] = base;
      }
    });
    return next;
  }, [config.interventions, config.variables, factualValues]);

  const resolvedConstraints = useMemo(() => {
    if (config.variables.length === 0) return config.constraints;
    const next: Record<string, [number, number]> = { ...config.constraints };
    config.variables.forEach((variable) => {
      if (!next[variable]) {
        const base = factualValues?.[variable] ?? 50;
        next[variable] = [parseFloat((base * 0.8).toFixed(2)), parseFloat((base * 1.2).toFixed(2))];
      }
    });
    return next;
  }, [config.constraints, config.variables, factualValues]);

  const handleComplete = () => {
    onComplete({
      ...config,
      interventions: resolvedInterventions,
      constraints: resolvedConstraints,
    });
  };

  const handleInterventionChange = (variable: string, value: number) => {
    setConfig((prev) => ({ ...prev, interventions: { ...prev.interventions, [variable]: value } }));
  };

  const handleConstraintChange = (variable: string, bound: 'min' | 'max', value: number) => {
    setConfig((prev) => {
      const current = prev.constraints[variable] || [value, value];
      const next: [number, number] = bound === 'min' ? [value, current[1]] : [current[0], value];
      return { ...prev, constraints: { ...prev.constraints, [variable]: next } };
    });
  };

  const handleObjectiveChange = (objective: string) => {
    setConfig((prev) => ({ ...prev, objective }));
  };

  if (!selectedTemplate) {
    return (
      <div style={{ padding: '30px', maxWidth: '1000px', margin: '0 auto' }}>
        <div style={{ marginBottom: '30px' }}>
          <h2 style={{ margin: '0 0 10px 0' }}>Choose an Analysis Template</h2>
          <p style={{ color: '#666', fontSize: '16px', margin: 0 }}>
            Select a pre-built template to guide you through your analysis
          </p>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
            gap: '20px',
          }}
        >
          {templates.map((template) => (
            <div
              key={template.id}
              onClick={() => handleTemplateSelect(template)}
              style={{
                padding: '25px',
                border: '2px solid #e0e0e0',
                borderRadius: '8px',
                cursor: 'pointer',
                transition: 'all 0.3s',
                backgroundColor: 'white',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = '#007bff';
                e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,123,255,0.15)';
                e.currentTarget.style.transform = 'translateY(-2px)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = '#e0e0e0';
                e.currentTarget.style.boxShadow = 'none';
                e.currentTarget.style.transform = 'translateY(0)';
              }}
            >
              <div style={{ fontSize: '48px', marginBottom: '15px' }}>{template.icon}</div>
              <h3 style={{ margin: '0 0 10px 0', fontSize: '20px' }}>{template.name}</h3>
              <p
                style={{ color: '#666', fontSize: '14px', margin: '0 0 15px 0', lineHeight: '1.5' }}
              >
                {template.description}
              </p>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  color: '#007bff',
                  fontSize: '14px',
                  fontWeight: 'bold',
                }}
              >
                <span>{template.steps.length} steps</span>
                <span style={{ marginLeft: 'auto' }}>→</span>
              </div>
            </div>
          ))}
        </div>

        <div style={{ marginTop: '30px', textAlign: 'center' }}>
          <button
            onClick={onCancel}
            style={{
              padding: '12px 24px',
              backgroundColor: '#6c757d',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '16px',
            }}
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  const currentStepData = selectedTemplate.steps[currentStep];
  const isLastStep = currentStep === selectedTemplate.steps.length - 1;

  return (
    <div style={{ padding: '30px', maxWidth: '900px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '30px' }}>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '15px' }}>
          <span style={{ fontSize: '36px', marginRight: '15px' }}>{selectedTemplate.icon}</span>
          <div>
            <h2 style={{ margin: 0 }}>{selectedTemplate.name}</h2>
            <p style={{ color: '#666', margin: '5px 0 0 0' }}>
              Step {currentStep + 1} of {selectedTemplate.steps.length}
            </p>
          </div>
        </div>

        {/* Progress Bar */}
        <div
          style={{
            width: '100%',
            height: '8px',
            backgroundColor: '#e0e0e0',
            borderRadius: '4px',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              width: `${((currentStep + 1) / selectedTemplate.steps.length) * 100}%`,
              height: '100%',
              backgroundColor: '#007bff',
              transition: 'width 0.3s',
            }}
          />
        </div>
      </div>

      {/* Step Content */}
      <div style={{ marginBottom: '30px' }}>
        <h3 style={{ margin: '0 0 10px 0', fontSize: '24px' }}>{currentStepData.title}</h3>
        <p style={{ color: '#666', fontSize: '16px', margin: '0 0 20px 0' }}>
          {currentStepData.description}
        </p>

        {/* Guidance Box */}
        <div
          style={{
            padding: '15px',
            backgroundColor: '#fff3cd',
            border: '1px solid #ffc107',
            borderRadius: '4px',
            marginBottom: '25px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'flex-start' }}>
            <span style={{ fontSize: '20px', marginRight: '10px' }}>💡</span>
            <div>
              <strong style={{ display: 'block', marginBottom: '5px' }}>Tip:</strong>
              <p style={{ margin: 0, fontSize: '14px' }}>{currentStepData.guidance}</p>
            </div>
          </div>
        </div>

        {/* Step Component */}
        {currentStepData.component === 'variable-selection' && dag && (
          <VariableSelector
            dag={dag}
            selectedVariables={config.variables}
            onSelectionChange={(variables) => setConfig((prev) => ({ ...prev, variables }))}
            mode="checkbox"
            title="Select Variables"
            description="Pick the variables you want this workflow to focus on"
          />
        )}

        {currentStepData.component === 'intervention-setup' && (
          <div
            style={{
              padding: '20px',
              border: '1px solid #ddd',
              borderRadius: '8px',
              backgroundColor: '#f8f9fa',
            }}
          >
            <h4 style={{ margin: '0 0 10px 0' }}>Set New Values</h4>
            {config.variables.length === 0 && (
              <p style={{ color: '#666', margin: 0 }}>Select at least one variable first.</p>
            )}
            {config.variables.map((variable) => {
              const base = factualValues?.[variable] ?? 50;
              const min = parseFloat((base * 0.5).toFixed(2));
              const max = parseFloat((base * 1.5).toFixed(2));
              const value = resolvedInterventions[variable] ?? base;
              const step = (max - min) / 100;
              return (
                <div
                  key={variable}
                  style={{
                    marginBottom: '20px',
                    padding: '15px',
                    backgroundColor: 'white',
                    borderRadius: '6px',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      marginBottom: '8px',
                    }}
                  >
                    <strong>{variable}</strong>
                    <span style={{ color: '#666', fontSize: '12px' }}>
                      Current: {base.toFixed(2)}
                    </span>
                  </div>
                  <input
                    type="range"
                    min={min}
                    max={max}
                    step={step}
                    value={value}
                    onChange={(e) => handleInterventionChange(variable, parseFloat(e.target.value))}
                    style={{ width: '100%', cursor: 'pointer' }}
                  />
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      fontSize: '12px',
                      color: '#666',
                    }}
                  >
                    <span>{min.toFixed(2)}</span>
                    <span>{max.toFixed(2)}</span>
                  </div>
                  <div
                    style={{
                      marginTop: '10px',
                      display: 'grid',
                      gridTemplateColumns: '1fr 120px',
                      gap: '10px',
                      alignItems: 'center',
                    }}
                  >
                    <div style={{ fontSize: '13px', color: '#555' }}>
                      New value will change downstream effects in the DAG automatically.
                    </div>
                    <input
                      type="number"
                      value={value}
                      onChange={(e) => {
                        const parsed = parseFloat(e.target.value);
                        if (!Number.isNaN(parsed)) {
                          handleInterventionChange(variable, parsed);
                        }
                      }}
                      step={step}
                      style={{
                        width: '100%',
                        padding: '8px',
                        border: '1px solid #ddd',
                        borderRadius: '4px',
                        fontSize: '14px',
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {currentStepData.component === 'constraint-setup' && (
          <div
            style={{
              padding: '20px',
              border: '1px solid #ddd',
              borderRadius: '8px',
              backgroundColor: '#f8f9fa',
            }}
          >
            <h4 style={{ margin: '0 0 12px 0' }}>Set Constraints and Objective</h4>
            {config.variables.length === 0 && (
              <p style={{ color: '#666', marginBottom: '10px' }}>
                Select at least one variable to constrain.
              </p>
            )}

            {config.variables.map((variable) => {
              const base = factualValues?.[variable] ?? 50;
              const constraint = resolvedConstraints[variable] || [
                parseFloat((base * 0.8).toFixed(2)),
                parseFloat((base * 1.2).toFixed(2)),
              ];
              return (
                <div
                  key={variable}
                  style={{
                    marginBottom: '15px',
                    padding: '12px',
                    backgroundColor: 'white',
                    borderRadius: '6px',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: '8px',
                    }}
                  >
                    <strong>{variable}</strong>
                    <span style={{ color: '#666', fontSize: '12px' }}>
                      Current: {base.toFixed(2)}
                    </span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                    <label style={{ fontSize: '13px' }}>
                      Min allowed
                      <input
                        type="number"
                        value={constraint[0]}
                        onChange={(e) => {
                          const parsed = parseFloat(e.target.value);
                          if (!Number.isNaN(parsed)) {
                            handleConstraintChange(variable, 'min', parsed);
                          }
                        }}
                        style={{
                          width: '100%',
                          padding: '8px',
                          marginTop: '6px',
                          border: '1px solid #ddd',
                          borderRadius: '4px',
                        }}
                      />
                    </label>
                    <label style={{ fontSize: '13px' }}>
                      Max allowed
                      <input
                        type="number"
                        value={constraint[1]}
                        onChange={(e) => {
                          const parsed = parseFloat(e.target.value);
                          if (!Number.isNaN(parsed)) {
                            handleConstraintChange(variable, 'max', parsed);
                          }
                        }}
                        style={{
                          width: '100%',
                          padding: '8px',
                          marginTop: '6px',
                          border: '1px solid #ddd',
                          borderRadius: '4px',
                        }}
                      />
                    </label>
                  </div>
                  <p style={{ margin: '8px 0 0 0', fontSize: '12px', color: '#666' }}>
                    Keep outcomes for {variable} between these bounds while the optimizer searches
                    for solutions.
                  </p>
                </div>
              );
            })}

            <div style={{ marginTop: '10px' }}>
              <label style={{ display: 'block', marginBottom: '6px', fontWeight: 'bold' }}>
                Optimization objective
              </label>
              <select
                value={config.objective || ''}
                onChange={(e) => handleObjectiveChange(e.target.value)}
                style={{
                  padding: '10px',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  minWidth: '260px',
                }}
              >
                <option value="">Choose an objective...</option>
                <option value="minimize_energy">Minimize energy use</option>
                <option value="maximize_yield">Maximize yield/output</option>
                <option value="balance_quality">Balance quality and cost</option>
              </select>
            </div>
          </div>
        )}

        {currentStepData.component === 'review' && (
          <div
            style={{
              padding: '20px',
              border: '1px solid #ddd',
              borderRadius: '8px',
              backgroundColor: '#f8f9fa',
            }}
          >
            <h4 style={{ margin: '0 0 15px 0' }}>Configuration Summary</h4>
            <div
              style={{
                padding: '15px',
                backgroundColor: 'white',
                borderRadius: '4px',
                marginBottom: '15px',
              }}
            >
              <div style={{ marginBottom: '10px' }}>
                <strong>Template:</strong> {selectedTemplate.name}
              </div>
              <div style={{ marginBottom: '10px' }}>
                <strong>Selected Variables:</strong>{' '}
                {config.variables.length > 0 ? config.variables.join(', ') : 'None'}
              </div>
              <div>
                <strong>Interventions:</strong>{' '}
                {Object.keys(resolvedInterventions).length > 0
                  ? Object.keys(resolvedInterventions).length
                  : 'None'}
              </div>
            </div>
            <div
              style={{
                padding: '15px',
                backgroundColor: '#d4edda',
                border: '1px solid #c3e6cb',
                borderRadius: '4px',
              }}
            >
              <strong style={{ color: '#155724' }}>✓ Ready to run analysis</strong>
              <p style={{ margin: '5px 0 0 0', fontSize: '14px', color: '#155724' }}>
                {config.variables.length === 0
                  ? 'Add at least one variable to focus your analysis.'
                  : `We will run ${selectedTemplate.name.toLowerCase()} with ${config.variables.length} variable(s)`}
              </p>
              {Object.keys(resolvedInterventions).length > 0 && (
                <p style={{ margin: '5px 0 0 0', fontSize: '14px', color: '#155724' }}>
                  Planned interventions:{' '}
                  {Object.entries(resolvedInterventions)
                    .map(([variable, value]) => `${variable} → ${value.toFixed(2)}`)
                    .join(', ')}
                </p>
              )}
              {Object.keys(resolvedConstraints).length > 0 && (
                <p style={{ margin: '5px 0 0 0', fontSize: '14px', color: '#155724' }}>
                  Constraints:{' '}
                  {Object.entries(resolvedConstraints)
                    .map(
                      ([variable, [min, max]]) =>
                        `${variable} ∈ [${min.toFixed(2)}, ${max.toFixed(2)}]`
                    )
                    .join('; ')}
                </p>
              )}
              {config.objective && (
                <p style={{ margin: '5px 0 0 0', fontSize: '14px', color: '#155724' }}>
                  Objective: {config.objective.replace(/_/g, ' ')}
                </p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Navigation Buttons */}
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '15px' }}>
        <button
          onClick={() => {
            setSelectedTemplate(null);
            setCurrentStep(0);
          }}
          style={{
            padding: '12px 24px',
            backgroundColor: '#6c757d',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '16px',
          }}
        >
          ← Back to Templates
        </button>

        <div style={{ display: 'flex', gap: '15px' }}>
          {currentStep > 0 && (
            <button
              onClick={handleBack}
              style={{
                padding: '12px 24px',
                backgroundColor: '#6c757d',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '16px',
              }}
            >
              ← Previous
            </button>
          )}

          {!isLastStep ? (
            <button
              onClick={handleNext}
              disabled={
                currentStepData.component === 'variable-selection' && config.variables.length === 0
              }
              style={{
                padding: '12px 24px',
                backgroundColor:
                  config.variables.length > 0 || currentStepData.component !== 'variable-selection'
                    ? '#007bff'
                    : '#ccc',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor:
                  config.variables.length > 0 || currentStepData.component !== 'variable-selection'
                    ? 'pointer'
                    : 'not-allowed',
                fontSize: '16px',
                fontWeight: 'bold',
              }}
            >
              Next →
            </button>
          ) : (
            <button
              onClick={handleComplete}
              style={{
                padding: '12px 24px',
                backgroundColor: '#28a745',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '16px',
                fontWeight: 'bold',
              }}
            >
              Complete ✓
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
