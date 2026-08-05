# tests/integration/test_route_endpoint.py
"""
Integration tests for POST /api/v1/route — TC-08 (E2E happy path).
Uses FastAPI TestClient — no running server needed.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="module", autouse=True)
def _app_lifespan():
    """Start the FastAPI lifespan (initialises GatewayRouter) for all tests."""
    with client:
        yield

FREE_KEY        = "free-key-001"
PRO_KEY         = "pro-key-001"
ENTERPRISE_KEY  = "enterprise-key-001"

BASIC_PAYLOAD = {
    "messages": [{"role": "user", "content": "What is the capital of France?"}],
    "nfr": {"latency": "low", "cost": "low", "accuracy": "standard"},
}


# ── Authentication ────────────────────────────────────────────────────────────

def test_no_auth_returns_401():
    r = client.post("/api/v1/route", json=BASIC_PAYLOAD)
    assert r.status_code == 401


def test_invalid_key_returns_401():
    r = client.post("/api/v1/route", json=BASIC_PAYLOAD,
                    headers={"Authorization": "Bearer invalid-key"})
    assert r.status_code == 401


def test_valid_key_returns_200():
    r = client.post("/api/v1/route", json=BASIC_PAYLOAD,
                    headers={"Authorization": f"Bearer {FREE_KEY}"})
    assert r.status_code == 200


# ── Response structure ────────────────────────────────────────────────────────

def test_response_has_required_fields():
    r = client.post("/api/v1/route", json=BASIC_PAYLOAD,
                    headers={"Authorization": f"Bearer {PRO_KEY}"})
    assert r.status_code == 200
    body = r.json()
    for field in ("id", "model", "provider", "content", "usage", "metadata"):
        assert field in body, f"Missing field: {field}"


def test_metadata_fields_present():
    r = client.post("/api/v1/route", json=BASIC_PAYLOAD,
                    headers={"Authorization": f"Bearer {FREE_KEY}"})
    meta = r.json()["metadata"]
    for key in ("cache_hit", "latency_ms", "cost", "failover_count", "selected_reason"):
        assert key in meta, f"Missing metadata key: {key}"


def test_usage_fields_present():
    r = client.post("/api/v1/route", json=BASIC_PAYLOAD,
                    headers={"Authorization": f"Bearer {FREE_KEY}"})
    usage = r.json()["usage"]
    assert "prompt_tokens"     in usage
    assert "completion_tokens" in usage
    assert "total_tokens"      in usage


# ── NFR routing ───────────────────────────────────────────────────────────────

def test_low_cost_nfr_selects_cheap_model():
    payload = {
        "messages": [{"role": "user", "content": "Hello"}],
        "nfr": {"latency": "medium", "cost": "low", "accuracy": "standard"},
    }
    r = client.post("/api/v1/route", json=payload,
                    headers={"Authorization": f"Bearer {ENTERPRISE_KEY}"})
    assert r.status_code == 200
    body = r.json()
    # Cheapest models are gemini-flash or claude-3-haiku
    assert body["model"] in ["gemini-flash", "claude-3-haiku", "gpt-3.5-turbo"]


def test_nfr_via_headers():
    r = client.post(
        "/api/v1/route",
        json={"messages": [{"role": "user", "content": "Hello"}]},
        headers={
            "Authorization":  f"Bearer {FREE_KEY}",
            "X-NFR-Latency":  "low",
            "X-NFR-Cost":     "low",
            "X-NFR-Accuracy": "standard",
        },
    )
    assert r.status_code == 200


def test_invalid_nfr_value_returns_400():
    payload = {
        "messages": [{"role": "user", "content": "Hello"}],
        "nfr": {"latency": "ultra_fast", "cost": "low", "accuracy": "standard"},
    }
    r = client.post("/api/v1/route", json=payload,
                    headers={"Authorization": f"Bearer {FREE_KEY}"})
    assert r.status_code in (400, 422)


# ── Semantic cache ────────────────────────────────────────────────────────────

def test_second_identical_request_is_cache_hit():
    payload = {
        "messages": [{"role": "user", "content": "What is 2 + 2?"}],
        "nfr": {"latency": "low", "cost": "low", "accuracy": "standard"},
    }
    headers = {"Authorization": f"Bearer {FREE_KEY}"}
    # First call — must be a miss
    r1 = client.post("/api/v1/route", json=payload, headers=headers)
    assert r1.status_code == 200
    # Second call — same prompt should be a hit
    r2 = client.post("/api/v1/route", json=payload, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["metadata"]["cache_hit"] is True


# ── Health endpoint ───────────────────────────────────────────────────────────

def test_health_endpoint_no_auth_required():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_health_returns_provider_states():
    r = client.get("/health")
    body = r.json()
    assert "providers" in body
    providers = body["providers"]
    for name in ("openai", "anthropic", "google"):
        assert name in providers
        assert providers[name]["state"] == "CLOSED"


# ── Analytics endpoints ───────────────────────────────────────────────────────

def test_analytics_summary_accessible():
    r = client.get("/api/v1/analytics/summary",
                   headers={"Authorization": f"Bearer {FREE_KEY}"})
    assert r.status_code == 200
    body = r.json()
    assert "total_requests" in body
    assert "cache_hit_rate" in body


def test_circuit_breaker_open_triggers_failover():
    headers = {"Authorization": f"Bearer {ENTERPRISE_KEY}"}
    # Force openai down
    client.post("/api/v1/providers/openai/circuit/open", headers=headers)
    # Route a request — should still succeed via failover
    r = client.post("/api/v1/route", json=BASIC_PAYLOAD, headers=headers)
    assert r.status_code == 200
    assert r.json()["provider"] != "openai"
    # Restore openai
    client.post("/api/v1/providers/openai/circuit/close", headers=headers)
