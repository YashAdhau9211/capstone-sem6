#!/bin/bash
# Format code using black and isort

set -e

echo "Formatting code..."

echo "1. Running black..."
poetry run black src/ tests/ config/

echo "2. Running isort..."
poetry run isort src/ tests/ config/

echo ""
echo "Code formatting complete!"
