#!/bin/bash
# Run linting and formatting checks

set -e

echo "Running code formatting checks..."

echo "1. Black (code formatter)..."
poetry run black --check src/ tests/ config/

echo "2. isort (import sorter)..."
poetry run isort --check-only src/ tests/ config/

echo "3. flake8 (linter)..."
poetry run flake8 src/ tests/ config/

echo "4. mypy (type checker)..."
poetry run mypy src/ config/

echo ""
echo "All linting checks passed!"
