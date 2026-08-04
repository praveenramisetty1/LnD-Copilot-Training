# src/gateway/failover.py
"""
Multi-level failover engine with per-provider circuit breakers.
State is persisted to data/provider_health.json — no Redis required.
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.providers.base import BaseProvider, ProviderResponse
from src.providers.registry import get_failover_chain

# ── Config ────────────────────────────────────────────────────────────────────
HEALTH_FILE       = os.getenv("PROVIDER_HEALTH_FILE", "data/provider_health.json")
FAILURE_THRESHOLD = int(os.getenv("CB_FAILURE_THRESHOLD", "5"))
RECOVERY_TIMEOUT  = int(os.getenv("CB_RECOVERY_TIMEOUT_SECONDS", "60"))
PROBE_COUNT       = int(os.getenv("CB_PROBE_COUNT", "3"))

# ── Circuit Breaker ───────────────────────────────────────────────────────────

class CircuitBreaker:
    """
    States:
      CLOSED    → normal operation
      OPEN      → provider bypassed until recovery timeout expires
      HALF_OPEN → sending probe requests to test recovery
    """

    def __init__(self, provider: str):
        self.provider       = provider
        self._state         = "CLOSED"
        self._failure_count = 0
        self._last_failure  = 0.0
        self._probe_count   = 0

    # ── public API ───────────────────────────────────────────────────────────

    @property
    def state(self) -> str:
        return self._state

    def is_available(self) -> bool:
        if self._state == "CLOSED":
            return True
        if self._state == "OPEN":
            if time.time() - self._last_failure >= RECOVERY_TIMEOUT:
                self._transition("HALF_OPEN")
                return True
            return False
        # HALF_OPEN: allow up to PROBE_COUNT requests
        return self._probe_count < PROBE_COUNT

    def record_success(self) -> None:
        if self._state == "HALF_OPEN":
            self._probe_count += 1
            if self._probe_count >= PROBE_COUNT:
                self._transition("CLOSED")
                self._failure_count = 0
        elif self._state == "CLOSED":
            self._failure_count = max(0, self._failure_count - 1)

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure = time.time()
        if self._failure_count >= FAILURE_THRESHOLD:
            self._transition("OPEN")

    def force_open(self) -> None:
        """Force circuit open — useful for demo/testing."""
        self._transition("OPEN")
        self._last_failure = time.time()

    def force_close(self) -> None:
        """Reset circuit breaker to healthy state."""
        self._transition("CLOSED")
        self._failure_count = 0

    def to_dict(self) -> dict:
        return {
            "provider":       self.provider,
            "state":          self._state,
            "failure_count":  self._failure_count,
            "last_failure":   self._last_failure,
            "probe_count":    self._probe_count,
        }

    def from_dict(self, data: dict) -> None:
        self._state         = data.get("state", "CLOSED")
        self._failure_count = data.get("failure_count", 0)
        self._last_failure  = data.get("last_failure", 0.0)
        self._probe_count   = data.get("probe_count", 0)

    # ── private ──────────────────────────────────────────────────────────────

    def _transition(self, new_state: str) -> None:
        self._state       = new_state
        self._probe_count = 0


# ── Failover Manager ─────────────────────────────────────────────────────────

class FailoverManager:
    """
    Wraps all circuit breakers and executes multi-level failover.
    Persists CB state to a local JSON file after every state change.
    """

    def __init__(self, providers: Dict[str, BaseProvider]):
        self.providers = providers
        self.breakers: Dict[str, CircuitBreaker] = {
            name: CircuitBreaker(name) for name in providers
        }
        self._load_state()

    # ── main entry point ─────────────────────────────────────────────────────

    def execute_with_failover(
        self,
        primary_model:    str,
        messages:         List[dict],
    ) -> Tuple[ProviderResponse, int]:
        """
        Attempt the primary model first, then walk the failover chain.
        Returns (ProviderResponse, failover_count).
        """
        chain         = get_failover_chain(primary_model)
        failover_count = 0
        last_error    = "All providers unavailable"

        for step in chain:
            model    = step["model"]
            provider = step["provider"]

            cb = self.breakers.get(provider)
            if cb and not cb.is_available():
                last_error = f"{provider} circuit OPEN — skipping"
                continue

            prov_instance = self.providers.get(provider)
            if prov_instance is None:
                continue

            response = prov_instance.complete(messages, model)

            if response.success:
                if cb:
                    cb.record_success()
                self._save_state()
                return response, failover_count
            else:
                if cb:
                    cb.record_failure()
                self._save_state()
                last_error = response.error or "Unknown error"
                if failover_count == 0:
                    # Only increment after first failure (first attempt is not a failover)
                    pass
                failover_count += 1

        # All options exhausted
        return ProviderResponse(
            model=primary_model, provider="none", content="",
            prompt_tokens=0, completion_tokens=0,
            latency_ms=0, cost=0.0, success=False,
            error=f"All failover levels exhausted. Last error: {last_error}",
        ), failover_count

    # ── circuit breaker control ───────────────────────────────────────────────

    def get_available_providers(self) -> List[str]:
        return [name for name, cb in self.breakers.items() if cb.is_available()]

    def get_health_status(self) -> Dict[str, dict]:
        return {name: cb.to_dict() for name, cb in self.breakers.items()}

    def force_open(self, provider: str) -> bool:
        if provider in self.breakers:
            self.breakers[provider].force_open()
            self._save_state()
            return True
        return False

    def force_close(self, provider: str) -> bool:
        if provider in self.breakers:
            self.breakers[provider].force_close()
            self._save_state()
            return True
        return False

    # ── persistence ──────────────────────────────────────────────────────────

    def _save_state(self) -> None:
        Path(HEALTH_FILE).parent.mkdir(parents=True, exist_ok=True)
        state = {name: cb.to_dict() for name, cb in self.breakers.items()}
        with open(HEALTH_FILE, "w") as f:
            json.dump(state, f, indent=2)

    def _load_state(self) -> None:
        if not Path(HEALTH_FILE).exists():
            return
        try:
            with open(HEALTH_FILE) as f:
                state = json.load(f)
            for name, data in state.items():
                if name in self.breakers:
                    self.breakers[name].from_dict(data)
        except (json.JSONDecodeError, KeyError):
            pass  # Start fresh if file is corrupt
