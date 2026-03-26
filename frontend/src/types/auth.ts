// User roles as defined in requirements
export type UserRole = 'Process_Engineer' | 'Plant_Manager' | 'QA_Lead' | 'Citizen_Data_Scientist';

// User permissions
export type Permission =
  | 'create_model'
  | 'edit_model'
  | 'delete_model'
  | 'run_simulation'
  | 'view_rca'
  | 'view_model'
  | 'view_reports'
  | 'configure_alerts';

// User authentication state
export interface User {
  id: string;
  username: string;
  email: string;
  role: UserRole;
  permissions: Permission[];
}

// Authentication context
export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

// Login credentials
export interface LoginCredentials {
  username: string;
  password: string;
}

// Login response
export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}
