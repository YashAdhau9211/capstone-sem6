import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import type { CausalDAG, StationModel, SimulationScenario, CounterfactualResponse } from '../types';
import { InterventionPanel } from '../components/InterventionPanel';
import { CounterfactualDisplay } from '../components/CounterfactualDisplay';
import { ScenarioManager } from '../components/ScenarioManager';
import { ScenarioComparison } from '../components/ScenarioComparison';
import { HistoricalReplay } from '../components/HistoricalReplay';
import { useWebSocket } from '../hooks/useWebSocket';

export const SimulationPage: React.FC = () => {
  const [models, setModels] = useState<StationModel[]>([]);
  const [selectedStationId, setSelectedStationId] = useState<string>('');
  const [currentDAG, setCurrentDAG] = useState<CausalDAG | null>(null);
  const [factualValues, setFactualValues] = useState<Record<string, number>>({});
  const [interventions, setInterventions] = useState<Record<string, number>>({});
  const [counterfactualResult, setCounterfactualResult] = useState<CounterfactualResponse | null>(
    null
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scenarios, setScenarios] = useState<SimulationScenario[]>([]);
  const [compareScenarios, setCompareScenarios] = useState<SimulationScenario[]>([]);
  const [activeTab, setActiveTab] = useState<'realtime' | 'historical'>('realtime');
  const [historicalResult, setHistoricalResult] = useState<any>(null);
  const [historicalLoading, setHistoricalLoading] = useState(false);
  const [latency, setLatency] = useState<number | null>(null);

  // WebSocket connection for real-time updates
  const wsUrl = selectedStationId
    ? `${import.meta.env.VITE_WS_URL || 'ws://localhost:8000'}/ws/simulation/${selectedStationId}`
    : null;

  const { isConnected: wsConnected } = useWebSocket(wsUrl, {
    onMessage: (message) => {
      if (
        message.type === 'counterfactual_update' &&
        message.data &&
        typeof message.data === 'object' &&
        'result' in message.data &&
        'latency_ms' in message.data
      ) {
        setCounterfactualResult(message.data.result as CounterfactualResponse);
        setLatency(message.data.latency_ms as number);
      }
    },
    onError: (error) => {
      console.error('WebSocket error:', error);
    },
  });

  // Load station models on mount
  useEffect(() => {
    loadModels();
  }, []);

  // Load DAG when station is selected
  useEffect(() => {
    if (selectedStationId) {
      loadDAG(selectedStationId);
      loadScenarios(selectedStationId);
    }
  }, [selectedStationId]);

  // Run counterfactual simulation when interventions change
  useEffect(() => {
    if (selectedStationId && Object.keys(interventions).length > 0) {
      runCounterfactual();
    } else {
      setCounterfactualResult(null);
    }
  }, [interventions, selectedStationId]);

  const loadModels = async () => {
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
  };

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
      }
    } catch (err) {
      console.error('Failed to load DAG:', err);
      setError('Failed to load causal DAG');
    }
  };

  const loadScenarios = async (stationId: string) => {
    try {
      const data = await api.scenarios.list(stationId);
      setScenarios(data);
    } catch (err) {
      console.error('Failed to load scenarios:', err);
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
    } catch (err: any) {
      console.error('Counterfactual simulation failed:', err);
      setError(err.response?.data?.message || 'Failed to compute counterfactual');
      setCounterfactualResult(null);
    } finally {
      setLoading(false);
    }
  }, [selectedStationId, interventions]);

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

  const handleSaveScenario = async (name: string, description: string) => {
    if (!counterfactualResult || !selectedStationId) return;

    try {
      await api.scenarios.save({
        station_id: selectedStationId,
        name,
        description,
        interventions,
        factual_outcomes: counterfactualResult.factual,
        counterfactual_outcomes: counterfactualResult.counterfactual,
        differences: counterfactualResult.difference,
        confidence_intervals: counterfactualResult.confidence_intervals,
        created_by: 'current_user', // In production, get from auth context
      });

      // Reload scenarios
      await loadScenarios(selectedStationId);
    } catch (err) {
      console.error('Failed to save scenario:', err);
      setError('Failed to save scenario');
    }
  };

  const handleLoadScenario = (scenario: SimulationScenario) => {
    setInterventions(scenario.interventions);
  };

  const handleDeleteScenario = async (scenarioId: string) => {
    try {
      await api.scenarios.delete(scenarioId);
      setScenarios(scenarios.filter((s) => s.scenario_id !== scenarioId));
    } catch (err) {
      console.error('Failed to delete scenario:', err);
      setError('Failed to delete scenario');
    }
  };

  const handleCompareScenarios = (scenarioIds: string[]) => {
    const selected = scenarios.filter((s) => scenarioIds.includes(s.scenario_id));
    setCompareScenarios(selected);
  };

  const handleRunHistoricalReplay = async (
    timeRange: { start: string; end: string },
    replayInterventions: Record<string, number>
  ) => {
    if (!selectedStationId) return;

    setHistoricalLoading(true);
    try {
      const result = await api.simulation.historicalReplay(
        selectedStationId,
        timeRange,
        replayInterventions
      );
      setHistoricalResult(result);
    } catch (err) {
      console.error('Historical replay failed:', err);
      setError('Failed to run historical replay');
    } finally {
      setHistoricalLoading(false);
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '1400px', margin: '0 auto' }}>
      <h1 style={{ marginBottom: '10px' }}>Counterfactual Simulation Dashboard</h1>
      <p style={{ color: '#666', marginBottom: '30px' }}>
        Run what-if scenarios and analyze counterfactual predictions
      </p>

      {/* Station Selection */}
      <div style={{ marginBottom: '20px' }}>
        <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
          Select Station
        </label>
        <select
          value={selectedStationId}
          onChange={(e) => setSelectedStationId(e.target.value)}
          style={{
            padding: '10px',
            border: '1px solid #ddd',
            borderRadius: '4px',
            fontSize: '16px',
            minWidth: '300px',
          }}
        >
          <option value="">Select a station...</option>
          {models.map((model) => (
            <option key={model.station_id} value={model.station_id}>
              {model.station_id} ({model.status})
            </option>
          ))}
        </select>
      </div>

      {/* Tabs */}
      <div style={{ marginBottom: '20px', borderBottom: '2px solid #dee2e6' }}>
        <button
          onClick={() => setActiveTab('realtime')}
          style={{
            padding: '10px 20px',
            backgroundColor: activeTab === 'realtime' ? '#007bff' : 'transparent',
            color: activeTab === 'realtime' ? 'white' : '#007bff',
            border: 'none',
            borderBottom: activeTab === 'realtime' ? '2px solid #007bff' : 'none',
            cursor: 'pointer',
            fontSize: '16px',
            fontWeight: 'bold',
          }}
        >
          Real-Time Simulation
        </button>
        <button
          onClick={() => setActiveTab('historical')}
          style={{
            padding: '10px 20px',
            backgroundColor: activeTab === 'historical' ? '#007bff' : 'transparent',
            color: activeTab === 'historical' ? 'white' : '#007bff',
            border: 'none',
            borderBottom: activeTab === 'historical' ? '2px solid #007bff' : 'none',
            cursor: 'pointer',
            fontSize: '16px',
            fontWeight: 'bold',
          }}
        >
          Historical Replay
        </button>
      </div>

      {activeTab === 'realtime' ? (
        <>
          {/* Real-Time Simulation */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 2fr',
              gap: '20px',
              marginBottom: '20px',
            }}
          >
            <InterventionPanel
              dag={currentDAG}
              factualValues={factualValues}
              interventions={interventions}
              onInterventionChange={handleInterventionChange}
              onClearAll={handleClearAllInterventions}
            />
            <CounterfactualDisplay
              result={counterfactualResult}
              loading={loading}
              error={error}
              latency={latency}
              wsConnected={wsConnected}
            />
          </div>

          {/* Scenario Management */}
          <ScenarioManager
            scenarios={scenarios}
            currentScenario={
              Object.keys(interventions).length > 0 && counterfactualResult
                ? { interventions, result: counterfactualResult }
                : null
            }
            onSaveScenario={handleSaveScenario}
            onLoadScenario={handleLoadScenario}
            onDeleteScenario={handleDeleteScenario}
            onCompareScenarios={handleCompareScenarios}
          />

          {/* Scenario Comparison Modal */}
          {compareScenarios.length >= 2 && (
            <ScenarioComparison
              scenarios={compareScenarios}
              onClose={() => setCompareScenarios([])}
            />
          )}
        </>
      ) : (
        <>
          {/* Historical Replay */}
          <HistoricalReplay
            stationId={selectedStationId}
            onRunReplay={handleRunHistoricalReplay}
            replayResult={historicalResult}
            loading={historicalLoading}
          />
        </>
      )}
    </div>
  );
};
