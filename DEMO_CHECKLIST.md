# Demo Checklist

Use this checklist to ensure everything is ready for your demo.

## Pre-Demo Setup (5 minutes)

### Backend
- [ ] Virtual environment activated (if using one)
- [ ] Backend dependencies installed (`pip install -r requirements.txt`)
- [ ] Backend server started: `python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000`
- [ ] Backend health check passes: http://localhost:8000/health
- [ ] API docs accessible: http://localhost:8000/docs

### Frontend
- [ ] Node.js installed (v18+)
- [ ] Frontend dependencies installed (`cd frontend && npm install`)
- [ ] Frontend server started: `cd frontend && npm run dev`
- [ ] Frontend accessible: http://localhost:5173
- [ ] No console errors in browser

### Verification
- [ ] Run test script: `python test_api_endpoints.py`
- [ ] All tests pass (7/7)
- [ ] Login works with admin/admin123

## Demo Flow (15-20 minutes)

### 1. Introduction (2 min)
- [ ] Explain the platform purpose
- [ ] Mention it's using mock manufacturing data
- [ ] Show the login screen

### 2. Login & Dashboard (1 min)
- [ ] Login as `admin` / `admin123`
- [ ] Show the main dashboard
- [ ] Point out the navigation sidebar

### 3. Station Models (2 min)
- [ ] Click "Station Models"
- [ ] Show 3 manufacturing stations
- [ ] Point out `anneal-01` has drift detected
- [ ] Explain model accuracy metrics

### 4. Graph Builder (3 min)
- [ ] Click "Graph Builder"
- [ ] Select `furnace-01` from dropdown
- [ ] Show the causal DAG visualization
- [ ] Hover over nodes (show variable details)
- [ ] Hover over edges (show causal coefficients)
- [ ] Explain: "This shows how variables causally affect each other"
- [ ] Pan and zoom the graph

### 5. Counterfactual Simulation (4 min)
- [ ] Click "Simulation"
- [ ] Select `furnace-01`
- [ ] Explain: "What if we change the temperature?"
- [ ] Set intervention: `temperature = 850`
- [ ] Click "Compute Counterfactual"
- [ ] Show predicted changes in yield and energy
- [ ] Explain confidence intervals
- [ ] Save the scenario with a name

### 6. Root Cause Analysis (3 min)
- [ ] Click "Root Cause Analysis"
- [ ] Show the RCA report for `anomaly-001`
- [ ] Explain the top 3 root causes
- [ ] Show attribution scores
- [ ] Show causal paths
- [ ] Explain suppressed alerts

### 7. Energy Optimization (2 min)
- [ ] Click "Energy Optimization"
- [ ] Select `furnace-01`
- [ ] Show recommendations for reducing energy
- [ ] Point out expected savings
- [ ] Explain confidence intervals
- [ ] Mention constraint validation

### 8. Yield Optimization (2 min)
- [ ] Click "Yield Optimization"
- [ ] Select `furnace-01`
- [ ] Show recommendations for maximizing yield
- [ ] Point out trade-offs with energy
- [ ] Explain multi-objective optimization

### 9. Wrap-up (1 min)
- [ ] Summarize key features
- [ ] Mention ROI potential ($2-6M/year)
- [ ] Explain next steps (pilot deployment)
- [ ] Open for questions

## Common Demo Questions & Answers

**Q: Is this using real manufacturing data?**  
A: This demo uses realistic mock data. For production, we connect to your ISA-95 systems (OPC UA, SCADA, MES, ERP) to ingest real-time data.

**Q: How long does causal discovery take?**  
A: For 50 variables with 10,000 time points, DirectLiNGAM takes <5 minutes, RESIT takes <15 minutes.

**Q: Can we edit the causal graphs?**  
A: Yes! The Graph Builder allows domain experts to add, delete, or reverse edges. The system validates that the graph remains acyclic.

**Q: How accurate are the counterfactual predictions?**  
A: Predictions include 95% confidence intervals. Accuracy depends on the quality of the causal model and historical data. We recommend validating with domain experts.

**Q: What's the ROI?**  
A: Manufacturing companies typically see $2-6M/year value from energy optimization, yield improvement, and faster root cause analysis. ROI is typically 10-30x.

**Q: How does this integrate with our existing systems?**  
A: We support standard ISA-95 protocols: OPC UA for SCADA/PLC, ODBC/JDBC for ERP/MES, and MQTT for IIoT sensors. Integration typically takes 2-4 weeks.

**Q: What about security?**  
A: This demo uses basic authentication. Production deployment includes Keycloak SSO, RBAC, MFA, audit logging, and IEC 62443 SL3 compliance.

**Q: Can non-technical users use this?**  
A: Yes! The Citizen Analyst interface provides a low-code experience with pre-built templates, guided wizards, and natural language descriptions.

**Q: What if the model drifts?**  
A: The system automatically detects model drift (>10% accuracy degradation) and alerts you within 60 seconds. You can trigger retraining manually or on a schedule.

**Q: How many stations can it handle?**  
A: The platform supports 100+ concurrent station models with independent causal structures. Each station has its own DAG and can be analyzed independently.

## Troubleshooting During Demo

### Backend Not Responding
```bash
# Check if backend is running
curl http://localhost:8000/health

# Restart backend if needed
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Not Loading
```bash
# Check if frontend is running
# Look for "Local: http://localhost:5173/" in terminal

# Restart frontend if needed
cd frontend && npm run dev
```

### Login Not Working
- Verify credentials: `admin` / `admin123`
- Check browser console for errors
- Verify backend is running on port 8000

### Graph Not Displaying
- Select a station from the dropdown first
- Check browser console for errors
- Verify DAG data is loading (check Network tab)

### Simulation Not Computing
- Verify you've selected a station
- Verify you've entered at least one intervention
- Check browser console for errors
- Verify backend `/api/v1/simulation/counterfactual` endpoint is working

## Post-Demo Follow-up

- [ ] Send demo recording (if recorded)
- [ ] Share `DEMO_STARTUP_GUIDE.md`
- [ ] Share `MVP_STATUS.md`
- [ ] Schedule follow-up meeting
- [ ] Discuss pilot deployment options
- [ ] Provide technical documentation
- [ ] Answer additional questions

## Demo Success Criteria

✅ All features demonstrated without errors  
✅ Audience understands the value proposition  
✅ Questions answered satisfactorily  
✅ Next steps agreed upon  
✅ Positive feedback received  

---

**Good luck with your demo!** 🎉

Remember: The platform is fully functional with mock data. Focus on the value proposition and use cases rather than technical implementation details.
