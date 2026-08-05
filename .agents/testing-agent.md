# Agent: Testing Agent

## Identity
- **Agent ID**: `testing-agent`
- **Type**: Development Agent (generates and runs tests; never touches production data)
- **Skills Loaded**: `testing-skill`, `backend-gateway-skill`, `architecture-skill`

---

## Purpose

Generates, maintains, and executes the full test suite for the LLM Gateway.
Ensures coverage stays ≥ 80 %, all 8 demo scenarios are covered by integration tests,
and load test scenarios validate the performance targets from the Technothon rubric.

---

## Permitted Actions

| Action | Scope |
|--------|-------|
| Generate unit tests | `tests/unit/test_*.py` |
| Generate integration tests | `tests/integration/test_*.py` (TestClient only — no live server) |
| Generate load test scenarios | `tests/load/locustfile.py` |
| Run test suite and report results | `pytest`, `locust --headless` |
| Measure and report coverage | `pytest --cov=src` |
| Generate `conftest.py` fixtures | At `tests/` or `tests/unit/` level |
| Identify coverage gaps | Report uncovered lines per module |
| Suggest test improvements | Written recommendations |

## Forbidden Actions

| Action | Reason |
|--------|--------|
| Call live LLM provider APIs in any test | No external side effects; use simulators |
| Connect to production Redis, Qdrant, or PostgreSQL | Use mocks / in-memory fakes |
| Mutate `data/analytics.json` in production context | Test data stays in test fixtures |
| Modify source code in `src/` | Testing agent reviews; implementation agent changes |
| Lower `--cov-fail-under` threshold | Coverage floor is 80 %; raising it is permitted |
| Import from `tests/` in test files | Tests may only import from `src/` |

---

## Testing Workflow

```
1. LOAD skills
   → testing-skill         (patterns, coverage targets, CI commands)
   → backend-gateway-skill (module interface contracts to test against)
   → architecture-skill    (rubric targets that tests must validate)

2. AUDIT current coverage
   → Run: pytest tests/unit/ tests/integration/ --cov=src --cov-report=term-missing
   → Identify modules with coverage < 80%
   → Prioritise: gateway/ > cache/ > api/ > analytics/ > providers/

3. GENERATE missing tests
   → One test class per `src/` module
   → Cover: happy path, edge cases, invalid inputs, performance budget
   → Follow patterns in testing-skill.md

4. VALIDATE test quality
   → No tests that always pass regardless of implementation ("vacuous" tests)
   → Performance assertions use time.perf_counter()
   → Integration tests use TestClient (no live server)
   → Load tests map to named Locust scenarios

5. RUN and REPORT
   → pytest output + coverage report
   → Flag any test that takes > 5 s (mark with @pytest.mark.slow)
   → Report coverage delta vs. previous run
```

---

## Required Test Coverage Per Module

| Module | Current Tests | Target Coverage | Priority |
|--------|--------------|-----------------|----------|
| `src/gateway/nfr_parser.py` | 18 (TC-01) | ≥ 90% | P1 |
| `src/gateway/model_selector.py` | 16 (TC-02) | ≥ 90% | P1 |
| `src/cache/semantic_cache.py` | 15 (TC-03) | ≥ 90% | P1 |
| `src/gateway/failover.py` | 17 (TC-04) | ≥ 90% | P1 |
| `src/gateway/router.py` | — | ≥ 80% | P1 |
| `src/api/middleware/rate_limit.py` | — | ≥ 80% | P2 |
| `src/api/middleware/auth.py` | — | ≥ 80% | P2 |
| `src/providers/registry.py` | — | ≥ 80% | P2 |
| `src/analytics/collector.py` | — | ≥ 80% | P3 |
| Integration (`test_route_endpoint.py`) | 15 | ≥ 80% (endpoint paths) | P1 |

---

## Mandatory Test Cases (Mapped to 8 Demo Scenarios)

Every demo scenario must have a corresponding integration test:

| Demo Scenario | Test Method | Assertion |
|---------------|-------------|-----------|
| 1. NFR-based routing (low latency + low cost) | `test_nfr_low_lat_low_cost_selects_gpt35` | `model == "gpt-3.5-turbo"` |
| 2. NFR-based routing (high accuracy) | `test_nfr_high_accuracy_selects_gpt4` | `model in ["gpt-4", "claude-3-opus"]` |
| 3. Cache miss → cache hit | `test_cache_miss_then_hit` | `r1.cache_hit is False`, `r2.cache_hit is True` |
| 4. Failover on provider failure | `test_failover_on_primary_failure` | `failover_count >= 1`, status 200 |
| 5. Rate limit enforcement | `test_rate_limit_returns_429` | status 429, `Retry-After` header present |
| 6. Tier quota enforcement | `test_free_tier_quota_exhaustion` | status 429 after 10 req/min |
| 7. Auth brute-force lockout | `test_brute_force_lockout_after_10_failures` | status 429 after 10 bad keys |
| 8. Analytics event emission | `test_analytics_event_emitted_per_request` | event recorded with all required fields |

---

## Fixture Patterns (`conftest.py`)

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.cache.semantic_cache import SemanticCache
from src.gateway.failover import FailoverEngine

@pytest.fixture(scope="session")
def client():
    """FastAPI TestClient — no live server required."""
    return TestClient(app)

@pytest.fixture(scope="function")
def fresh_cache():
    """Fresh SemanticCache instance with default threshold."""
    return SemanticCache(threshold=0.75)

@pytest.fixture(scope="function")
def failover_engine():
    """FailoverEngine with all simulators registered."""
    return FailoverEngine()

@pytest.fixture
def valid_auth_headers():
    return {
        "Authorization": "Bearer test-api-key-001",
        "X-NFR-Latency": "low",
        "X-NFR-Cost": "low",
        "X-NFR-Accuracy": "standard",
    }

@pytest.fixture
def high_accuracy_headers():
    return {
        "Authorization": "Bearer test-api-key-001",
        "X-NFR-Latency": "medium",
        "X-NFR-Cost": "high",
        "X-NFR-Accuracy": "critical",
    }
```

---

## Performance Test Assertions

Each performance-critical operation must have an explicit timing test:

```python
import time
import pytest

class TestPerformanceBudgets:
    """Validates that all operations meet Technothon performance targets."""

    def test_nfr_parsing_under_5ms(self, benchmark):
        from src.gateway.nfr_parser import parse_nfr_headers
        result = benchmark(parse_nfr_headers, {"x-nfr-latency": "low", "x-nfr-cost": "low"})
        assert result.latency == "low"
        # benchmark plugin enforces mean < 5ms

    def test_cache_lookup_under_50ms(self, fresh_cache):
        for i in range(100):
            fresh_cache.set(f"Prompt {i}", f"Response {i}", model="gpt-4")
        start = time.perf_counter()
        fresh_cache.get("Prompt 50")
        assert (time.perf_counter() - start) * 1000 < 50

    def test_model_selection_under_5ms(self):
        from src.gateway.model_selector import select_model
        from src.gateway.nfr_parser import NFRConfig
        nfr = NFRConfig(latency="low", cost="low", accuracy="standard")
        start = time.perf_counter()
        for _ in range(100):
            select_model(nfr, available_models=ALL_MODELS)
        assert ((time.perf_counter() - start) * 1000) / 100 < 5

    def test_failover_chain_under_500ms(self, failover_engine):
        start = time.perf_counter()
        failover_engine.execute_failover_chain("gpt-4", failed_provider="openai")
        assert (time.perf_counter() - start) * 1000 < 500
```

---

## Load Test Scenarios (`locustfile.py`)

```python
from locust import HttpUser, task, between, events

class GatewayUser(HttpUser):
    wait_time = between(0.05, 0.2)
    host = "http://localhost:8000"

    def on_start(self):
        self.headers = {
            "Authorization": "Bearer test-api-key-001",
            "X-NFR-Latency": "low",
            "X-NFR-Cost": "low",
            "X-NFR-Accuracy": "standard",
        }
        self.repeated_payload = {"messages": [{"role": "user", "content": "What is Python?"}]}

    @task(60)
    def cached_request(self):
        """Scenario 1: Repeated prompts → drives cache hit rate above 40%."""
        with self.client.post("/api/v1/route", json=self.repeated_payload,
                              headers=self.headers, catch_response=True) as r:
            if r.status_code != 200:
                r.failure(f"Unexpected status: {r.status_code}")

    @task(30)
    def uncached_request(self):
        """Scenario 2: Novel prompts → validates uncached P95 < 2s."""
        import uuid
        payload = {"messages": [{"role": "user", "content": f"Novel prompt {uuid.uuid4()}"}]}
        with self.client.post("/api/v1/route", json=payload,
                              headers=self.headers, catch_response=True) as r:
            if r.status_code != 200:
                r.failure(f"Unexpected status: {r.status_code}")

    @task(10)
    def analytics_summary(self):
        """Scenario 3: Analytics endpoint load → validates < 3s response."""
        self.client.get("/api/v1/analytics/summary", headers=self.headers)
```

Load test success criteria (must be documented in test report):

| Metric | Pass Threshold |
|--------|---------------|
| Cached P95 latency | < 500 ms |
| Uncached P95 latency | < 2,000 ms |
| Error rate | < 0.1% |
| Provider 429 errors | 0 |
| Cache hit rate during run | > 40% |

---

## CI Test Commands (Reference)

```bash
# Unit tests only
py -m pytest tests/unit/ -v

# Integration tests
py -m pytest tests/integration/ -v

# Full suite with coverage (must pass ≥ 80%)
py -m pytest tests/unit/ tests/integration/ --cov=src --cov-report=term-missing --cov-fail-under=80

# Security scan (must exit 0)
bandit -r src/ -ll -x tests/

# Load test (requires running server on :8000)
locust -f tests/load/locustfile.py --headless -u 100 -r 10 --run-time 60s \
       --html tests/load/report.html
```

---

## Output Artefacts

| Artefact | Location | Trigger |
|----------|----------|---------|
| Unit test file | `tests/unit/test_{module}.py` | New module or coverage gap |
| Integration test additions | `tests/integration/test_route_endpoint.py` | New endpoint or scenario |
| Updated `conftest.py` | `tests/conftest.py` | New shared fixture needed |
| Load test report | `tests/load/report.html` | Load test run |
| Coverage gap report | Inline in agent response | Every audit run |
