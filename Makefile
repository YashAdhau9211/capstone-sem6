.PHONY: help install dev-setup test lint format clean docker-up docker-down

help:
	@echo "Causal AI Manufacturing Platform - Development Commands"
	@echo ""
	@echo "Available commands:"
	@echo "  make install      - Install dependencies using Poetry"
	@echo "  make dev-setup    - Set up development environment"
	@echo "  make test         - Run test suite with coverage"
	@echo "  make lint         - Run linting checks"
	@echo "  make format       - Format code with black and isort"
	@echo "  make docker-up    - Start Docker services"
	@echo "  make docker-down  - Stop Docker services"
	@echo "  make clean        - Clean build artifacts and cache"

install:
	poetry install

dev-setup:
	bash scripts/setup_dev.sh

test:
	poetry run pytest -v --cov=src --cov-report=term-missing --cov-report=html

lint:
	bash scripts/lint.sh

format:
	bash scripts/format.sh

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build dist htmlcov .coverage
