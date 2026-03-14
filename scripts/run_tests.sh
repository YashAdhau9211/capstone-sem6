#!/bin/bash
# Run test suite with coverage

set -e

echo "Running test suite..."
poetry run pytest -v --cov=src --cov-report=term-missing --cov-report=html

echo ""
echo "Test coverage report generated in htmlcov/index.html"
