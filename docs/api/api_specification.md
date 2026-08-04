# API Specification — LLM Gateway Platform

> Status: Draft | Version: 1.0

---

## Base URL
```
http://localhost:8000
```

> ⚠️ **POC vs. Production Note:**
> The POC implementation exposes the gateway at `POST /api/v1/route`.
> The production target endpoint is `POST /v1/chat/completions` (OpenAI-compatible, per ADR-004).
> All examples below reflect the production API contract. For POC demo, substitute `/v1/chat/completions` with `/api/v1/route`.

---

## Authentication
All requests require an API key passed as a Bearer token:
```
Authorization: Bearer {api_key}
```

---

## Endpoints

### POST /api/v1/route *(POC)* · POST /v1/chat/completions *(Production target)*
Main chat completion endpoint with NFR-based routing.

> **POC endpoint:** `POST /api/v1/route` (implemented, demo-verified 8/8 PASS)
> **Production endpoint:** `POST /v1/chat/completions` (OpenAI-compatible, ADR-004 — production target)

**Request Headers:**
| Header | Values | Description |
|--------|--------|-------------|
| `X-NFR-Latency` | `low` \| `medium` \| `high` | Latency requirement |
| `X-NFR-Cost` | `low` \| `medium` \| `high` | Cost sensitivity |
| `X-NFR-Accuracy` | `standard` \| `high` \| `critical` | Accuracy requirement |
| `X-Model-Preference` | `gpt-4` \| `claude-3-opus` \| `gemini-pro` | Optional model hint |
| `X-Context-Window` | `4k` \| `8k` \| `16k` \| `32k` \| `128k` | Context window size |
| `X-Stream-Required` | `true` \| `false` | Enable streaming |

**Request Body:**
```json
{
  "messages": [
    { "role": "system", "content": "You are a helpful assistant." },
    { "role": "user",   "content": "What is the capital of France?" }
  ],
  "temperature": 0.7,
  "max_tokens": 500,
  "stream": false
}
```

**Response:**
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1738670400,
  "model": "gpt-4-turbo",
  "provider": "openai",
  "choices": [
    {
      "index": 0,
      "message": { "role": "assistant", "content": "The capital of France is Paris." },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 25,
    "completion_tokens": 8,
    "total_tokens": 33
  },
  "metadata": {
    "cache_hit": false,
    "latency_ms": 1234,
    "cost": 0.002,
    "failover_count": 0,
    "selected_reason": "nfr_match"
  }
}
```

---

### GET /health
Returns gateway health status.

### GET /v1/models
Returns available models and their capabilities.

### GET /v1/analytics/summary
Returns real-time analytics summary.

### POST /v1/analytics/chat
Natural language query over analytics data.

---

---

## Error Codes

| HTTP Status | Code | Description |
|-------------|------|-------------|
| 400 | `invalid_nfr_header` | NFR header value not in allowed enum |
| 401 | `unauthorized` | Missing or invalid API key |
| 413 | `payload_too_large` | Request body exceeds 1MB limit |
| 422 | `validation_error` | Malformed request body (Pydantic) |
| 429 | `rate_limit_exceeded` | Daily quota exhausted for tier |
| 503 | `no_provider_available` | All providers down / circuit breakers open |

## Rate Limit Headers (Response)

| Header | Description |
|--------|-------------|
| `X-RateLimit-Tier` | Consumer tier: free / basic / pro / enterprise |
| `X-RateLimit-Limit` | Requests allowed per minute for this tier |
| `X-RateLimit-Remaining` | Requests remaining in current window |
| `X-RateLimit-Reset` | Unix timestamp when the window resets |

## Additional Endpoints

### GET /health
```json
{ "status": "ok", "version": "1.0.0", "providers": {"openai": "CLOSED", "anthropic": "CLOSED", "google": "CLOSED"} }
```

### GET /v1/models
Returns available models and their NFR capability scores.

### GET /v1/analytics/summary
Returns aggregated analytics: total requests, cache hit rate, total cost, provider distribution.

### POST /v1/analytics/chat
> 📅 **Future Scope** — NLU conversational analytics interface (not implemented in POC).

Accepts natural language query; returns analytics data and chart.

```json
{ "query": "What was my total cost today?" }
```
