import axios, { type AxiosInstance, AxiosError, type InternalAxiosRequestConfig } from 'axios';
import type {
  HealthResponse,
  CausalDAG,
  StationModel,
  RCAReport,
  CounterfactualRequest,
  CounterfactualResponse,
  CausalEffectRequest,
  CausalEffectResponse,
  APIError,
} from '../types';

// API base URL - defaults to localhost:8000 as per design
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Create axios instance with default config
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('auth_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<APIError>) => {
    if (error.response?.status === 401) {
      // Unauthorized - clear token and redirect to login
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// API service methods
export const api = {
  // Health check
  health: async (): Promise<HealthResponse> => {
    const response = await apiClient.get<HealthResponse>('/health');
    return response.data;
  },

  // Authentication
  auth: {
    login: async (username: string, password: string) => {
      const formData = new FormData();
      formData.append('username', username);
      formData.append('password', password);
      const response = await apiClient.post('/api/v1/auth/login', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return response.data;
    },
    logout: async () => {
      await apiClient.post('/api/v1/auth/logout');
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user');
    },
  },

  // Station Models
  models: {
    list: async (): Promise<StationModel[]> => {
      const response = await apiClient.get<StationModel[]>('/api/v1/models');
      return response.data;
    },
    get: async (stationId: string): Promise<StationModel> => {
      const response = await apiClient.get<StationModel>(`/api/v1/models/${stationId}`);
      return response.data;
    },
    create: async (data: Partial<StationModel>): Promise<StationModel> => {
      const response = await apiClient.post<StationModel>('/api/v1/models', data);
      return response.data;
    },
    update: async (stationId: string, data: Partial<StationModel>): Promise<StationModel> => {
      const response = await apiClient.put<StationModel>(`/api/v1/models/${stationId}`, data);
      return response.data;
    },
    delete: async (stationId: string): Promise<void> => {
      await apiClient.delete(`/api/v1/models/${stationId}`);
    },
  },

  // Causal DAGs
  dags: {
    list: async (stationId?: string): Promise<CausalDAG[]> => {
      const params = stationId ? { station_id: stationId } : {};
      const response = await apiClient.get<CausalDAG[]>('/api/v1/dags', { params });
      return response.data;
    },
    get: async (dagId: string): Promise<CausalDAG> => {
      const response = await apiClient.get<CausalDAG>(`/api/v1/dags/${dagId}`);
      return response.data;
    },
    create: async (data: Partial<CausalDAG>): Promise<CausalDAG> => {
      const response = await apiClient.post<CausalDAG>('/api/v1/dags', data);
      return response.data;
    },
    update: async (dagId: string, data: Partial<CausalDAG>): Promise<CausalDAG> => {
      const response = await apiClient.put<CausalDAG>(`/api/v1/dags/${dagId}`, data);
      return response.data;
    },
    delete: async (dagId: string): Promise<void> => {
      await apiClient.delete(`/api/v1/dags/${dagId}`);
    },
    modifyEdges: async (
      stationId: string,
      request: {
        operations: Array<{
          operation: 'add' | 'delete' | 'reverse';
          source: string;
          target: string;
          coefficient?: number;
          confidence?: number;
          edge_type?: 'linear' | 'nonlinear';
        }>;
        created_by: string;
      }
    ) => {
      const response = await apiClient.put(`/api/v1/dags/${stationId}/edges`, request);
      return response.data;
    },
    listVersions: async (stationId: string) => {
      const response = await apiClient.get(`/api/v1/dags/${stationId}/versions`);
      return response.data;
    },
    getVersion: async (stationId: string, version: number): Promise<CausalDAG> => {
      const response = await apiClient.get<CausalDAG>(
        `/api/v1/dags/${stationId}/versions/${version}`
      );
      return response.data;
    },
  },

  // Causal Effect Estimation
  causal: {
    estimate: async (request: CausalEffectRequest): Promise<CausalEffectResponse> => {
      const response = await apiClient.post<CausalEffectResponse>(
        '/api/v1/causal/estimate',
        request
      );
      return response.data;
    },
  },

  // Counterfactual Simulation
  simulation: {
    counterfactual: async (request: CounterfactualRequest): Promise<CounterfactualResponse> => {
      const response = await apiClient.post<CounterfactualResponse>(
        '/api/v1/simulation/counterfactual',
        request
      );
      return response.data;
    },
    historicalReplay: async (
      stationId: string,
      timeRange: { start: string; end: string },
      interventions: Record<string, number>
    ) => {
      const response = await apiClient.post('/api/v1/simulation/historical-replay', {
        station_id: stationId,
        time_range: timeRange,
        interventions,
      });
      return response.data;
    },
    exportHistoricalReplay: async (
      stationId: string,
      timeRange: { start: string; end: string },
      interventions: Record<string, number>
    ) => {
      const response = await apiClient.post(
        '/api/v1/simulation/historical-replay/export',
        {
          station_id: stationId,
          time_range: timeRange,
          interventions,
        },
        { responseType: 'blob' }
      );
      return response.data;
    },
  },

  // Scenarios
  scenarios: {
    list: async (stationId?: string) => {
      const params = stationId ? { station_id: stationId } : {};
      const response = await apiClient.get('/api/v1/scenarios', { params });
      return response.data;
    },
    get: async (scenarioId: string) => {
      const response = await apiClient.get(`/api/v1/scenarios/${scenarioId}`);
      return response.data;
    },
    save: async (data: {
      station_id: string;
      name: string;
      description: string;
      interventions: Record<string, number>;
      factual_outcomes: Record<string, number>;
      counterfactual_outcomes: Record<string, number>;
      differences: Record<string, number>;
      confidence_intervals: Record<string, [number, number]>;
      created_by: string;
    }) => {
      const response = await apiClient.post('/api/v1/scenarios', data);
      return response.data;
    },
    delete: async (scenarioId: string) => {
      await apiClient.delete(`/api/v1/scenarios/${scenarioId}`);
    },
    compare: async (scenarioIds: string[]) => {
      const response = await apiClient.post('/api/v1/scenarios/compare', {
        scenario_ids: scenarioIds,
      });
      return response.data;
    },
  },

  // Root Cause Analysis
  rca: {
    get: async (anomalyId: string): Promise<RCAReport> => {
      const response = await apiClient.get<RCAReport>(`/api/v1/rca/${anomalyId}`);
      return response.data;
    },
    list: async (stationId?: string): Promise<RCAReport[]> => {
      const params = stationId ? { station_id: stationId } : {};
      const response = await apiClient.get<RCAReport[]>('/api/v1/rca', { params });
      return response.data;
    },
  },

  // Causal Discovery
  discovery: {
    start: async (stationId: string, algorithm: 'DirectLiNGAM' | 'RESIT') => {
      const response = await apiClient.post('/api/v1/discovery/start', {
        station_id: stationId,
        algorithm,
      });
      return response.data;
    },
    status: async (jobId: string) => {
      const response = await apiClient.get(`/api/v1/discovery/jobs/${jobId}`);
      return response.data;
    },
  },
};

export default apiClient;
