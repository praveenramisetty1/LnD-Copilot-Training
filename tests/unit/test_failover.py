# tests/unit/test_failover.py
"""Unit tests for circuit breaker + multi-level failover — TC-04"""

import time
from unittest.mock import MagicMock

from src.gateway.failover import CircuitBreaker, FailoverManager
from src.providers.base import ProviderResponse

# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock_provider(success: bool, provider_name: str = "openai"):
    m = MagicMock()
    m.complete.return_value = ProviderResponse(
        model="gpt-3.5-turbo", provider=provider_name,
        content="Mock response" if success else "",
        prompt_tokens=10, completion_tokens=20,
        latency_ms=500 if success else 0,
        cost=0.001 if success else 0.0,
        success=success,
        error=None if success else "Provider down (mock)",
    )
    m.health_check.return_value = success
    return m


MESSAGES = [{"role": "user", "content": "Hello"}]


# ── Circuit Breaker state machine ─────────────────────────────────────────────

def test_cb_initial_state_is_closed():
    cb = CircuitBreaker("openai")
    assert cb.state == "CLOSED"
    assert cb.is_available() is True


def test_cb_opens_after_failure_threshold():
    cb = CircuitBreaker("openai")
    for _ in range(5):          # CB_FAILURE_THRESHOLD default = 5
        cb.record_failure()
    assert cb.state       == "OPEN"
    assert cb.is_available() is False


def test_cb_does_not_open_below_threshold():
    cb = CircuitBreaker("openai")
    for _ in range(4):
        cb.record_failure()
    assert cb.state == "CLOSED"
    assert cb.is_available() is True


def test_cb_transitions_to_half_open_after_timeout():
    cb = CircuitBreaker("openai")
    for _ in range(5):
        cb.record_failure()
    assert cb.state == "OPEN"
    cb._last_failure = time.time() - 61   # simulate recovery timeout elapsed
    assert cb.is_available() is True
    assert cb.state == "HALF_OPEN"


def test_cb_closes_after_enough_probes():
    cb = CircuitBreaker("openai")
    cb.force_open()
    cb._last_failure = time.time() - 61
    cb.is_available()                     # triggers HALF_OPEN transition
    for _ in range(3):                    # CB_PROBE_COUNT default = 3
        cb.record_success()
    assert cb.state == "CLOSED"
    assert cb._failure_count == 0


def test_cb_stays_open_if_timeout_not_elapsed():
    cb = CircuitBreaker("openai")
    cb.force_open()
    cb._last_failure = time.time()        # just now — timeout not elapsed
    assert cb.is_available() is False
    assert cb.state == "OPEN"


def test_cb_force_open():
    cb = CircuitBreaker("openai")
    cb.force_open()
    assert cb.state == "OPEN"


def test_cb_force_close():
    cb = CircuitBreaker("openai")
    cb.force_open()
    cb.force_close()
    assert cb.state == "CLOSED"
    assert cb._failure_count == 0
    assert cb.is_available() is True


def test_cb_to_dict_has_required_keys():
    cb = CircuitBreaker("openai")
    d = cb.to_dict()
    for key in ("provider", "state", "failure_count", "last_failure", "probe_count"):
        assert key in d


def test_cb_from_dict_restores_state():
    cb = CircuitBreaker("openai")
    cb.from_dict({"state": "OPEN", "failure_count": 5,
                  "last_failure": 0.0, "probe_count": 0})
    assert cb.state == "OPEN"
    assert cb._failure_count == 5


# ── FailoverManager ───────────────────────────────────────────────────────────

def test_failover_succeeds_on_first_attempt(tmp_path, monkeypatch):
    monkeypatch.setenv("PROVIDER_HEALTH_FILE", str(tmp_path / "h.json"))
    providers = {
        "openai":    _mock_provider(True,  "openai"),
        "anthropic": _mock_provider(False, "anthropic"),
        "google":    _mock_provider(False, "google"),
    }
    fm = FailoverManager(providers)
    resp, fc = fm.execute_with_failover("gpt-3.5-turbo", MESSAGES)
    assert resp.success  is True
    assert fc            == 0


def test_failover_triggered_on_primary_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("PROVIDER_HEALTH_FILE", str(tmp_path / "h.json"))
    providers = {
        "openai":    _mock_provider(False, "openai"),
        "anthropic": _mock_provider(True,  "anthropic"),
        "google":    _mock_provider(True,  "google"),
    }
    fm = FailoverManager(providers)
    resp, fc = fm.execute_with_failover("gpt-3.5-turbo", MESSAGES)
    assert resp.success is True
    assert fc           >= 1


def test_failover_all_providers_down_returns_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("PROVIDER_HEALTH_FILE", str(tmp_path / "h.json"))
    providers = {
        "openai":    _mock_provider(False, "openai"),
        "anthropic": _mock_provider(False, "anthropic"),
        "google":    _mock_provider(False, "google"),
    }
    fm = FailoverManager(providers)
    resp, fc = fm.execute_with_failover("gpt-3.5-turbo", MESSAGES)
    assert resp.success is False
    assert resp.error   is not None


def test_open_circuit_excluded_from_routing(tmp_path, monkeypatch):
    monkeypatch.setenv("PROVIDER_HEALTH_FILE", str(tmp_path / "h.json"))
    providers = {
        "openai":    _mock_provider(True, "openai"),
        "anthropic": _mock_provider(True, "anthropic"),
        "google":    _mock_provider(True, "google"),
    }
    fm = FailoverManager(providers)
    fm.force_open("openai")
    available = fm.get_available_providers()
    assert "openai"    not in available
    assert "anthropic" in available
    assert "google"    in available


def test_force_open_and_close_via_manager(tmp_path, monkeypatch):
    monkeypatch.setenv("PROVIDER_HEALTH_FILE", str(tmp_path / "h.json"))
    providers = {"openai": _mock_provider(True, "openai")}
    fm = FailoverManager(providers)
    assert fm.force_open("openai")  is True
    assert fm.force_close("openai") is True
    assert "openai" in fm.get_available_providers()


def test_force_open_unknown_provider_returns_false(tmp_path, monkeypatch):
    monkeypatch.setenv("PROVIDER_HEALTH_FILE", str(tmp_path / "h.json"))
    providers = {"openai": _mock_provider(True, "openai")}
    fm = FailoverManager(providers)
    assert fm.force_open("nonexistent") is False


def test_get_health_status_returns_all_providers(tmp_path, monkeypatch):
    monkeypatch.setenv("PROVIDER_HEALTH_FILE", str(tmp_path / "h.json"))
    providers = {
        "openai":    _mock_provider(True, "openai"),
        "anthropic": _mock_provider(True, "anthropic"),
        "google":    _mock_provider(True, "google"),
    }
    fm = FailoverManager(providers)
    status = fm.get_health_status()
    assert "openai"    in status
    assert "anthropic" in status
    assert "google"    in status
    assert status["openai"]["state"] == "CLOSED"
