#!/bin/bash
# Development environment setup script

set -e

echo "Setting up Causal AI Manufacturing Platform development environment..."

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "Poetry not found. Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
fi

# Install dependencies
echo "Installing Python dependencies..."
poetry install

# Copy environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
fi

# Start Docker services
echo "Starting Docker services..."
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 10

# Check service health
echo "Checking service health..."
docker-compose ps

echo ""
echo "Development environment setup complete!"
echo ""
echo "To activate the virtual environment, run:"
echo "  poetry shell"
echo ""
echo "To run the application, use:"
echo "  poetry run uvicorn src.main:app --reload"
echo ""
echo "To run tests, use:"
echo "  poetry run pytest"
