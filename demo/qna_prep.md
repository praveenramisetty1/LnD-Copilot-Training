# Q&A Preparation — LLM Gateway POC
**Propeller Technothon | Problem Statement 4**

---

## Q1: Why not just use LiteLLM or OpenRouter?

**Answer:**
> "LiteLLM and OpenRouter are excellent proxies, but they don't solve our specific problems:
> - Neither has **NFR-based automatic model selection** via custom headers
> - Neither has a **priority queue** that prevents provider 429 errors by tier
> - Neither has **semantic caching** that reuses responses for similar prompts
> - OpenRouter is cloud-only — no self-hosted option for data-sensitive workloads
>
> Our gateway adds the intelligence layer on top: it decides *which* model to use
> based on the request's latency, cost, and accuracy requirements — automatically."

| Feature | Our Gateway | LiteLLM | OpenRouter | PortKey |
|---------|:-----------:|:-------:|:----------:|:-------:|
| NFR-based routing | ✅ | ❌ | ❌ | ❌ |
| Semantic caching | ✅ | Partial | ❌ | ✅ |
| Priority queue | ✅ | ❌ | ❌ | ❌ |
| Self-hosted | ✅ | ✅ | ❌ | Partial |
| Analytics NLU chat | ✅ | ❌ | ❌ | ❌ |
| Circuit breaker | ✅ | ❌ | ❌ | Partial |

---

## Q2: How does the NFR scoring algorithm work?

**Answer:**
> "Each model is scored across three dimensions — cost, latency, and accuracy.
> Base weights are: Cost 40%, Latency 30%, Accuracy 30%.
>
> These weights are then multiplied by NFR multipliers:
> - `X-NFR-Latency: low` → latency weight ×2 (speed matters more)
> - `X-NFR-Cost: low` → cost weight ×2 (cheapest model preferred)
> - `X-NFR-Accuracy: critical` → accuracy weight ×2 (quality non-negotiable)
>
> Weights are normalised to sum to 1.0, then applied to per-model scores.
> The model with the highest final score wins."

**Example:**
```
NFR: latency=low, cost=low, accuracy=standard
Adjusted weights: cost=0.36, latency=0.55, accuracy=0.09

gemini-flash score = (cost_score×0.36) + (latency_score×0.55) + (accuracy×0.09)
                   = (0.98×0.36) + (1.00×0.55) + (0.72×0.09)
                   = 0.353 + 0.550 + 0.065 = 0.968  ← wins
```

---

## Q3: What happens if the similarity threshold is too low and wrong answers are returned?

**Answer:**
> "This is a real risk we took seriously. Our default threshold is 0.75 — conservative enough
> to avoid false positives while still catching paraphrased prompts.
>
> We also made the threshold configurable via `CACHE_SIMILARITY_THRESHOLD` in `.env`,
> so operators can tune it per deployment. In production we'd start at 0.90 and lower
> it gradually while monitoring user feedback.
>
> Our test suite (TC-03-04) specifically tests that prompts with cosine similarity ~0.80
> do NOT get a cache hit when the threshold is set to 0.99."

---

## Q4: How does the circuit breaker recover automatically?

**Answer:**
> "The circuit breaker follows the standard three-state pattern:
> 1. **CLOSED** — normal operation, all requests go through
> 2. **OPEN** — after 5 consecutive failures, provider is bypassed for 60 seconds
> 3. **HALF_OPEN** — after timeout, 3 probe requests are sent
>    - If probes succeed → back to CLOSED
>    - If probes fail → back to OPEN for another 60 seconds
>
> All state is persisted to `data/provider_health.json`, so recovery survives restarts.
> The 5 / 60s / 3 values are all configurable via environment variables."

---

## Q5: How do you guarantee zero provider 429 errors?

**Answer:**
> "We absorb all bursts in a Redis Sorted Set priority queue before they reach providers.
> Each user tier has a token bucket rate limit:
>
> | Tier | Requests/min | Queue Priority |
> |------|-------------|----------------|
> | Free | 10 | 1 |
> | Basic | 100 | 5 |
> | Pro | 500 | 10 |
> | Enterprise | 5,000 | 20 |
>
> When a user exceeds their limit, requests are queued — not rejected and not forwarded.
> The queue worker dispatches them as capacity allows.
> Provider rate limits are never exceeded because we control the dispatch rate."

---

## Q6: What is the cost saving evidence?

**Answer:**
> "In our seeded demo dataset of 200 requests:
> - 40% were served from cache at $0.00 provider cost
> - The remaining 60% were routed to the cheapest model meeting the NFR
>
> Conservative scenario (40% hit rate):
> - Baseline cost (no gateway): $1,000/day at 100K requests
> - With gateway: $600/day
> - **Annual saving: $144,000**
>
> Embedding costs (Ada-002 at $0.0001/1K tokens) are factored in.
> Net saving remains >40% even after embedding overhead."

---

## Q7: Why use local JSON files instead of Redis/PostgreSQL?

**Answer:**
> "For the POC, local JSON files give us:
> - Zero infrastructure dependencies — `pip install` and run
> - Easy inspection and debugging — open the file in VS Code
> - Identical interface to production — we'd swap `SemanticCache._save()` for Qdrant,
>   `AnalyticsCollector._save()` for TimescaleDB, and the circuit breaker for Redis
>
> The production migration path is documented in `docs/06-HLD.md` Section 7.
> Every storage module has a clear interface — swapping backends is a single-file change."

---

## Q8: How does the tier system prevent abuse?

**Answer:**
> "Three layers of enforcement:
> 1. **API key → tier binding**: tier is set at key creation, stored server-side
> 2. **Model access control**: free tier cannot use GPT-4 or Claude-3-Opus (registry.py)
> 3. **Rate limiting**: token bucket per user per 60-second window in Redis
>
> A free-tier user cannot self-upgrade by passing `user_tier: enterprise` in the body —
> the middleware-resolved tier always wins unless the body value is *lower* than the key tier."

---

## Q9: What would you change for a production deployment?

**Answer:**
> "Five key changes:
> 1. **Redis** replaces in-memory rate limiter and L1 cache metadata
> 2. **Qdrant** replaces local JSON vector store (horizontal scaling, persistence)
> 3. **TimescaleDB** replaces analytics JSON (time-series queries, retention policies)
> 4. **Kubernetes** replaces Docker Compose (HPA on CPU + RPS metrics)
> 5. **AWS Secrets Manager / Vault** replaces `.env` file
>
> The gateway code itself doesn't change — only the storage adapters.
> This is why we designed with clear module boundaries from day one."

---

## Q10: What is your test coverage and how did you ensure quality?

**Answer:**
> "Our test suite covers:
> - **Unit tests**: NFR parser (17 tests), model selector (16 tests),
>   failover/circuit breaker (17 tests), semantic cache (15 tests)
> - **Integration tests**: full POST /api/v1/route lifecycle (14 tests)
> - **Load tests**: Locust file with 3 scenarios (mixed, cache-heavy, failover)
>
> The CI pipeline (`.github/workflows/ci.yml`) runs all tests on every push,
> fails if coverage drops below 70%, and runs `bandit` for security scanning.
>
> Key design principle: every module is independently testable —
> no global state, injectable file paths via env vars, mock-friendly interfaces."
