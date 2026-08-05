# Skill: Testing

## Identity
- **Skill ID**: `testing-skill`
- **Domain**: pytest / Locust — Unit, Integration, Load Testing
- **Used By**: Testing Agent, Implementation Agent

---

## Purpose

Provides complete knowledge of the LLM Gateway test strategy, test structure,
coverage targets, and test generation patterns so agents can write correct,
high-value tests aligned with Technothon evaluation rubrics.

---

## Test Coverage Targets

| Target | Minimum | Outstanding |
|--------|---------|-------------|
| Overall coverage | > 80% | > 90% |
| Unit tests | > 80% per module | > 90% |
| Integration tests | All 8 core scenarios covered | All edge cases covered |
| Load tests | 3 Locust scenarios defined | Throughput > 10,000 RPS validated |

---

## Test Directory Structure

```
tests/
├── unit/
│   ├── test_nfr_parser.py          ← 18 tests  (TC-01)
│   ├── test_model_selector.py      ← 16 tests  (TC-02)
│   ├── test_semantic_cache.py      ← 15 tests  (TC-03)
│   ├── test_failover.py            ← 17 tests  (TC-04)
│   ├── test_rate_limiter.py        ← target: 12+ tests
│   ├── test_auth_middleware.py     ← target: 10+ tests
│   ├── test_analytics_collector.py ← target: 8+ tests
│   └── test_provider_registry.py   ← target: 10+ tests
├── integration/
│   └── test_route_endpoint.py      ← 15 tests (TestClient, no live server)
└── load/
    └── locustfile.py               ← 3 Locust scenarios
```

---

## Unit Test Patterns

### NFR Parser (`test_nfr_parser.py`) — TC-01
```python
import pytest
from src.gateway.nfr_parser import parse_nfr_headers, NFRConfig

class TestNFRParser:
    def test_valid_low_latency_low_cost(self):
        config = parse_nfr_headers({
            "x-nfr-latency": "low",
            "x-nfr-cost": "low",
            "x-nfr-accuracy": "standard"
        })
        assert config.latency == "low"
        assert config.cost == "low"
        assert config.accuracy == "standard"

    def test_invalid_latency_raises_400(self):
        with pytest.raises(ValueError):
            parse_nfr_headers({"x-nfr-latency": "ultrafast"})

    def test_missing_headers_use_defaults(self):
        config = parse_nfr_headers({})
        assert config.latency == "medium"
        assert config.cost == "medium"
        assert config.accuracy == "standard"

    def test_parsing_completes_under_5ms(self):
        import time
        start = time.perf_counter()
        for _ in range(100):
            parse_nfr_headers({"x-nfr-latency": "low", "x-nfr-cost": "high", "x-nfr-accuracy": "critical"})
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms / 100 < 5  # average < 5 ms per parse
```

### Model Selector (`test_model_selector.py`) — TC-02
```python
from src.gateway.model_selector import select_model
from src.gateway.nfr_parser import NFRConfig

class TestModelSelector:
    def test_low_latency_low_cost_selects_gpt35(self):
        nfr = NFRConfig(latency="low", cost="low", accuracy="standard")
        result = select_model(nfr, available_models=ALL_MODELS)
        assert result.name == "gpt-3.5-turbo"

    def test_high_accuracy_selects_gpt4(self):
        nfr = NFRConfig(latency="medium", cost="high", accuracy="critical")
        result = select_model(nfr, available_models=ALL_MODELS)
        assert result.name in ["gpt-4", "claude-3-opus"]

    def test_cost_weight_dominates_at_40_percent(self):
        # When cost=low, model with lower cost must win even if slightly higher latency
        ...

    def test_selection_with_no_available_models_raises(self):
        with pytest.raises(RuntimeError, match="No available models"):
            select_model(NFRConfig(), available_models=[])
```

### Semantic Cache (`test_semantic_cache.py`) — TC-03
```python
from src.cache.semantic_cache import SemanticCache

class TestSemanticCache:
    def setup_method(self):
        self.cache = SemanticCache(threshold=0.75)

    def test_exact_prompt_returns_cache_hit(self):
        self.cache.set("What is AI?", "AI is...", model="gpt-4")
        result = self.cache.get("What is AI?")
        assert result is not None
        assert result.response == "AI is..."

    def test_semantically_similar_prompt_returns_hit(self):
        self.cache.set("What is artificial intelligence?", "AI is...", model="gpt-4")
        result = self.cache.get("Can you define artificial intelligence?")
        assert result is not None

    def test_unrelated_prompt_returns_miss(self):
        self.cache.set("What is AI?", "AI is...", model="gpt-4")
        result = self.cache.get("What is the capital of France?")
        assert result is None

    def test_threshold_respected(self):
        cache_strict = SemanticCache(threshold=0.99)
        cache_strict.set("What is machine learning?", "ML is...", model="gpt-4")
        result = cache_strict.get("Define machine learning")
        assert result is None  # strict threshold → miss

    def test_cache_lookup_under_50ms(self):
        import time
        for i in range(100):
            self.cache.set(f"Prompt {i}", f"Response {i}", model="gpt-4")
        start = time.perf_counter()
        self.cache.get("Prompt 50")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 50
```

### Failover (`test_failover.py`) — TC-04
```python
from src.gateway.failover import FailoverEngine, CircuitBreaker, CircuitState

class TestCircuitBreaker:
    def test_opens_after_5_failures(self):
        cb = CircuitBreaker(failure_threshold=5)
        for _ in range(5):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_transitions_to_half_open_after_60s(self):
        cb = CircuitBreaker(failure_threshold=5, timeout_seconds=60)
        for _ in range(5):
            cb.record_failure()
        cb._last_failure_time -= 61  # fast-forward time
        assert cb.state == CircuitState.HALF_OPEN

    def test_level1_failover_tries_different_provider(self):
        engine = FailoverEngine()
        result = engine.failover("gpt-4", failed_provider="openai", level=1)
        assert result.provider != "openai"
        assert result.model == "gpt-4"

    def test_full_failover_completes_under_500ms(self):
        import time
        engine = FailoverEngine()
        start = time.perf_counter()
        engine.execute_failover_chain("gpt-4", failed_provider="openai")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 500
```

---

## Integration Test Patterns

### Route Endpoint (`test_route_endpoint.py`)
```python
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)
VALID_KEY = "test-api-key-001"

class TestRouteEndpoint:
    def test_cache_miss_then_hit(self):
        payload = {"messages": [{"role": "user", "content": "What is Python?"}]}
        headers = {"Authorization": f"Bearer {VALID_KEY}",
                   "X-NFR-Latency": "low", "X-NFR-Cost": "low",
                   "X-NFR-Accuracy": "standard"}
        r1 = client.post("/api/v1/route", json=payload, headers=headers)
        assert r1.status_code == 200
        assert r1.json()["metadata"]["cache_hit"] is False

        r2 = client.post("/api/v1/route", json=payload, headers=headers)
        assert r2.status_code == 200
        assert r2.json()["metadata"]["cache_hit"] is True

    def test_invalid_api_key_returns_401(self):
        r = client.post("/api/v1/route", json={"messages": []},
                        headers={"Authorization": "Bearer bad-key"})
        assert r.status_code == 401

    def test_rate_limit_returns_429(self):
        # Exhaust token bucket for Free tier
        ...

    def test_nfr_headers_reflected_in_metadata(self):
        ...

    def test_failover_triggered_on_provider_failure(self):
        # Set FAILURE_RATE=1.0 on primary provider
        ...
```

---

## Load Test Patterns (`locustfile.py`)

```python
from locust import HttpUser, task, between

class GatewayUser(HttpUser):
    wait_time = between(0.1, 0.5)
    host = "http://localhost:8000"

    @task(60)
    def cached_request(self):
        """Scenario 1: Repeated similar prompts — drives cache hit rate"""
        ...

    @task(30)
    def uncached_request(self):
        """Scenario 2: Novel prompts — measures uncached P95 latency"""
        ...

    @task(10)
    def analytics_query(self):
        """Scenario 3: Analytics endpoint load"""
        ...
```

Load test success criteria:
- Cached P95 < 500 ms at 100 concurrent users
- Uncached P95 < 2,000 ms at 100 concurrent users
- 0 provider 429 errors during run
- Error rate < 0.1%

---

## Test Generation Rules (Agents Must Follow)

1. Every public function in `src/` must have at least one unit test
2. Tests must cover: happy path, edge cases, and error/exception paths
3. No real LLM provider API calls in any test — use simulators or mocks
4. No real Redis, Qdrant, or DB connections in unit tests — mock at the client level
5. Performance assertions (timing) must use `time.perf_counter()`, not `time.time()`
6. Integration tests must use `fastapi.testclient.TestClient` — no live server required
7. Test files must not import from `tests/` package — only from `src/`
8. Fixtures must be in `conftest.py` at the appropriate level, not duplicated in test files
9. Each test class maps to one module in `src/`
10. Coverage report generated by `pytest --cov=src --cov-report=term-missing`

---

## CI Test Commands

```bash
# Run all unit tests
py -m pytest tests/unit/ -v

# Run integration tests
py -m pytest tests/integration/ -v

# Run all tests with coverage
py -m pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=80

# Run security scan
bandit -r src/ -ll

# Run load test (requires running server)
locust -f tests/load/locustfile.py --headless -u 100 -r 10 --run-time 60s
```
