# src/simulator/provider_simulator.py
"""
Provider failure simulator — used for demo and integration tests.
Allows scripted failure/recovery scenarios without touching real providers.
"""

from typing import Dict

from src.gateway.failover import FailoverManager
from src.providers.registry import build_providers


class ProviderSimulator:
    """
    Controls provider failure scenarios for demo and testing.
    Works by toggling circuit breakers on the FailoverManager.
    """

    def __init__(self, failover_manager: FailoverManager):
        self.fm = failover_manager

    # ── Scenario helpers ──────────────────────────────────────────────────────

    def simulate_outage(self, provider: str) -> str:
        """Force a provider into OPEN (down) state."""
        success = self.fm.force_open(provider)
        return f"✅ {provider} is now DOWN (circuit OPEN)" if success \
               else f"❌ Provider '{provider}' not found"

    def restore_provider(self, provider: str) -> str:
        """Restore a provider to CLOSED (healthy) state."""
        success = self.fm.force_close(provider)
        return f"✅ {provider} is now UP (circuit CLOSED)" if success \
               else f"❌ Provider '{provider}' not found"

    def status(self) -> Dict[str, dict]:
        """Return current circuit breaker state for all providers."""
        return self.fm.get_health_status()

    def available_providers(self):
        return self.fm.get_available_providers()

    # ── Pre-built demo scenarios ──────────────────────────────────────────────

    def scenario_openai_down(self):
        """Demo scenario: OpenAI goes down → expect Anthropic/Google failover."""
        print("🔴  Scenario: OpenAI outage")
        print(self.simulate_outage("openai"))
        print("    → Next request should failover to Anthropic or Google")

    def scenario_all_recover(self):
        """Restore all providers to healthy state."""
        for provider in ("openai", "anthropic", "google"):
            print(self.restore_provider(provider))
        print("✅  All providers healthy")

    def scenario_cascade_failure(self):
        """Demo scenario: OpenAI + Anthropic down → only Google available."""
        print("🔴  Scenario: Cascade failure (OpenAI + Anthropic down)")
        print(self.simulate_outage("openai"))
        print(self.simulate_outage("anthropic"))
        print("    → Requests will route exclusively to Google")

    def print_status(self):
        status = self.status()
        print("\n── Provider Health ─────────────────────────────")
        for name, info in status.items():
            state_icon = {"CLOSED": "🟢", "OPEN": "🔴", "HALF_OPEN": "🟡"}.get(info["state"], "⚪")
            print(f"  {state_icon}  {name:12} {info['state']:10} "
                  f"failures={info['failure_count']}")
        print()


# ── Standalone demo runner ─────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    providers = build_providers()
    fm        = FailoverManager(providers)
    sim       = ProviderSimulator(fm)

    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    commands = {
        "status":    sim.print_status,
        "down-oai":  sim.scenario_openai_down,
        "cascade":   sim.scenario_cascade_failure,
        "recover":   sim.scenario_all_recover,
    }

    if cmd in commands:
        commands[cmd]()
    else:
        print(f"Unknown command '{cmd}'. Available: {list(commands)}")
