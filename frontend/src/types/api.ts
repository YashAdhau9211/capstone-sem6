// API Response Types
export interface HealthResponse {
  status: string;
  version: string;
}

export interface CausalEdge {
  source: string;
  target: string;
  coefficient: number;
  confidence: number;
  edge_type: 'linear' | 'nonlinear';
}

export interface CausalDAG {
  dag_id: string;
  station_id: string;
  version: number;
  nodes: string[];
  edges: CausalEdge[];
  algorithm: string;
  created_at: string;
  created_by: string;
  metadata: Record<string, unknown>;
}

export interface StationModel {
  model_id: string;
  station_id: string;
  current_dag_id: string;
  baseline_accuracy: number;
  last_evaluated: string;
  status: 'active' | 'drifted' | 'training' | 'archived';
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Anomaly {
  anomaly_id: string;
  station_id: string;
  variable: string;
  timestamp: string;
  value: number;
  expected_value: number;
  deviation: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
}

export interface RootCause {
  variable: string;
  attribution_score: number;
  confidence_interval: [number, number];
  causal_path: string[];
  recommended_action?: string;
}

export interface RCAReport {
  report_id: string;
  anomaly: Anomaly;
  root_causes: RootCause[];
  suppressed_alerts: Anomaly[];
  generated_at: string;
  generation_time_ms: number;
}

export interface SimulationScenario {
  scenario_id: string;
  station_id: string;
  name: string;
  description: string;
  interventions: Record<string, number>;
  factual_outcomes: Record<string, number>;
  counterfactual_outcomes: Record<string, number>;
  differences: Record<string, number>;
  confidence_intervals: Record<string, [number, number]>;
  created_by: string;
  created_at: string;
}

export interface CounterfactualRequest {
  station_id: string;
  interventions: Record<string, number>;
  time_range?: {
    start: string;
    end: string;
  };
}

export interface CounterfactualResponse {
  factual: Record<string, number>;
  counterfactual: Record<string, number>;
  difference: Record<string, number>;
  confidence_intervals: Record<string, [number, number]>;
}

export interface CausalEffectRequest {
  station_id: string;
  treatment: string;
  outcome: string;
  method?: 'linear_regression' | 'propensity_score_matching' | 'inverse_propensity_weighting';
}

export interface CausalEffectResponse {
  treatment: string;
  outcome: string;
  ate: number;
  confidence_interval: [number, number];
  method: string;
  adjustment_set: string[];
  sample_size: number;
}

export interface APIError {
  error: string;
  message: string;
  detail?: string;
  timestamp: string;
}

// Optimization Types
export interface OptimizationRecommendation {
  variable: string;
  current_value: number;
  recommended_value: number;
  direction: 'increase' | 'decrease';
  causal_effect: number;
  expected_savings: number;
  confidence_interval: [number, number];
  constraint_violated: boolean;
  adjustment_set: string[];
  energy_tradeoff?: number;
  quality_tradeoff?: number;
  weighted_score?: number;
}

export interface EnergyOptimizationRequest {
  station_id: string;
  energy_variable: string;
  constraints?: Record<string, [number, number]>;
}

export interface EnergyOptimizationResponse {
  station_id: string;
  energy_variable: string;
  recommendations: OptimizationRecommendation[];
  timestamp: string;
}

export interface YieldOptimizationRequest {
  station_id: string;
  yield_variable: string;
  energy_variable?: string;
  quality_variable?: string;
  constraints?: Record<string, [number, number]>;
  optimization_weights?: Record<string, number>;
}

export interface YieldOptimizationResponse {
  station_id: string;
  yield_variable: string;
  energy_variable?: string;
  quality_variable?: string;
  recommendations: OptimizationRecommendation[];
  timestamp: string;
}
