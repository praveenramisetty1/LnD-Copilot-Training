# ADR-002: In-Memory Token Bucket for Rate Limiting (No Redis)

> Status: Accepted | Date: POC Phase | Deciders: Architecture Team

---

## Context

The system requires tier-based rate limiting (Free / Basic / Pro / Enterprise) to enforce per-minute and per-day request quotas. The production design calls for Redis INCR + TTL as a distributed token bucket. However, the POC must run on a single developer machine without infrastructure dependencies.

## Decision

Use an **in-memory Python token bucket** for rate limiting in the POC. No Redis instance is required.

## Implementation

```python
# src/api/middleware/rate_limit.py
# In-memory dict keyed by api_key + window timestamp
# Token bucket replenished per tier quota every 60s
```

## Rationale

| Factor | Redis (Production) | In-Memory (POC) |
|--------|-------------------|-----------------|
| Infrastructure | Requires Redis container | None |
| Distribution | Works across replicas | Single-process only |
| Persistence | Survives restarts | Reset on restart |
| Demo suitability | Over-engineered | Sufficient |
| Setup friction | docker-compose required | Zero |

## Consequences

- **Positive:** Zero infrastructure friction for demo and evaluation
- **Positive:** Rate limiting verified in all 8 demo scenarios (PASS)
- **Negative:** Does not support multi-instance deployments (acceptable for POC)
- **Negative:** Quota resets on gateway restart (acceptable for POC)

## Production Migration Path

Replace in-memory dict with Redis INCR + TTL:

```python
# Production:
redis.incr(f"ratelimit:{user_id}:{window}")
redis.expire(f"ratelimit:{user_id}:{window}", 60)
```

## Related

- ADR-001: Tech stack selection
- ADR-010: JSON analytics store (same pattern — in-memory/file for POC)
