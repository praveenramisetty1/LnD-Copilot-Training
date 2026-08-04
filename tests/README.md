# Tests — LLM Gateway POC

## Structure
```
tests/
├── unit/          # Fast, no I/O — pytest
├── integration/   # Requires app running — pytest + httpx
├── e2e/           # Full flow tests
└── load/          # Locust load tests
```

## Run
```bash
# Unit tests only
PYTHONPATH=. pytest tests/unit/ -v

# All tests with coverage
PYTHONPATH=. pytest tests/ --cov=src --cov-report=term-missing

# Load tests (requires server running on port 8000)
locust -f tests/load/locustfile.py --host http://localhost:8000
```

## Demo Keys for Integration Tests
- `free-key-001` / `basic-key-001` / `pro-key-001` / `enterprise-key-001`
