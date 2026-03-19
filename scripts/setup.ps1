# PowerShell setup script for Windows users
# Alternative to Makefile commands

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

function Show-Help {
    Write-Host "Causal AI Manufacturing Platform - Development Commands" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Available commands:" -ForegroundColor Yellow
    Write-Host "  .\scripts\setup.ps1 install        - Install dependencies using Poetry"
    Write-Host "  .\scripts\setup.ps1 test           - Run test suite with coverage"
    Write-Host "  .\scripts\setup.ps1 lint           - Run linting checks"
    Write-Host "  .\scripts\setup.ps1 format         - Format code with black and isort"
    Write-Host "  .\scripts\setup.ps1 docker-up      - Start Docker services"
    Write-Host "  .\scripts\setup.ps1 docker-down    - Stop Docker services"
    Write-Host "  .\scripts\setup.ps1 setup-influxdb - Configure InfluxDB buckets and retention policies"
    Write-Host "  .\scripts\setup.ps1 clean          - Clean build artifacts and cache"
    Write-Host ""
}

function Install-Dependencies {
    Write-Host "Installing dependencies..." -ForegroundColor Green
    poetry install
}

function Run-Tests {
    Write-Host "Running tests..." -ForegroundColor Green
    poetry run pytest -v --cov=src --cov-report=term-missing --cov-report=html
}

function Run-Lint {
    Write-Host "Running linting checks..." -ForegroundColor Green
    poetry run flake8 src tests
    poetry run mypy src
}

function Run-Format {
    Write-Host "Formatting code..." -ForegroundColor Green
    poetry run black src tests
    poetry run isort src tests
}

function Start-Docker {
    Write-Host "Starting Docker services..." -ForegroundColor Green
    docker-compose up -d
}

function Stop-Docker {
    Write-Host "Stopping Docker services..." -ForegroundColor Green
    docker-compose down
}

function Setup-InfluxDB {
    Write-Host "Setting up InfluxDB buckets and retention policies..." -ForegroundColor Green
    poetry run python scripts/setup_influxdb.py
    Write-Host "✓ InfluxDB setup complete" -ForegroundColor Green
}

function Clean-Artifacts {
    Write-Host "Cleaning build artifacts and cache..." -ForegroundColor Green
    Get-ChildItem -Path . -Include __pycache__ -Recurse -Force | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue
    Get-ChildItem -Path . -Include *.egg-info -Recurse -Force | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue
    Get-ChildItem -Path . -Include .pytest_cache -Recurse -Force | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue
    Get-ChildItem -Path . -Include .mypy_cache -Recurse -Force | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue
    Remove-Item -Path build, dist, htmlcov, .coverage -Force -Recurse -ErrorAction SilentlyContinue
    Write-Host "✓ Cleanup complete" -ForegroundColor Green
}

# Execute command
switch ($Command.ToLower()) {
    "help" { Show-Help }
    "install" { Install-Dependencies }
    "test" { Run-Tests }
    "lint" { Run-Lint }
    "format" { Run-Format }
    "docker-up" { Start-Docker }
    "docker-down" { Stop-Docker }
    "setup-influxdb" { Setup-InfluxDB }
    "clean" { Clean-Artifacts }
    default {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Write-Host ""
        Show-Help
    }
}
