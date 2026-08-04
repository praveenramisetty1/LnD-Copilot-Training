# ADR-010: JSON File Store for Analytics (No TimescaleDB in POC)

> Status: Accepted | Date: POC Phase | Deciders: Architecture Team

---

## Context

The system requires analytics storage for per-request metrics (cost, latency, model selected, cache hit, provider used). The production design uses TimescaleDB (a PostgreSQL time-series extension) for optimised time-range queries and materialized views. The POC must run without a database server.

## Decision

Use a **JSON file store (`data/analytics.json`)** for analytics in the POC. No database dependency required.

## Implementation

```python
# src/analytics/collector.py
# Append-only JSON list — each entry is one request record
# {
#   "request_id": "uuid",
#   "timestamp": "2024-01-15T10:23:45Z",
#   "model": "gpt-3.5-turbo",
#   "provider": "openai",
#   "latency_ms": 720,
#   "cost_usd": 0.002,
#   "cache_hit": false,
#   "tier": "pro",
#   "nfr_latency": "low",
#   "nfr_cost": "low",
#   "nfr_accuracy": "standard"
# }
```

## Rationale

| Factor | TimescaleDB (Production) | JSON File (POC) |
|--------|-------------------------|-----------------|
| Infrastructure | PostgreSQL + TimescaleDB extension | None |
| Query capability | Time-range SQL, materialized views | Python list filtering |
| Performance at scale | Millions of rows | ~10K records comfortably |
| Demo suitability | Over-engineered | Sufficient |
| Schema migrations | Alembic required | None |
| Setup time | 10+ minutes | Zero |

## Analytics API (POC)

```http
GET /v1/analytics/summary
Response: {
  "total_requests": 1247,
  "cache_hit_rate": 0.422,
  "total_cost_usd": 4.37,
  "cost_saved_usd": 3.21,
  "avg_latency_ms": 720,
  "p95_latency_ms": 1840,
  "provider_distribution": {"openai": 0.61, "anthropic": 0.29, "google": 0.10}
}
```

## Demo Seed

`demo/seed_demo_data.py` populates `data/analytics.json` with 30 days of realistic request history to produce meaningful dashboard metrics before the demo.

## Consequences

- **Positive:** Zero infrastructure dependency — demo runs immediately after `pip install`
- **Positive:** Analytics verified in Demo 7 and Demo 8 (8/8 PASS)
- **Positive:** Seed script produces consistent, reproducible metrics for evaluation
- **Negative:** No SQL query capability — aggregations done in Python
- **Negative:** Not suitable for production volumes (>100K requests/day)
- **Negative:** No Alembic migration path from JSON → SQL (manual migration required)

## Production Migration Path

1. Deploy PostgreSQL 15 + TimescaleDB 2.14 extension
2. Run Alembic migration with schema defined in `docs/06-HLD.md` Section 3.1
3. Migrate historical JSON records via ETL script
4. Switch `ANALYTICS_BACKEND=timescaledb` in `.env`

## Related

- ADR-007: NLU future scope (depends on TimescaleDB SQL queries)
- ADR-002: In-memory rate limiter (same POC simplification pattern)
- `docs/06-HLD.md`: Section 3.1 — production SQL schema
