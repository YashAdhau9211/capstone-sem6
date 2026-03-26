# Demo Startup Guide

This guide will help you start the Causal AI Manufacturing Platform demo with mock data.

## Prerequisites

- Python 3.10+ installed
- Node.js 18+ installed
- Backend dependencies installed (`pip install -r requirements.txt` or using your virtual environment)
- Frontend dependencies installed (`cd frontend && npm install`)

## Recent Fixes

### ✅ Optimization Endpoints Fixed (Latest)
- Fixed "No module named 'psycopg2'" error in Yield Optimization
- Added mock data fallbacks for both Energy and Yield optimization
- Both dashboards now work correctly with realistic recommendations
- See `OPTIMIZATION_FIX.md` for details

## Quick Start

### Option 1: Using the Makefile (Recommended)

If you have `make` installed:

```bash
# Start backend (in one terminal)
make run

# Start frontend (in another terminal)
make frontend
```

### Option 2: Manual Start

#### Terminal 1: Start Backend

```bash
# Activate your virtual environment first (if using one)
# Example: source myenv/bin/activate  (Linux/Mac)
# Example: myenv\Scripts\activate     (Windows)

# Start the backend server
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

#### Terminal 2: Start Frontend

```bash
cd frontend
npm run dev
```

You should see:
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

## Testing the Backend

Before opening the UI, verify the backend is working:

```bash
# Test the API endpoints
python test_api_endpoints.py
```

This will test:
- ✅ Health check
- ✅ Login authentication
- ✅ Station models
- ✅ Causal DAGs
- ✅ Counterfactual simulation
- ✅ Root cause analysis
- ✅ Optimization recommendations

## Accessing the Application

1. Open your browser to: **http://localhost:5173**

2. Login with one of these test accounts:

   | Username | Password    | Role                      | Permissions                    |
   |----------|-------------|---------------------------|--------------------------------|
   | admin    | admin123    | Admin                     | Full access to everything      |
   | engineer | engineer123 | Process Engineer          | Create/edit/delete models      |
   | manager  | manager123  | Plant Manager             | View only                      |
   | qa       | qa123       | QA Lead                   | View RCA reports               |
   | analyst  | analyst123  | Citizen Data Scientist    | Run simulations only           |

3. After login, you'll see the dashboard with these features:

## Available Features (with Mock Data)

### 1. Station Models
- View 3 mock stations: `furnace-01`, `mill-01`, `anneal-01`
- See model status, accuracy, and drift detection
- **Mock Data**: Pre-configured with realistic manufacturing stations

### 2. Graph Builder
- Visualize causal DAGs for each station
- Interactive node-and-edge graph
- Hover tooltips showing variable details and causal coefficients
- **Mock Data**: Pre-built DAGs with 6 variables and realistic causal relationships

### 3. Simulation Dashboard
- Select a station and specify interventions
- See real-time counterfactual predictions
- Compare factual vs counterfactual outcomes
- Save and compare scenarios
- **Mock Data**: Generates realistic counterfactual predictions based on interventions

### 4. Root Cause Analysis
- View RCA reports for anomalies
- See top root causes ranked by attribution score
- View causal paths from root cause to anomaly
- See suppressed descendant alerts
- **Mock Data**: 2 pre-configured RCA reports with realistic root causes

### 5. Energy Optimization
- Get recommendations for reducing energy consumption
- See expected savings with confidence intervals
- Validate against process constraints
- **Mock Data**: Generates recommendations based on causal relationships

### 6. Yield Optimization
- Get recommendations for maximizing product yield
- See trade-offs with energy and quality
- Multi-objective optimization support
- **Mock Data**: Generates recommendations with trade-off analysis

## Mock Data Details

The platform uses mock data when the database is unavailable:

### Station Models
- **furnace-01**: Active, 92% accuracy, no drift
- **mill-01**: Active, 88% accuracy, no drift
- **anneal-01**: Drifted, 73% accuracy (was 85%), drift detected

### Causal DAGs

**Furnace-01 Variables:**
- temperature, pressure, fuel_flow, oxygen_level, yield, energy_consumption
- 6 causal edges with realistic coefficients

**Mill-01 Variables:**
- speed, force, coolant_flow, vibration, surface_quality, power_consumption
- 5 causal edges

**Anneal-01 Variables:**
- heating_rate, hold_time, cooling_rate, hardness, grain_size, energy_usage
- 5 causal edges

### RCA Reports
- **anomaly-001**: Yield anomaly in furnace-01 with 3 root causes
- **anomaly-002**: Surface quality anomaly in mill-01 with 2 root causes

## Troubleshooting

### Backend Issues

**Problem**: `ModuleNotFoundError` when starting backend
```bash
# Solution: Install dependencies
pip install -r requirements.txt
```

**Problem**: Port 8000 already in use
```bash
# Solution: Use a different port
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8001

# Update frontend/.env to match:
VITE_API_BASE_URL=http://localhost:8001
```

**Problem**: Database connection errors
```
# This is expected! The platform falls back to mock data automatically.
# You'll see warnings like "Database not available, using mock data"
# This is normal for demo mode.
```

### Frontend Issues

**Problem**: `npm: command not found`
```bash
# Solution: Install Node.js from https://nodejs.org/
```

**Problem**: Port 5173 already in use
```bash
# Solution: Vite will automatically use the next available port (5174, 5175, etc.)
# Check the terminal output for the actual URL
```

**Problem**: "Failed to fetch" errors in browser console
```bash
# Solution: Verify backend is running on http://localhost:8000
# Check frontend/.env has correct VITE_API_BASE_URL
```

**Problem**: Login fails with 401 Unauthorized
```bash
# Solution: Check you're using the correct credentials:
# Username: admin, Password: admin123
```

## API Documentation

Once the backend is running, you can access:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Demo Workflow

Here's a suggested workflow to demonstrate the platform:

1. **Login** as `admin` (admin123)

2. **View Station Models**
   - Click "Station Models" in the sidebar
   - See the 3 manufacturing stations
   - Notice `anneal-01` has drift detected

3. **Explore Causal Graph**
   - Click "Graph Builder"
   - Select `furnace-01` from dropdown
   - Hover over nodes to see variable details
   - Hover over edges to see causal coefficients
   - Pan and zoom the graph

4. **Run Simulation**
   - Click "Simulation"
   - Select `furnace-01`
   - Set intervention: `temperature = 850`
   - Click "Compute Counterfactual"
   - See predicted changes in yield and energy consumption
   - Save the scenario with a name

5. **View Root Cause Analysis**
   - Click "Root Cause Analysis"
   - View the RCA report for `anomaly-001`
   - See the top 3 root causes
   - View the causal paths

6. **Get Optimization Recommendations**
   - Click "Energy Optimization"
   - Select `furnace-01`
   - See recommendations for reducing energy consumption
   - Note the expected savings and confidence intervals

7. **Yield Optimization**
   - Click "Yield Optimization"
   - Select `furnace-01`
   - See recommendations for maximizing yield
   - View trade-offs with energy consumption

## Next Steps

This demo uses mock data. To connect to real manufacturing systems:

1. Configure ISA-95 connectors (OPC UA, ODBC, MQTT)
2. Set up PostgreSQL database
3. Set up InfluxDB/TimescaleDB for time-series data
4. Configure Redis for caching
5. Run causal discovery on real data
6. Deploy with Kubernetes for production

See the full implementation plan in `.kiro/specs/causal-ai-manufacturing-platform/tasks.md`

## Support

If you encounter issues:
1. Check the terminal output for error messages
2. Run `python test_api_endpoints.py` to verify backend
3. Check browser console for frontend errors
4. Verify all dependencies are installed
5. Ensure ports 8000 and 5173 are available

---

**Ready to demo!** 🎉

The platform is now running with realistic mock data and all features are functional.
