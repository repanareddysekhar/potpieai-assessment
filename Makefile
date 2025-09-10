# Code Review Agent - Test Makefile
# Provides convenient commands for running different types of tests

.PHONY: help test test-unit test-integration test-e2e test-performance test-smoke test-fast test-all test-cache test-api test-github coverage lint clean install-dev

# Default target
help:
	@echo "🧪 Code Review Agent Test Commands"
	@echo "=================================="
	@echo ""
	@echo "Test Commands:"
	@echo "  make test-unit         - Run unit tests (fast, isolated)"
	@echo "  make test-integration  - Run integration tests"
	@echo "  make test-e2e          - Run end-to-end tests"
	@echo "  make test-performance  - Run performance tests"
	@echo "  make test-smoke        - Run smoke tests"
	@echo "  make test-fast         - Run fast tests only"
	@echo "  make test-all          - Run all tests with coverage"
	@echo ""
	@echo "Specific Test Categories:"
	@echo "  make test-cache        - Run cache-related tests"
	@echo "  make test-api          - Run API endpoint tests"
	@echo "  make test-github       - Run GitHub service tests"
	@echo ""
	@echo "Quality Commands:"
	@echo "  make coverage          - Generate coverage report"
	@echo "  make lint              - Run code linting"
	@echo "  make clean             - Clean test artifacts"
	@echo ""
	@echo "Setup Commands:"
	@echo "  make install-dev       - Install development dependencies"
	@echo ""

# Test commands using the test runner
test-unit:
	@python run_tests.py unit

test-integration:
	@python run_tests.py integration

test-e2e:
	@python run_tests.py e2e

test-performance:
	@python run_tests.py performance

test-smoke:
	@python run_tests.py smoke

test-fast:
	@python run_tests.py fast

test-all:
	@python run_tests.py all

test-cache:
	@python run_tests.py cache

test-api:
	@python run_tests.py api

test-github:
	@python run_tests.py github

coverage:
	@python run_tests.py coverage

lint:
	@python run_tests.py lint

# Alternative test commands using pytest directly
test:
	@echo "🧪 Running default test suite (unit + integration)"
	@./venv/bin/python -m pytest tests/unit/ tests/integration/ -v --tb=short

test-verbose:
	@echo "🧪 Running tests with verbose output"
	@./venv/bin/python -m pytest tests/ -v --tb=long --durations=10

test-parallel:
	@echo "🧪 Running tests in parallel (requires pytest-xdist)"
	@./venv/bin/python -m pytest tests/unit/ -n auto --tb=short

test-watch:
	@echo "🧪 Running tests in watch mode (requires pytest-watch)"
	@./venv/bin/python -m ptw tests/ app/

# Quality and maintenance commands
test-security:
	@echo "🔒 Running security tests (requires bandit)"
	@./venv/bin/python -m bandit -r app/ -f json -o security-report.json || true
	@./venv/bin/python -m bandit -r app/

format:
	@echo "🎨 Formatting code with black"
	@./venv/bin/python -m black app/ tests/ --line-length 88

format-check:
	@echo "🎨 Checking code formatting"
	@./venv/bin/python -m black app/ tests/ --check --line-length 88

type-check:
	@echo "🔍 Running type checking with mypy"
	@./venv/bin/python -m mypy app/ --ignore-missing-imports

# Docker test commands
test-docker:
	@echo "🐳 Running tests in Docker"
	@docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit

test-docker-clean:
	@echo "🐳 Cleaning Docker test environment"
	@docker-compose -f docker-compose.test.yml down -v --remove-orphans

# Benchmark and profiling
benchmark:
	@echo "📊 Running performance benchmarks"
	@./venv/bin/python -m pytest tests/performance/ --benchmark-only --benchmark-sort=mean

profile:
	@echo "📈 Running tests with profiling"
	@./venv/bin/python -m pytest tests/unit/ --profile --profile-svg

# Clean up commands
clean:
	@echo "🧹 Cleaning test artifacts"
	@rm -rf .pytest_cache/
	@rm -rf htmlcov/
	@rm -rf .coverage
	@rm -rf coverage.xml
	@rm -rf security-report.json
	@rm -rf prof/
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true

clean-all: clean
	@echo "🧹 Deep cleaning all artifacts"
	@rm -rf .mypy_cache/
	@rm -rf .tox/
	@rm -rf build/
	@rm -rf dist/
	@rm -rf *.egg-info/

# Development setup
install-dev:
	@echo "📦 Installing development dependencies"
	@./venv/bin/pip install -e .
	@./venv/bin/pip install pytest pytest-cov pytest-mock pytest-asyncio
	@./venv/bin/pip install black flake8 mypy bandit
	@./venv/bin/pip install pytest-xdist pytest-watch pytest-benchmark
	@./venv/bin/pip install psutil  # For performance tests

# CI/CD commands
ci-test:
	@echo "🤖 Running CI test suite"
	@./venv/bin/python -m pytest tests/ --tb=short --cov=app --cov-report=xml --cov-fail-under=80

ci-quality:
	@echo "🤖 Running CI quality checks"
	@make lint
	@make format-check
	@make type-check

# Database and Redis commands for testing
test-setup:
	@echo "🔧 Setting up test environment"
	@docker-compose up redis -d
	@sleep 2  # Wait for Redis to start

test-teardown:
	@echo "🔧 Tearing down test environment"
	@docker-compose down

# Test with real Redis
test-redis:
	@echo "🔴 Running tests with real Redis"
	@make test-setup
	@./venv/bin/python -m pytest tests/ -m "redis" -v
	@make test-teardown

# Generate test reports
test-report:
	@echo "📋 Generating comprehensive test report"
	@./venv/bin/python -m pytest tests/ --html=test-report.html --self-contained-html --cov=app --cov-report=html

# Test specific files or patterns
test-file:
	@echo "🎯 Running tests for specific file: $(FILE)"
	@./venv/bin/python -m pytest $(FILE) -v

test-pattern:
	@echo "🎯 Running tests matching pattern: $(PATTERN)"
	@./venv/bin/python -m pytest tests/ -k "$(PATTERN)" -v

# Debug commands
test-debug:
	@echo "🐛 Running tests in debug mode"
	@./venv/bin/python -m pytest tests/ -v --tb=long --capture=no --log-cli-level=DEBUG

test-pdb:
	@echo "🐛 Running tests with PDB on failure"
	@./venv/bin/python -m pytest tests/ --pdb --pdbcls=IPython.terminal.debugger:Pdb
