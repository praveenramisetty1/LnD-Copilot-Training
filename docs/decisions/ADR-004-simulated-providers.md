# ADR-004: Simulate LLM Providers (No Real API Calls in POC)

> Status: Accepted | Date: POC Phase | Deciders: Architecture Team

---

## Context

The gateway routes requests to OpenAI, Anthropic, and Google LLM providers. Using real API calls during development and demo would incur costs, require live credentials, and introduce external failure dependencies that cannot be controlled during evaluation.

## Decision

Implement **simulated LLM providers** that mimic real provider behaviour including:
- Configurable response latency (injected delay)
- Configurable failure rates (to trigger failover and circuit breaker demos)
- Realistic response structure matching real provider API contracts
- Cost estimation based on token counts

## Implementation

```python
# src/providers/simulator.py
# Each provider simulator:
# - Accepts same request format as real provider
# - Injects configurable latency (e.g. openai_latency_ms=200)
# - Raises ProviderException at configured failure_rate (0.0–1.0)
# - Returns realistic ChatCompletion response structure
# - Tracks token usage for cost estimation
```

## Configurable Parameters (via .env)

```env
SIMULATE_PROVIDERS=true
OPENAI_FAILURE_RATE=0.0
ANTHROPIC_FAILURE_RATE=0.3
GOOGLE_FAILURE_RATE=0.0
OPENAI_LATENCY_MS=200
ANTHROPIC_LATENCY_MS=350
GOOGLE_LATENCY_MS=280
```

## Rationale

| Factor | Real Providers | Simulated Providers |
|--------|---------------|---------------------|
| Cost | $$ per demo run | $0 |
| Credentials | Required | Not required |
| Failure control | None | Fully configurable |
| Latency control | None | Fully configurable |
| Offline demo | Impossible | Fully supported |
| API contract fidelity | Exact | Mirrored |

## Consequences

- **Positive:** Demo runs at $0 with no external dependencies
- **Positive:** Failover and circuit breaker scenarios are reproducible and controllable
- **Positive:** All 8 demo scenarios verified PASS with simulated providers
- **Negative:** Simulated latency does not reflect real-world provider variability
- **Negative:** Real token cost accuracy requires production validation
- **Mitigation:** Cost estimation logic is production-ready; only the provider call is simulated

## Production Migration Path

Set `SIMULATE_PROVIDERS=false` and provide real API keys in `.env`. No code changes required — the provider abstraction layer handles both modes transparently.

## Related

- ADR-001: Tech stack selection
- FR-02: Intelligent failover routing
- Demo scenarios: Demo 4 (failover), Demo 6 (circuit breaker)
