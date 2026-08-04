# NFR Routing Guide — LLM Gateway Platform

> Status: Draft | Version: 1.0

---

## What are NFRs?

NFR (Non-Functional Requirements) headers allow clients to express routing preferences without specifying a model directly. The gateway scores available models against these requirements and selects the best match.

---

## Supported NFR Headers

| Header | Allowed Values | Default | Description |
|--------|---------------|---------|-------------|
| `X-NFR-Latency` | `low` \| `medium` \| `high` | `medium` | Speed priority |
| `X-NFR-Cost` | `low` \| `medium` \| `high` | `medium` | Cost sensitivity |
| `X-NFR-Accuracy` | `standard` \| `high` \| `critical` | `standard` | Quality requirement |
| `X-Model-Preference` | model name | _(none)_ | Optional hint |
| `X-Context-Window` | `4k` \| `8k` \| `16k` \| `32k` \| `128k` | `8k` | Min context size |
| `X-Stream-Required` | `true` \| `false` | `false` | Streaming mode |

---

## Scoring Algorithm

Each available model is scored across three dimensions:

```
Final Score = (Latency Score × 0.30)
            + (Cost Score × 0.40)
            + (Accuracy Score × 0.30)
```

The model with the highest score is selected.

---

## NFR → Model Mapping Reference

| Latency | Cost | Accuracy | Selected Model | Fallback 1 | Fallback 2 |
|---------|------|----------|---------------|------------|------------|
| low | low | standard | GPT-3.5-Turbo | Claude Haiku | Gemini Flash |
| low | medium | high | GPT-4-Turbo | Claude Sonnet | Gemini Pro |
| high | low | standard | GPT-3.5-Turbo | Claude Haiku | Gemini Flash |
| medium | medium | critical | GPT-4 | Claude Opus | Gemini Ultra |
| low | high | critical | GPT-4 | Claude Opus | Gemini Ultra |
| medium | low | high | Claude Sonnet | GPT-4 | Gemini Pro |

---

## Example Usage

> **POC endpoint:** `POST /api/v1/route` | **Production target:** `POST /v1/chat/completions` (ADR-004)

```http
POST /api/v1/route
Authorization: Bearer {api_key}
X-NFR-Latency: low
X-NFR-Cost: low
X-NFR-Accuracy: standard

{
  "messages": [{"role": "user", "content": "Summarize this text..."}]
}
```

Response will include the selected model and reason:
```json
{
  "model": "gpt-3.5-turbo",
  "metadata": {
    "selected_reason": "nfr_match",
    "nfr_score": 87.5
  }
}
```

---

---

## Advanced Routing Rules

The gateway supports override rules that take precedence over the scoring algorithm. Rules are evaluated in priority order (lowest number = highest priority).

### Rule Structure

```json
{
  "priority": 1,
  "conditions": {
    "tier": "enterprise",
    "nfr_accuracy": "critical"
  },
  "target_model": "gpt-4",
  "fallback_models": ["claude-3-opus"],
  "enabled": true
}
```

### Example Rules

| Priority | Condition | Override Target | Use Case |
|----------|-----------|-----------------|----------|
| 1 | `tier=enterprise AND accuracy=critical` | `gpt-4` forced | SLA guarantee |
| 2 | `context_window=128k` | `claude-3-sonnet` | Long-doc processing |
| 3 | `stream=true` | `gpt-4-turbo` | Real-time UX |
| 10 | _(default)_ | Scoring algorithm | Standard routing |

### Configuring Rules (POC)

In the POC, routing rules are loaded from `config/routing_rules.json` at startup:

```json
[
  {
    "priority": 1,
    "conditions": { "nfr_accuracy": "critical" },
    "target_model": "gpt-4",
    "fallback_models": ["claude-3-opus", "gemini-ultra"],
    "enabled": true
  }
]
```

Runtime rule updates are a production feature via the Admin API (`PUT /admin/routing-rules/{id}` — see `docs/architecture/config-ui-design.md`).

---

## A/B Testing Configuration

> 📅 **Future Scope** — A/B testing is a production feature (Path B). Design is documented here for completeness.

A/B testing allows traffic splitting between two model configurations to compare cost, latency, or quality outcomes.

### Designed A/B Rule Structure

```json
{
  "experiment_id": "exp-001",
  "description": "GPT-4 vs Claude Opus for accuracy-critical requests",
  "condition": { "nfr_accuracy": "critical" },
  "variants": [
    { "model": "gpt-4",       "traffic_pct": 50, "label": "control" },
    { "model": "claude-3-opus", "traffic_pct": 50, "label": "challenger" }
  ],
  "metrics": ["latency_ms", "cost_usd", "user_rating"],
  "enabled": false
}
```

### Traffic Splitting Logic (Designed)

```python
# Deterministic split using request_id hash (avoids session inconsistency)
variant = "control" if hash(request_id) % 100 < 50 else "challenger"
```

### POC Note

A/B testing is **not active in the POC**. The scoring algorithm always selects the highest-scoring model. To implement A/B testing in production, add experiment rules to the routing rule engine and enable the traffic splitter middleware.
