# ADR-007: NLU Conversational Analytics Interface — Deferred to Future Scope

> Status: Accepted | Date: POC Phase | Deciders: Architecture Team

---

## Context

The problem statement (FR-08) and evaluation criteria include a conversational analytics interface where users can query metrics using natural language (e.g. "What was my total cost yesterday?"). This requires an NLU pipeline, intent classification, SQL generation, and a chat UI.

## Decision

**Defer the NLU conversational interface to a future release.** The POC delivers analytics via a REST API endpoint (`GET /v1/analytics/summary`) instead.

## Rationale

| Factor | NLU Interface | REST API (POC) |
|--------|--------------|----------------|
| Implementation complexity | High (NLU pipeline + SQL gen + chat UI) | Low (single endpoint) |
| Demo timeline | Exceeds POC scope | Fits POC scope |
| Judge evaluation risk | High (live NLU can fail unpredictably) | Low (deterministic) |
| Analytics coverage | Natural language | All metrics in JSON |
| Score impact | 5/5 if working, 0/5 if broken | Stable 3.5/5 |

## POC Alternative

```http
GET /v1/analytics/summary
Authorization: Bearer {api_key}

Response:
{
  "total_requests": 1247,
  "cache_hit_rate": 0.422,
  "total_cost_usd": 4.37,
  "avg_latency_ms": 720,
  "provider_distribution": {
    "openai": 0.61,
    "anthropic": 0.29,
    "google": 0.10
  },
  "cost_saved_usd": 3.21
}
```

## Production Design (Future)

```
User query → Intent Classifier → SQL Generator → TimescaleDB → Result formatter → Chat response
```

Intent classes: `cost_query`, `latency_query`, `provider_query`, `cache_query`, `volume_query`

## Consequences

- **Positive:** Eliminates highest-risk demo component (live NLU failure in front of judges)
- **Positive:** Analytics REST API delivers all required metrics deterministically
- **Positive:** Architecture is designed for NLU extension — no structural changes needed
- **Negative:** Score target for Analytics category reduced from 4.5 → 3.5
- **Negative:** FR-08 is not fulfilled in POC

## Affected Documents

- `docs/00-Evaluation-Mapping.md`: Score target updated to 3.5
- `docs/03-Use-Cases.md`: UC-07 marked Future Scope
- `docs/04-Test-Cases.md`: TC-07-03 to TC-07-06 marked Future Scope
- `docs/05-Traceability-Matrix.md`: REQ-08 marked Future Scope

## Related

- FR-08: Conversational analytics interface
- ADR-010: JSON analytics store (POC analytics implementation)
