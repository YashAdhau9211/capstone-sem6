import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import {
  LoginPage,
  DashboardPage,
  UnauthorizedPage,
  NotFoundPage,
  GraphBuilderPage,
  ModelsPage,
  RCAPage,
  SimulationPage,
  EnergyOptimizationPage,
  YieldOptimizationPage,
  CitizenAnalystPage,
} from './pages';

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/unauthorized" element={<UnauthorizedPage />} />

          {/* Protected routes */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />

          <Route
            path="/models"
            element={
              <ProtectedRoute requiredPermissions={['view_model']}>
                <ModelsPage />
              </ProtectedRoute>
            }
          />

          <Route
            path="/graph-builder"
            element={
              <ProtectedRoute requiredPermissions={['view_model']}>
                <GraphBuilderPage />
              </ProtectedRoute>
            }
          />

          <Route
            path="/simulation"
            element={
              <ProtectedRoute requiredPermissions={['run_simulation']}>
                <SimulationPage />
              </ProtectedRoute>
            }
          />

          <Route
            path="/rca"
            element={
              <ProtectedRoute requiredPermissions={['view_rca']}>
                <RCAPage />
              </ProtectedRoute>
            }
          />

          <Route
            path="/energy-optimization"
            element={
              <ProtectedRoute requiredPermissions={['view_model']}>
                <EnergyOptimizationPage />
              </ProtectedRoute>
            }
          />

          <Route
            path="/yield-optimization"
            element={
              <ProtectedRoute requiredPermissions={['view_model']}>
                <YieldOptimizationPage />
              </ProtectedRoute>
            }
          />

          <Route
            path="/citizen-analyst"
            element={
              <ProtectedRoute requiredPermissions={['run_simulation']}>
                <CitizenAnalystPage />
              </ProtectedRoute>
            }
          />

          {/* Default redirect */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />

          {/* 404 */}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
