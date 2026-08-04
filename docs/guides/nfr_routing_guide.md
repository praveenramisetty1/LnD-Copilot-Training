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

```http
POST /v1/chat/completions
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

_TODO: Add advanced routing rules, A/B testing configuration_
