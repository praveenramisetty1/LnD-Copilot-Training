# Evidence — Semantic Cache MISS then HIT

> Demo Scenarios: Demo 2 (MISS) + Demo 3 (HIT)
> Threshold: cosine ≥ 0.75 (ADR-003)

---

## Request 1 — Cache MISS (new prompt)

```http
POST /api/v1/route
Authorization: Bearer demo-key
Content-Type: application/json

{ "messages": [{"role": "user", "content": "Explain quantum computing in simple terms"}] }
```

**Response:**
```json
{
  "cache_hit": false,
  "model": "gpt-3.5-turbo",
  "provider": "openai",
  "latency_ms": 187,
  "cost_usd": 0.002,
  "similarity_score": null
}
```

## Request 2 — Cache HIT (paraphrased prompt)

```http
POST /api/v1/route
Authorization: Bearer demo-key
Content-Type: application/json

{ "messages": [{"role": "user", "content": "Can you explain quantum computing simply?"}] }
```

**Response:**
```json
{
  "cache_hit": true,
  "similarity_score": 0.89,
  "threshold": 0.75,
  "latency_ms": 4,
  "cost_usd": 0.000,
  "cost_saved_usd": 0.002,
  "cached_response": "Quantum computing uses quantum mechanical phenomena..."
}
```

## Cache Performance Summary

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Cache hit latency | 4ms | < 500ms | ✅ |
| Cache miss latency | 187ms | < 2s | ✅ |
| Similarity threshold | 0.75 | — | ADR-003 |
| Hit rate (30-day seeded) | 42.2% | > 40% | ✅ |
| Cost on cache hit | $0.000 | — | ✅ |
