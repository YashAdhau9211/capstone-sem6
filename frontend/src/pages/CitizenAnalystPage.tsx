import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import type { CausalDAG, StationModel, CounterfactualResponse } from '../types';
import { VariableSelector } from '../components/VariableSelector';
import { SimpleInterventionPanel } from '../components/SimpleInterventionPanel';
import { AnalysisWizard } from '../components/AnalysisWizard';
import { ExportDialog } from '../components/ExportDialog';
import { CounterfactualDisplay } from '../components/CounterfactualDisplay';

/**
 * Low-code interface page for Citizen Data Scientists
 * Provides visual tools for causal analysis without programming expertise
 * **Validates: Requirements 15.1, 15.2, 15.3, 15.4, 15.5, 15.6**
 */
export const CitizenAnalystPage: React.FC = () => {
  const [models, setModels] = useState<StationModel[]>([]);
  const [selectedStationId, setSelectedStationId] = useState<string>('');
  const [currentDAG, setCurrentDAG] = useState<CausalDAG | null>(null);
  const [factualValues, setFactualValues] = useState<Record<string, number>>({});
  const [selectedVariables, setSelectedVariables] = useState<string[]>([]);
  const [interventions, setInterventions] = useState<Record<string, number>>({});
  const [counterfactualResult, setCounterfactualResult] = useState<CounterfactualResponse | null>(
    null
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showWizard, setShowWizard] = useState(false);
  const [showExportDialog, setShowExportDialog] = useState(false);
  const [activeView, setActiveView] = useState<'simple' | 'guided'>('simple');

  const loadModels = useCallback(async () => {
    try {
      const data = await api.models.list();
      setModels(data);
      if (data.length > 0 && !selectedStationId) {
        setSelectedStationId(data[0].station_id);
      }
    } catch (err) {
      console.error('Failed to load models:', err);
      setError('Failed to load station models');
    }
  }, [selectedStationId]);

  useEffect(() => {
    void loadModels();
  }, [loadModels]);

  useEffect(() => {
    if (selectedStationId) {
      loadDAG(selectedStationId);
    }
  }, [selectedStationId]);

  const loadDAG = async (stationId: string) => {
    try {
      const dags = await api.dags.list(stationId);
      if (dags.length > 0) {
        setCurrentDAG(dags[0]);
        // Initialize factual values (mock data - in production, fetch from time-series DB)
        const mockFactual: Record<string, number> = {};
        dags[0].nodes.forEach((node) => {
          mockFactual[node] = Math.random() * 100;
        });
        setFactualValues(mockFactual);
        setSelectedVariables([]);
        setInterventions({});
      }
    } catch (err) {
      console.error('Failed to load DAG:', err);
      setError('Failed to load causal model');
    }
  };

  const runCounterfactual = useCallback(async () => {
    if (!selectedStationId || Object.keys(interventions).length === 0) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await api.simulation.counterfactual({
        station_id: selectedStationId,
        interventions,
      });
      setCounterfactualResult(result);
    } catch (err: unknown) {
      console.error('Counterfactual simulation failed:', err);
      const apiMessage =
        err &&
        typeof err === 'object' &&
        'response' in err &&
        typeof (err as { response?: { data?: { message?: string } } }).response?.data?.message ===
          'string'
          ? (err as { response?: { data?: { message?: string } } }).response?.data?.message
          : null;
      setError(apiMessage || 'Failed to compute prediction');
      setCounterfactualResult(null);
    } finally {
      setLoading(false);
    }
  }, [interventions, selectedStationId]);

  useEffect(() => {
    if (selectedStationId && Object.keys(interventions).length > 0) {
      void runCounterfactual();
    } else {
      setCounterfactualResult(null);
    }
  }, [interventions, selectedStationId, runCounterfactual]);

  const handleInterventionChange = (variable: string, value: number | null) => {
    if (value === null) {
      const updated = { ...interventions };
      delete updated[variable];
      setInterventions(updated);
    } else {
      setInterventions({
        ...interventions,
        [variable]: value,
      });
    }
  };

  const handleClearAllInterventions = () => {
    setInterventions({});
  };

  type WizardConfig = {
    variables: string[];
    interventions?: Record<string, number>;
    constraints?: Record<string, [number, number]>;
    objective?: string;
  };

  const handleWizardComplete = (config: WizardConfig) => {
    // Apply wizard configuration
    if (config.variables.length > 0) {
      setSelectedVariables(config.variables);
    }
    if (config.interventions && Object.keys(config.interventions).length > 0) {
      setInterventions(config.interventions);
    }
    setShowWizard(false);
    setActiveView('simple');
  };

  const generateNaturalLanguageResults = (): string => {
    if (!counterfactualResult) {
      return 'Run a simulation to see predicted outcomes.';
    }

    const significantChanges = Object.entries(counterfactualResult.difference)
      .filter(([, diff]) => Math.abs(diff as number) > 0.01)
      .sort((a, b) => Math.abs(b[1] as number) - Math.abs(a[1] as number))
      .slice(0, 3);

    if (significantChanges.length === 0) {
      return 'Your interventions would have minimal impact on the system.';
    }

    const descriptions = significantChanges.map(([variable, diff]) => {
      const direction = (diff as number) > 0 ? 'increase' : 'decrease';
      const magnitude = Math.abs(diff as number);
      return `${variable} would ${direction} by ${magnitude.toFixed(2)}`;
    });

    return `Based on your changes, we predict: ${descriptions.join(', ')}.`;
  };

  return (
    <div style={{ padding: '20px', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '30px' }}>
        <h1 style={{ margin: '0 0 10px 0' }}>Simple Analysis Tool</h1>
        <p style={{ color: '#666', fontSize: '16px', margin: 0 }}>
          Test different scenarios and see predicted outcomes - no coding required
        </p>
      </div>

      {/* Station Selection */}
      <div
        style={{
          marginBottom: '25px',
          padding: '20px',
          backgroundColor: '#f8f9fa',
          borderRadius: '8px',
        }}
      >
        <label
          style={{ display: 'block', marginBottom: '10px', fontWeight: 'bold', fontSize: '16px' }}
        >
          Select Your Manufacturing Station
        </label>
        <select
          value={selectedStationId}
          onChange={(e) => setSelectedStationId(e.target.value)}
          style={{
            padding: '12px',
            border: '1px solid #ddd',
            borderRadius: '4px',
            fontSize: '16px',
            minWidth: '300px',
            cursor: 'pointer',
          }}
        >
          <option value="">Choose a station...</option>
          {models.map((model) => (
            <option key={model.station_id} value={model.station_id}>
              {model.station_id} ({model.status})
            </option>
          ))}
        </select>
      </div>

      {/* View Toggle */}
      <div style={{ marginBottom: '25px', display: 'flex', gap: '15px', alignItems: 'center' }}>
        <button
          onClick={() => setActiveView('simple')}
          style={{
            padding: '12px 24px',
            backgroundColor: activeView === 'simple' ? '#007bff' : '#f8f9fa',
            color: activeView === 'simple' ? 'white' : '#333',
            border: '1px solid #ddd',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '16px',
            fontWeight: 'bold',
          }}
        >
          Simple Mode
        </button>
        <button
          onClick={() => {
            setShowWizard(true);
            setActiveView('guided');
          }}
          style={{
            padding: '12px 24px',
            backgroundColor: activeView === 'guided' ? '#007bff' : '#f8f9fa',
            color: activeView === 'guided' ? 'white' : '#333',
            border: '1px solid #ddd',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '16px',
            fontWeight: 'bold',
          }}
        >
          Guided Wizard
        </button>
        <div style={{ marginLeft: 'auto' }}>
          <button
            onClick={() => setShowExportDialog(true)}
            disabled={!counterfactualResult}
            style={{
              padding: '12px 24px',
              backgroundColor: counterfactualResult ? '#28a745' : '#ccc',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: counterfactualResult ? 'pointer' : 'not-allowed',
              fontSize: '16px',
              fontWeight: 'bold',
            }}
          >
            📥 Export Results
          </button>
        </div>
      </div>

      {/* Wizard View */}
      {showWizard && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'white',
            zIndex: 100,
            overflowY: 'auto',
          }}
        >
          <AnalysisWizard
            dag={currentDAG}
            factualValues={factualValues}
            onComplete={handleWizardComplete}
            onCancel={() => {
              setShowWizard(false);
              setActiveView('simple');
            }}
          />
        </div>
      )}

      {/* Simple View */}
      {!showWizard && activeView === 'simple' && (
        <>
          {/* Help Box */}
          <div
            style={{
              padding: '20px',
              backgroundColor: '#fff3cd',
              border: '1px solid #ffc107',
              borderRadius: '8px',
              marginBottom: '25px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start' }}>
              <span style={{ fontSize: '32px', marginRight: '15px' }}>💡</span>
              <div>
                <h3 style={{ margin: '0 0 10px 0' }}>How to use this tool:</h3>
                <ol style={{ margin: 0, paddingLeft: '20px', lineHeight: '1.8' }}>
                  <li>Select a manufacturing station from the dropdown above</li>
                  <li>Choose variables you want to change in the intervention panel</li>
                  <li>Adjust the values using sliders or direct input</li>
                  <li>See predicted outcomes in real-time</li>
                  <li>Export your results when done</li>
                </ol>
              </div>
            </div>
          </div>

          {/* Main Content */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '20px',
              marginBottom: '25px',
            }}
          >
            {/* Intervention Panel */}
            <SimpleInterventionPanel
              dag={currentDAG}
              factualValues={factualValues}
              interventions={interventions}
              onInterventionChange={handleInterventionChange}
              onClearAll={handleClearAllInterventions}
              showNaturalLanguage={true}
            />

            {/* Results Display */}
            <CounterfactualDisplay
              result={counterfactualResult}
              loading={loading}
              error={error}
              latency={null}
              wsConnected={false}
            />
          </div>

          {/* Natural Language Results Summary */}
          {counterfactualResult && (
            <div
              style={{
                padding: '25px',
                backgroundColor: '#d4edda',
                border: '2px solid #c3e6cb',
                borderRadius: '8px',
                marginBottom: '25px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start' }}>
                <span style={{ fontSize: '32px', marginRight: '15px' }}>📊</span>
                <div>
                  <h3 style={{ margin: '0 0 10px 0', color: '#155724' }}>What This Means:</h3>
                  <p style={{ margin: 0, fontSize: '16px', lineHeight: '1.6', color: '#155724' }}>
                    {generateNaturalLanguageResults()}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Variable Selector (Optional) */}
          {currentDAG && (
            <div style={{ marginTop: '25px' }}>
              <VariableSelector
                dag={currentDAG}
                selectedVariables={selectedVariables}
                onSelectionChange={setSelectedVariables}
                mode="checkbox"
                title="Filter Variables (Optional)"
                description="Select specific variables to focus your analysis"
              />
            </div>
          )}
        </>
      )}

      {/* Export Dialog */}
      <ExportDialog
        isOpen={showExportDialog}
        onClose={() => setShowExportDialog(false)}
        data={{
          stationId: selectedStationId,
          interventions,
          result: counterfactualResult || undefined,
          analysisType: 'Counterfactual Simulation',
        }}
      />
    </div>
  );
};
