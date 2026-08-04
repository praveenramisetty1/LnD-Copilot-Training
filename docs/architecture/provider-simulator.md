# Provider Simulator Design — LLM Gateway Platform

> Status: Implemented | POC Component
> Decision: ADR-004 — Simulate LLM Providers
> Purpose: Enable reproducible failover and circuit breaker demos without real API calls

---

## Overview

The provider simulator mimics the behaviour of real LLM providers (OpenAI, Anthropic, Google) including response structure, latency, token usage, and configurable failure injection. All 8 demo scenarios are verified against the simulator.

---

## Architecture

```
src/providers/
├── base.py              ← Abstract ProviderBase class
├── simulator.py         ← Core simulator engine
├── openai_sim.py        ← OpenAI-compatible simulator
├── anthropic_sim.py     ← Anthropic-compatible simulator
└── google_sim.py        ← Google-compatible simulator
```

---

## Simulator Engine Design

```python
# src/providers/simulator.py

class ProviderSimulator:
    """
    Simulates an LLM provider with configurable:
    - Response latency (injected sleep)
    - Failure rate (raises ProviderException at rate %)
    - Token usage tracking (for cost estimation)
    - Realistic response structure (matches real API contract)
    """

    def __init__(self, provider_name: str, config: SimulatorConfig):
        self.provider_name = provider_name
        self.failure_rate   = config.failure_rate    # 0.0 – 1.0
        self.latency_ms     = config.latency_ms      # injected delay
        self.model_catalog  = config.model_catalog   # available models

    async def complete(self, request: ChatRequest) -> ChatResponse:
        # 1. Inject configured latency
        await asyncio.sleep(self.latency_ms / 1000)

        # 2. Simulate failure at configured rate
        if random.random() < self.failure_rate:
            raise ProviderException(
                provider=self.provider_name,
                status_code=503,
                message="Simulated provider failure"
            )

        # 3. Generate realistic response
        tokens_in  = len(request.messages[-1].content.split())
        tokens_out = random.randint(50, 300)
        cost_usd   = self._calculate_cost(request.model, tokens_in, tokens_out)

        return ChatResponse(
            model=request.model,
            provider=self.provider_name,
            content=self._generate_response(request),
            usage=TokenUsage(prompt=tokens_in, completion=tokens_out),
            cost_usd=cost_usd,
            latency_ms=self.latency_ms
        )
```

---

## Configuration (via .env)

```env
# Enable/disable simulator (set false for production with real keys)
SIMULATE_PROVIDERS=true

# Per-provider failure rates (0.0 = never fail, 1.0 = always fail)
OPENAI_FAILURE_RATE=0.0
ANTHROPIC_FAILURE_RATE=0.0
GOOGLE_FAILURE_RATE=0.0

# Per-provider simulated latency (milliseconds)
OPENAI_LATENCY_MS=200
ANTHROPIC_LATENCY_MS=350
GOOGLE_LATENCY_MS=280
```

---

## Demo Failure Injection

To trigger Demo 4 (Failover) and Demo 6 (Circuit Breaker), set:

```env
# Demo 4: trigger single failover
ANTHROPIC_FAILURE_RATE=0.3

# Demo 6: trigger circuit breaker (high failure rate)
ANTHROPIC_FAILURE_RATE=0.9
```

The demo script (`demo/run_demo_v2.py`) sets these values programmatically per scenario.

---

## Provider Response Contracts

Each simulator mirrors the real provider API contract exactly:

### OpenAI-Compatible Response

```json
{
  "id": "chatcmpl-sim-uuid",
  "object": "chat.completion",
  "model": "gpt-3.5-turbo",
  "choices": [{
    "index": 0,
    "message": { "role": "assistant", "content": "..." },
    "finish_reason": "stop"
  }],
  "usage": { "prompt_tokens": 12, "completion_tokens": 87, "total_tokens": 99 }
}
```

### Anthropic-Compatible Response

```json
{
  "id": "msg-sim-uuid",
  "type": "message",
  "model": "claude-3-haiku-20240307",
  "content": [{ "type": "text", "text": "..." }],
  "usage": { "input_tokens": 12, "output_tokens": 87 }
}
```

---

## Cost Estimation Model

```python
COST_PER_1K_TOKENS = {
    "gpt-3.5-turbo":    {"input": 0.0005, "output": 0.0015},
    "gpt-4":            {"input": 0.03,   "output": 0.06},
    "gpt-4-turbo":      {"input": 0.01,   "output": 0.03},
    "claude-3-haiku":   {"input": 0.00025,"output": 0.00125},
    "claude-3-sonnet":  {"input": 0.003,  "output": 0.015},
    "claude-3-opus":    {"input": 0.015,  "output": 0.075},
    "gemini-pro":       {"input": 0.0005, "output": 0.0015},
}
```

---

## Production Migration Path

Set `SIMULATE_PROVIDERS=false` in `.env` and provide real API keys:

```env
SIMULATE_PROVIDERS=false
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
```

No code changes required. The provider abstraction layer (`src/providers/base.py`) handles both simulated and real providers transparently via the same `ProviderBase.complete()` interface.

---

## Related

- ADR-004: Decision to simulate providers
- `demo/run_demo_v2.py`: Uses simulator for all 8 demo scenarios
- `docs/evidence/failover-evidence.md`: Circuit breaker and failover evidence
- `docs/04-Test-Cases.md`: TC-04 (Failover), TC-06 (Circuit Breaker)
