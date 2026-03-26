# Development commands for Windows PowerShell

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

function Show-Help {
    Write-Host "Causal AI Manufacturing Platform - Development Commands" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Available commands:"
    Write-Host "  .\scripts\dev-commands.ps1 install        - Install dependencies using Poetry"
    Write-Host "  .\scripts\dev-commands.ps1 docker-up      - Start Docker services"
    Write-Host "  .\scripts\dev-commands.ps1 docker-down    - Stop Docker services"
    Write-Host "  .\scripts\dev-commands.ps1 setup-keycloak - Configure Keycloak"
    Write-Host "  .\scripts\dev-commands.ps1 setup-influxdb - Configure InfluxDB"
    Write-Host "  .\scripts\dev-commands.ps1 mock-data      - Generate mock data"
    Write-Host "  .\scripts\dev-commands.ps1 test           - Run tests"
    Write-Host "  .\scripts\dev-commands.ps1 lint           - Run linting"
    Write-Host "  .\scripts\dev-commands.ps1 format         - Format code"
    Write-Host "  .\scripts\dev-commands.ps1 clean          - Clean build artifacts"
    Write-Host "  .\scripts\dev-commands.ps1 run            - Start API server"
}

function Install-Dependencies {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    poetry install
}

function Start-Docker {
    Write-Host "Starting Docker services..." -ForegroundColor Yellow
    docker-compose up -d
    Write-Host "✓ Docker services started" -ForegroundColor Green
    Write-Host ""
    Write-Host "Services:"
    Write-Host "  - PostgreSQL: localhost:5432"
    Write-Host "  - Redis: localhost:6379"
    Write-Host "  - InfluxDB: localhost:8086"
    Write-Host "  - Kafka: localhost:9092"
    Write-Host "  - Keycloak: localhost:8080"
}

function Stop-Docker {
    Write-Host "Stopping Docker services..." -ForegroundColor Yellow
    docker-compose down
    Write-Host "✓ Docker services stopped" -ForegroundColor Green
}

function Setup-Keycloak {
    Write-Host "Setting up Keycloak realm, roles, and test users..." -ForegroundColor Yellow
    Write-Host "Waiting for Keycloak to be ready..." -ForegroundColor Yellow
    poetry run python scripts/setup_keycloak.py
    Write-Host "✓ Keycloak setup complete" -ForegroundColor Green
    Write-Host ""
    Write-Host "Test users created:" -ForegroundColor Cyan
    Write-Host "  engineer / Engineer123! (Process_Engineer)"
    Write-Host "  manager / Manager123! (Plant_Manager)"
    Write-Host "  qa / QALead123! (QA_Lead)"
    Write-Host "  analyst / Analyst123! (Citizen_Data_Scientist)"
    Write-Host "  admin / Admin123! (Admin)"
    Write-Host ""
    Write-Host "Keycloak Admin Console: http://localhost:8080" -ForegroundColor Cyan
    Write-Host "Admin credentials: admin / admin123"
}

function Setup-InfluxDB {
    Write-Host "Setting up InfluxDB buckets and retention policies..." -ForegroundColor Yellow
    poetry run python scripts/setup_influxdb.py
    Write-Host "✓ InfluxDB setup complete" -ForegroundColor Green
}

function Generate-MockData {
    Write-Host "Generating mock manufacturing data..." -ForegroundColor Yellow
    python scripts/generate_mock_data.py --days 30
    Write-Host "✓ Mock data generated in data/mock/" -ForegroundColor Green
}

function Run-Tests {
    Write-Host "Running test suite..." -ForegroundColor Yellow
    poetry run pytest -v --cov=src --cov-report=term-missing --cov-report=html
}

function Run-Lint {
    Write-Host "Running linting checks..." -ForegroundColor Yellow
    poetry run flake8 src tests
    poetry run mypy src
}

function Run-Format {
    Write-Host "Formatting code..." -ForegroundColor Yellow
    poetry run black src tests
    poetry run isort src tests
    Write-Host "✓ Code formatted" -ForegroundColor Green
}

function Clean-Artifacts {
    Write-Host "Cleaning build artifacts and cache..." -ForegroundColor Yellow
    Get-ChildItem -Path . -Include __pycache__,*.egg-info,.pytest_cache,.mypy_cache -Recurse -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path build,dist,htmlcov,.coverage -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "✓ Cleaned" -ForegroundColor Green
}

function Start-API {
    Write-Host "Starting API server..." -ForegroundColor Yellow
    Write-Host "API will be available at: http://localhost:8000" -ForegroundColor Cyan
    Write-Host "API docs: http://localhost:8000/docs" -ForegroundColor Cyan
    Write-Host ""
    poetry run uvicorn src.main:app --reload --port 8000
}

# Execute command
switch ($Command.ToLower()) {
    "help" { Show-Help }
    "install" { Install-Dependencies }
    "docker-up" { Start-Docker }
    "docker-down" { Stop-Docker }
    "setup-keycloak" { Setup-Keycloak }
    "setup-influxdb" { Setup-InfluxDB }
    "mock-data" { Generate-MockData }
    "test" { Run-Tests }
    "lint" { Run-Lint }
    "format" { Run-Format }
    "clean" { Clean-Artifacts }
    "run" { Start-API }
    default {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Write-Host ""
        Show-Help
    }
}
