# Evidence — Failover & Circuit Breaker

> Demo Scenarios: Demo 4 (Failover) + Demo 6 (Circuit Breaker)
> Source: src/gateway/failover.py | ADR-009

---

## Demo 4 — L1 Failover on Provider Failure

```http
POST /api/v1/route
Authorization: Bearer demo-key
X-NFR-Latency: low
X-NFR-Cost: low

{ "messages": [{"role": "user", "content": "What is machine learning?"}] }
```

**Internal Execution Log:**
```
[ROUTER] Primary model selected: claude-3-haiku (anthropic)
[PROVIDER] anthropic/claude-3-haiku → FAILURE (injected, failure_rate=0.3)
[FAILOVER] L1: Attempting same model, different provider...
[FAILOVER] L1: No alternative provider for claude-3-haiku
[FAILOVER] L2: Attempting different model, same family...
[FAILOVER] L2: openai/gpt-3.5-turbo → SUCCESS
[ROUTER] Response returned via failover in 0.8ms
```

**Response:**
```json
{
  "model": "gpt-3.5-turbo",
  "provider": "openai",
  "failover_triggered": true,
  "failover_level": "L2",
  "original_model": "claude-3-haiku",
  "latency_ms": 201,
  "cache_hit": false
}
```

---

## Demo 6 — Circuit Breaker OPEN → HALF-OPEN → CLOSED

**Step 1: Inject 5 consecutive failures into anthropic**
```
[CB] anthropic failure count: 1/5
[CB] anthropic failure count: 2/5
[CB] anthropic failure count: 3/5
[CB] anthropic failure count: 4/5
[CB] anthropic failure count: 5/5 — THRESHOLD REACHED
[CB] anthropic circuit: CLOSED → OPEN (duration: 60s)
```

**Step 2: Request during OPEN state**
```
[CB] anthropic circuit: OPEN — bypassing provider
[FAILOVER] Routing to openai/gpt-3.5-turbo (fallback)
```

**Step 3: Half-open probe after 60s**
```
[CB] anthropic circuit: OPEN → HALF-OPEN (60s elapsed)
[CB] Probe 1/3: SUCCESS
[CB] Probe 2/3: SUCCESS
[CB] Probe 3/3: SUCCESS
[CB] anthropic circuit: HALF-OPEN → CLOSED (recovery confirmed)
```

## Circuit Breaker Thresholds (ADR-009)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Failure threshold | 5 | Netflix Hystrix default |
| Open duration | 60s | Standard provider recovery window |
| Half-open probes | 3 | Resilience4j default |
