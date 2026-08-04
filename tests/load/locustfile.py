# tests/load/locustfile.py
"""
Locust load test — LLM Gateway POC.

Run:
    locust -f tests/load/locustfile.py --host http://localhost:8000

Then open http://localhost:8089 to control the test.

Scenarios:
  GatewayUser  — mixed cached + uncached requests (realistic workload)
  CachedUser   — hammers same prompt to maximise cache hit rate
  FailoverUser — trips circuit breaker then recovers
"""

from locust import HttpUser, task, between


HEADERS_FREE        = {"Authorization": "Bearer free-key-001"}
HEADERS_PRO         = {"Authorization": "Bearer pro-key-001"}
HEADERS_ENTERPRISE  = {"Authorization": "Bearer enterprise-key-001"}


# ── Scenario 1: Realistic mixed workload ──────────────────────────────────────

class GatewayUser(HttpUser):
    wait_time  = between(0.5, 2.0)
    weight     = 70   # 70 % of simulated users

    PROMPTS = [
        "What is the capital of France?",
        "Explain machine learning in simple terms",
        "Write a Python hello world program",
        "What is the speed of light?",
        "How does a neural network work?",
        "What is Docker?",
        "Explain the CAP theorem",
        "What is a REST API?",
        "How do I reverse a string in Python?",
        "What is a microservice architecture?",
    ]
    _prompt_index = 0

    @task(5)
    def route_low_cost(self):
        self.client.post(
            "/api/v1/route",
            json={
                "messages": [{"role": "user", "content": self._next_prompt()}],
                "nfr": {"latency": "medium", "cost": "low", "accuracy": "standard"},
            },
            headers=HEADERS_FREE,
            name="/api/v1/route [low-cost]",
        )

    @task(3)
    def route_low_latency(self):
        self.client.post(
            "/api/v1/route",
            json={
                "messages": [{"role": "user", "content": self._next_prompt()}],
                "nfr": {"latency": "low", "cost": "medium", "accuracy": "standard"},
            },
            headers=HEADERS_PRO,
            name="/api/v1/route [low-latency]",
        )

    @task(2)
    def route_high_accuracy(self):
        self.client.post(
            "/api/v1/route",
            json={
                "messages": [{"role": "user", "content": self._next_prompt()}],
                "nfr": {"latency": "high", "cost": "high", "accuracy": "critical"},
            },
            headers=HEADERS_ENTERPRISE,
            name="/api/v1/route [high-accuracy]",
        )

    @task(1)
    def health_check(self):
        self.client.get("/health", name="/health")

    @task(1)
    def analytics_summary(self):
        self.client.get(
            "/api/v1/analytics/summary",
            headers=HEADERS_FREE,
            name="/api/v1/analytics/summary",
        )

    def _next_prompt(self) -> str:
        prompt = self.PROMPTS[GatewayUser._prompt_index % len(self.PROMPTS)]
        GatewayUser._prompt_index += 1
        return prompt


# ── Scenario 2: Cache stress — maximise hit rate ──────────────────────────────

class CachedUser(HttpUser):
    wait_time  = between(0.1, 0.5)
    weight     = 20   # 20 % of simulated users

    REPEATED_PROMPTS = [
        "What is the capital of France?",
        "What is machine learning?",
        "What is Python?",
    ]
    _idx = 0

    @task
    def cached_route(self):
        prompt = self.REPEATED_PROMPTS[CachedUser._idx % len(self.REPEATED_PROMPTS)]
        CachedUser._idx += 1
        self.client.post(
            "/api/v1/route",
            json={
                "messages": [{"role": "user", "content": prompt}],
                "nfr": {"latency": "low", "cost": "low", "accuracy": "standard"},
            },
            headers=HEADERS_FREE,
            name="/api/v1/route [cached]",
        )


# ── Scenario 3: Failover demo — open/close circuit breakers ──────────────────

class FailoverUser(HttpUser):
    wait_time = between(1.0, 3.0)
    weight    = 10   # 10 % of simulated users

    @task(3)
    def route_after_failover(self):
        """Send a request while OpenAI circuit is open — expects failover."""
        self.client.post(
            "/api/v1/route",
            json={
                "messages": [{"role": "user", "content": "Failover test prompt"}],
                "nfr": {"latency": "medium", "cost": "medium", "accuracy": "standard"},
            },
            headers=HEADERS_ENTERPRISE,
            name="/api/v1/route [failover]",
        )

    @task(1)
    def open_openai_circuit(self):
        self.client.post(
            "/api/v1/providers/openai/circuit/open",
            headers=HEADERS_ENTERPRISE,
            name="/providers/openai/circuit/open",
        )

    @task(1)
    def close_openai_circuit(self):
        self.client.post(
            "/api/v1/providers/openai/circuit/close",
            headers=HEADERS_ENTERPRISE,
            name="/providers/openai/circuit/close",
        )
