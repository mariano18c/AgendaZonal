.PHONY: test test-unit test-integration test-security test-cov test-95 test-full

# Run all tests
test:
	python -m pytest tests/ -v --tb=short

# Run only unit tests
test-unit:
	python -m pytest tests/unit/ -v --tb=short -m unit

# Run only integration tests
test-integration:
	python -m pytest tests/integration/ -v --tb=short -m integration

# Run only security tests
test-security:
	python -m pytest tests/security/ -v --tb=short -m security

# Run with coverage report
test-cov:
	python -m pytest tests/ -v --tb=short --cov=app --cov-report=html --cov-report=term-missing

# Run with 90% coverage threshold
test-90:
	python -m pytest tests/ -v --tb=short --cov=app --cov-report=term-missing --cov-report=html --cov-fail-under=90

# Run all with coverage and parallel
test-full:
	python -m pytest tests/ -v --tb=short --cov=app --cov-report=html --cov-report=term-missing --cov-fail-under=90

# Initialize database
init-db:
	python init_db.py

# Run the server
run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run the server in debug mode
run-debug:
	uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level debug --reload
