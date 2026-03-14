# Causal AI Manufacturing Platform

Enterprise-grade decision intelligence system for manufacturing operations using causal reasoning.

## Overview

The Causal AI Manufacturing Platform enables industrial manufacturing operations to transition from reactive, predictive analytics to proactive, prescriptive decision-making using causal reasoning. The platform analyzes cause-and-effect relationships in manufacturing processes through Directed Acyclic Graphs (DAGs) to optimize energy consumption, process efficiency, and yield while reducing mean time to resolution (MTTR) for quality issues.

## Features

- **Automated Causal Discovery**: Learn causal relationships from observational data using DirectLiNGAM and RESIT algorithms
- **Interactive Graph Editing**: Expert-in-the-loop validation and refinement of discovered causal DAGs
- **Counterfactual Simulation**: Real-time "what-if" analysis with <500ms latency
- **Automated Root Cause Analysis**: Causal attribution-based RCA with alert suppression
- **Station-Specific Models**: Support for 100+ concurrent manufacturing station models
- **Enterprise Integration**: ISA-95 compliant connectors for ERP, MES, SCADA, PLC, and IIoT systems

## Technology Stack

- **Backend**: Python 3.10+, FastAPI
- **Causal Libraries**: lingam, DoWhy, NumPy, SciPy
- **Data Processing**: Apache Kafka, Dask
- **Databases**: PostgreSQL, InfluxDB, Redis
- **Operations**: Docker, Kubernetes

## Prerequisites

- Python 3.10 or higher
- Poetry (for dependency management)
- Docker and Docker Compose (for local development)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd causal-ai-manufacturing-platform
```

2. Install dependencies using Poetry:
```bash
poetry install
```

3. Copy the example environment file:
```bash
cp .env.example .env
```

4. Start the development infrastructure:
```bash
docker-compose up -d
```

5. Verify all services are running:
```bash
docker-compose ps
```

## Development

### Running Tests

```bash
poetry run pytest
```

### Code Formatting

```bash
poetry run black src/ tests/
poetry run isort src/ tests/
```

### Linting

```bash
poetry run flake8 src/ tests/
poetry run mypy src/
```

### Running the Application

```bash
poetry run uvicorn src.main:app --reload
```

## Project Structure

```
.
├── src/                    # Source code
│   ├── data_integration/   # ISA-95 connectors and ETL
│   ├── causal_engine/      # Causal discovery and inference
│   ├── models/             # Data models and types
│   ├── api/                # FastAPI endpoints
│   └── utils/              # Utilities and helpers
├── tests/                  # Test suite
├── config/                 # Configuration files
├── scripts/                # Utility scripts
├── docker-compose.yml      # Local development infrastructure
└── pyproject.toml          # Project dependencies and configuration
```

## License

Proprietary - All rights reserved
