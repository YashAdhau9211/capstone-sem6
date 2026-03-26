# Causal AI Manufacturing Platform - Frontend

React 18 + TypeScript frontend for the Causal AI Manufacturing Platform.

## Features

- **Authentication & Authorization**: OAuth 2.0 / API key authentication with role-based access control
- **Protected Routes**: Route guards based on user roles and permissions
- **API Integration**: Axios-based API client with interceptors for auth and error handling
- **Session Management**: Persistent authentication state with localStorage
- **Responsive Design**: Modern UI with React 18

## User Roles

- **Process_Engineer**: Create, edit, delete models; run simulations; view RCA
- **Plant_Manager**: View models and reports; run simulations
- **QA_Lead**: View models and RCA reports; configure alerts
- **Citizen_Data_Scientist**: Run simulations using existing models

## Tech Stack

- **React 18**: Modern React with hooks and functional components
- **TypeScript**: Type-safe development
- **Vite**: Fast build tool and dev server
- **React Router**: Client-side routing with protected routes
- **Axios**: HTTP client for API communication
- **ESLint + Prettier**: Code quality and formatting

## Directory Structure

```
src/
├── components/       # Reusable UI components
│   └── ProtectedRoute.tsx
├── contexts/         # React contexts (Auth, etc.)
│   └── AuthContext.tsx
├── hooks/            # Custom React hooks
│   └── usePermissions.ts
├── pages/            # Page components
│   ├── LoginPage.tsx
│   ├── DashboardPage.tsx
│   ├── GraphBuilderPage.tsx
│   ├── ModelsPage.tsx
│   ├── RCAPage.tsx
│   └── SimulationPage.tsx
├── services/         # API client and services
│   └── api.ts
├── types/            # TypeScript type definitions
│   ├── api.ts
│   ├── auth.ts
│   └── index.ts
├── utils/            # Utility functions
├── App.tsx           # Main app component with routing
└── main.tsx          # Application entry point
```

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Backend API running on http://localhost:8000

### Installation

```bash
npm install
```

### Development

Start the development server:

```bash
npm run dev
```

The app will be available at http://localhost:5173

### Build

Build for production:

```bash
npm run build
```

Preview production build:

```bash
npm run preview
```

### Code Quality

Run linter:

```bash
npm run lint
```

Fix linting issues:

```bash
npm run lint:fix
```

Format code:

```bash
npm run format
```

Check formatting:

```bash
npm run format:check
```

Type check:

```bash
npm run type-check
```

## Environment Variables

Create a `.env` file in the frontend directory:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## API Integration

The API client is configured in `src/services/api.ts` and includes:

- Automatic authentication token injection
- Request/response interceptors
- Error handling with automatic redirect on 401
- Type-safe API methods for all endpoints

### Example Usage

```typescript
import { api } from './services/api';

// Get station models
const models = await api.models.list();

// Run counterfactual simulation
const result = await api.simulation.counterfactual({
  station_id: 'furnace-01',
  interventions: { temperature: 1500 },
});
```

## Authentication Flow

1. User enters credentials on login page
2. Frontend sends credentials to `/api/v1/auth/login`
3. Backend validates and returns JWT token + user info
4. Frontend stores token in localStorage
5. All subsequent API requests include token in Authorization header
6. Protected routes check authentication state before rendering

## Protected Routes

Routes are protected using the `ProtectedRoute` component:

```typescript
<Route
  path="/models"
  element={
    <ProtectedRoute requiredPermissions={['view_model']}>
      <ModelsPage />
    </ProtectedRoute>
  }
/>
```

## Performance Targets

- Dashboard query latency: <500ms at 95th percentile
- Page load time: <2 seconds
- Interactive response: <100ms for user interactions

## Next Steps

The following features are planned for implementation:

1. **Graph Builder UI**: Interactive DAG visualization with React Flow or cytoscape.js
2. **Simulation Dashboard**: Real-time counterfactual analysis interface
3. **Station Models Management**: CRUD interface for causal models
4. **RCA Reports**: Anomaly analysis and root cause visualization
5. **Notifications**: Real-time alerts and event notifications
6. **Data Visualization**: Charts and graphs for time-series data
7. **Export Functionality**: PDF and Excel export for reports

## License

Proprietary - Causal AI Manufacturing Platform
