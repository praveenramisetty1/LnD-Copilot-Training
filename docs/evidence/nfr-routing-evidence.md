# Evidence — NFR Header Routing & Model Selection

> Demo Scenario: Demo 1 — NFR-Based Model Auto-Selection
> Endpoint: POST /api/v1/route

---

## Test Case 1: Low Latency + Low Cost → GPT-3.5-Turbo

```http
POST /api/v1/route
Authorization: Bearer demo-key
X-NFR-Latency: low
X-NFR-Cost: low
X-NFR-Accuracy: standard
Content-Type: application/json

{ "messages": [{"role": "user", "content": "What is 2+2?"}] }
```

**Response:**
```json
{
  "model": "gpt-3.5-turbo",
  "provider": "openai",
  "score": 0.91,
  "selection_reason": "nfr_match",
  "cost_usd": 0.002,
  "latency_ms": 187,
  "cache_hit": false
}
```

## Test Case 2: High Accuracy + Any Cost → GPT-4

```http
POST /api/v1/route
Authorization: Bearer demo-key
X-NFR-Latency: high
X-NFR-Cost: high
X-NFR-Accuracy: critical
```

**Response:**
```json
{
  "model": "gpt-4",
  "provider": "openai",
  "score": 0.94,
  "selection_reason": "nfr_match",
  "cost_usd": 0.06,
  "latency_ms": 820
}
```

## Test Case 3: Low Cost + Standard Accuracy → Claude Haiku

```http
POST /api/v1/route
Authorization: Bearer demo-key
X-NFR-Latency: medium
X-NFR-Cost: low
X-NFR-Accuracy: standard
```

**Response:**
```json
{
  "model": "claude-3-haiku",
  "provider": "anthropic",
  "score": 0.88,
  "selection_reason": "nfr_match",
  "cost_usd": 0.001,
  "latency_ms": 210
}
```

## Scoring Weights Applied (ADR-008)

| NFR | Weight | Low Score | Medium Score | High Score |
|-----|--------|-----------|--------------|------------|
| Cost | 40% | 1.0 | 0.6 | 0.2 |
| Latency | 30% | 1.0 | 0.6 | 0.2 |
| Accuracy | 30% | 0.2 | 0.6 | 1.0 |
