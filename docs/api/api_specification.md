# API Specification — LLM Gateway Platform

> Status: Draft | Version: 1.0

---

## Base URL
```
http://localhost:8000/v1
```

---

## Authentication
All requests require an API key passed as a Bearer token:
```
Authorization: Bearer {api_key}
```

---

## Endpoints

### POST /v1/chat/completions
Main chat completion endpoint with NFR-based routing.

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

_TODO: Expand with full endpoint documentation, error codes, and rate limit headers_
