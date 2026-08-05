# Skill: Architecture

## Identity
- **Skill ID**: `architecture-skill`
- **Domain**: System Design & Architecture
- **Used By**: Architecture Review Agent, Documentation Agent

---

## Purpose

Provides deep knowledge of the LLM Gateway system design so that agents can review,
validate, and improve architectural decisions against the Technothon evaluation rubrics.

---

## Core Architecture Knowledge

### System Layers (Top → Bottom)

```
Client Applications
        │
        ▼
┌─────────────────────────────────┐
│         API Gateway Layer        │  ← Request Handler, NFR Parser, Load Balancer
└─────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────┐
│    Intelligent Routing Engine    │  ← Model Selector, Failover Logic, Rule Engine
└─────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────┐
│      Semantic Caching System     │  ← Redis L1 + Vector DB L2, Embedding Service
└─────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────┐
│    Request Queue & Rate Limiter  │  ← Priority Queue, Token Bucket, Tier Quotas
└─────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────┐
│    LLM Provider Abstraction      │  ← OpenAI, Anthropic, Google, Azure, Bedrock
└─────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────┐
│   Analytics & Observability      │  ← Time-Series DB, Dashboard, NLU Interface
└─────────────────────────────────┘
```

---

## NFR Header Specification

| Header | Values | Weight in Scoring |
|--------|--------|-------------------|
| `X-NFR-Latency` | `low` / `medium` / `high` | 30% |
| `X-NFR-Cost` | `low` / `medium` / `high` | 40% |
| `X-NFR-Accuracy` | `standard` / `high` / `critical` | 30% |
| `X-Model-Preference` | model name (optional override) | — |
| `X-Context-Window` | `4k` / `8k` / `16k` / `32k` / `128k` | — |
| `X-Stream-Required` | `true` / `false` | — |

**Source files**: `src/gateway/nfr_parser.py`, `src/gateway/model_selector.py`

---

## Model Selection Algorithm

Scoring formula:
```
score = (latency_score × 0.30) + (cost_score × 0.40) + (accuracy_score × 0.30)
```

NFR-to-Model Mapping:

| NFR Combination | Primary | Fallback 1 | Fallback 2 |
|-----------------|---------|------------|------------|
| Low Latency + Low Cost | GPT-3.5-Turbo | Claude Haiku | Gemini Pro |
| Low Latency + High Accuracy | GPT-4-Turbo | Claude Sonnet | Gemini Pro |
| High Accuracy + Low Cost | Claude Sonnet | GPT-4 | Gemini Pro |
| High Accuracy + Any Cost | GPT-4 | Claude Opus | Gemini Ultra |
| Low Cost + Standard Accuracy | GPT-3.5-Turbo | Claude Haiku | Gemini Flash |
| Large Context + Low Cost | Claude Sonnet | GPT-4-Turbo | Gemini Pro |
| Streaming Required | GPT-4-Turbo | Claude Sonnet | Gemini Pro |

---

## Multi-Level Failover Strategy

```
Level 1 → Same model, different provider   (GPT-4 OpenAI → GPT-4 Azure)
Level 2 → Same model, different region     (GPT-4 us-east-1 → GPT-4 us-west-2)
Level 3 → Different model, same family     (GPT-4-Turbo → GPT-4)
Level 4 → Different model, different family (GPT-4 → Claude Opus)
Circuit Breaker → Opens after 5 failures, 60 s timeout, 3 half-open probes
```

**Source files**: `src/gateway/failover.py`, `src/providers/registry.py`

---

## Semantic Cache Architecture

| Layer | Technology | TTL | Eviction |
|-------|-----------|-----|----------|
| L1 Hot Cache | Redis | 24 h | LRU |
| L2 Vector Store | Pinecone / Milvus / Qdrant | 7 days | LRU |
| Similarity Threshold | Cosine similarity ≥ 0.75 | — | — |
| Embedding Model | OpenAI Ada-002 / Cohere | — | — |

**Source file**: `src/cache/semantic_cache.py`

---

## Tier-Based Rate Limits

| Tier | Req/Min | Req/Day | Tokens/Day | Queue Priority |
|------|---------|---------|------------|----------------|
| Free | 10 | 1,000 | 50,000 | 1 |
| Basic | 100 | 50,000 | 5,000,000 | 5 |
| Pro | 500 | 500,000 | 50,000,000 | 10 |
| Enterprise | 5,000 | Unlimited | Unlimited | 20 |

**Source file**: `src/api/middleware/rate_limit.py`

---

## Data Architecture

### PostgreSQL Core Tables
| Table | Purpose |
|-------|---------|
| `models` | Model catalog — provider, family, cost/token, latency, capabilities |
| `users` | User profiles — tier, api_key_hash, quotas, daily/monthly usage |
| `requests` | Time-series request log — model, tokens, cost, latency, cache_hit, NFR params |
| `routing_rules` | JSONB conditions and actions for routing engine |
| `provider_health` | Real-time availability, latency, error rate, circuit breaker state |

### Redis Keys
| Key Pattern | Structure | TTL |
|-------------|-----------|-----|
| `ratelimit:{user_id}:{window}` | Token bucket | 60 s |
| `cache:meta:{prompt_hash}` | Hot cache metadata | 24 h |
| `requests:queue:{tier}` | Sorted set (score = priority × 1M + timestamp) | — |

---

## Architecture Decision Rules (Enforce in Reviews)

1. **No hardcoded secrets** — all keys via `.env` or Secrets Manager
2. **No direct provider calls from API layer** — must pass through Provider Abstraction Layer
3. **No synchronous blocking I/O in cache lookup** — cache must be non-blocking
4. **Semantic cache threshold must remain configurable** — currently `0.75` in `.env`
5. **Circuit breaker state must be persisted** — not in-memory only for production
6. **All routing decisions must emit analytics events** — for dashboard accuracy
7. **New providers must implement the unified Provider interface** — no bespoke integrations
8. **No new microservices without a mapped Technothon requirement** — per agent boundary rules

---

## Evaluation Rubric Targets (Architecture Score)

| Criterion | Target (Score 5) | Source |
|-----------|-----------------|--------|
| NFR parse accuracy | 100%, < 5 ms | `nfr_parser.py` |
| Model selection accuracy | > 98% | `model_selector.py` |
| Failover time | < 300 ms | `failover.py` |
| Cache hit rate | > 50% | `semantic_cache.py` |
| Cache lookup latency | < 30 ms | `semantic_cache.py` |
| API P95 latency (cached) | < 300 ms | `router.py` |
| API P95 latency (uncached) | < 1.5 s | `router.py` |

---

## Source File Map

| Concern | File |
|---------|------|
| NFR parsing | `src/gateway/nfr_parser.py` |
| Model selection | `src/gateway/model_selector.py` |
| Failover + circuit breaker | `src/gateway/failover.py` |
| Main orchestrator | `src/gateway/router.py` |
| Semantic cache | `src/cache/semantic_cache.py` |
| Rate limiting | `src/api/middleware/rate_limit.py` |
| Auth middleware | `src/api/middleware/auth.py` |
| Provider registry | `src/providers/registry.py` |
| Analytics collector | `src/analytics/collector.py` |
