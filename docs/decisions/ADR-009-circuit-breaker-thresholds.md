# ADR-009: Circuit Breaker Thresholds — 5 Failures, 60s Open, 3 Half-Open Probes

> Status: Accepted | Date: Architecture Phase | Deciders: Architecture Team

---

## Context

The failover engine uses a circuit breaker pattern to prevent cascading failures when an LLM provider is degraded. Three parameters define the circuit breaker behaviour:

1. **Failure threshold** — how many consecutive failures before opening the circuit
2. **Open duration** — how long to keep the circuit open before probing
3. **Half-open probe count** — how many successful probes before closing the circuit

## Decision

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Failure threshold | **5 consecutive failures** | Avoids false positives from transient errors |
| Open duration | **60 seconds** | Gives provider time to recover; short enough to restore service quickly |
| Half-open probes | **3 successful probes** | Confirms recovery is stable before full restoration |

## State Machine

```
         5 consecutive failures
CLOSED ─────────────────────────► OPEN
  ▲                                 │
  │                                 │ 60 seconds elapsed
  │                                 ▼
  │          3 successful      HALF-OPEN
  └──────────────────────────── (probe mode)
         probes pass                │
                                    │ any failure
                                    ▼
                                  OPEN (reset timer)
```

## Rationale

### Why 5 Failures (not 3 or 10)?

- **3 failures** is too sensitive — transient network blips or rate limit spikes would open the circuit unnecessarily, causing unnecessary failovers
- **10 failures** is too lenient — too many requests fail before protection kicks in
- **5 failures** is the Netflix Hystrix default and widely validated in production systems

### Why 60 Seconds Open (not 30s or 120s)?

- **30s** may not give providers enough time to recover from transient overload
- **120s** is too long — unnecessary traffic loss if provider recovered in 45s
- **60s** matches the industry-standard recovery window for LLM provider rate limit resets

### Why 3 Half-Open Probes (not 1)?

- **1 probe** risks re-closing on a lucky successful request during partial recovery
- **3 probes** provides statistical confidence that recovery is genuine
- Aligns with Resilience4j defaults

## Implementation

```python
# src/gateway/failover.py
CIRCUIT_BREAKER_CONFIG = {
    "failure_threshold": 5,      # consecutive failures to open
    "open_duration_s":   60,     # seconds before half-open probe
    "probe_count":       3,      # successful probes to close
}
```

## Consequences

- **Positive:** Circuit breaker verified in Demo 6 (8/8 PASS)
- **Positive:** Failover time < 500ms (NFR-07) — circuit state is in-memory, no network call
- **Positive:** Thresholds are industry-validated (Netflix Hystrix, Resilience4j defaults)
- **Negative:** During 60s open period, affected provider receives zero traffic even if it partially recovers
- **Mitigation:** Half-open probing at 60s restores service without full window expiry

## Related

- FR-02: Intelligent failover routing
- NFR-07: Failover time < 500ms
- ADR-004: Simulated providers (enables failure injection for Demo 6)
- `docs/03-Use-Cases.md`: UC-03 (Failover), UC-05 (Circuit Breaker)
- `docs/04-Test-Cases.md`: TC-06
