# 04 — Test Cases
**Propeller Technothon | Problem Statement 4: LLM Gateway**

---

## Test Strategy

| Layer | Scope | Tool |
|-------|-------|------|
| Unit | Individual functions (NFR parser, model selector, scoring) | pytest |
| Integration | Module interactions (API → gateway → cache → provider) | pytest + httpx |
| E2E | Full request lifecycle via HTTP | pytest + httpx / Postman |
| Load | Throughput, latency under concurrent load | Locust / k6 |
| Security | Auth, input validation, injection attempts | pytest + manual |

---

## TC-01: NFR Header Parsing

| Field | Value |
|-------|-------|
| **ID** | TC-01 |
| **Category** | Unit |
| **Component** | `src/gateway/nfr_parser.py` |
| **Objective** | Verify all NFR headers are correctly parsed into structured NFR object |

| # | Test Case | Input | Expected Output | Pass Criteria |
|---|-----------|-------|-----------------|---------------|
| 01-01 | All headers present | `X-NFR-Latency: low`, `X-NFR-Cost: high`, `X-NFR-Accuracy: critical` | `{latency: low, cost: high, accuracy: critical}` | Exact match |
| 01-02 | Missing latency header | `X-NFR-Cost: low`, `X-NFR-Accuracy: standard` | `{latency: medium, cost: low, accuracy: standard}` | Default applied |
| 01-03 | All headers missing | _(no NFR headers)_ | `{latency: medium, cost: medium, accuracy: standard}` | All defaults |
| 01-04 | Invalid header value | `X-NFR-Latency: ultra` | HTTP 400 Bad Request | Validation error returned |
| 01-05 | Case-insensitive values | `X-NFR-Latency: LOW` | `{latency: low}` | Normalised correctly |

---

## TC-02: Model Selection / Scoring Algorithm

| Field | Value |
|-------|-------|
| **ID** | TC-02 |
| **Category** | Unit |
| **Component** | `src/gateway/model_selector.py` |
| **Objective** | Verify weighted scoring selects the correct model for each NFR combination |

| # | Test Case | NFR Input | Expected Model | Pass Criteria |
|---|-----------|-----------|----------------|---------------|
| 02-01 | Low latency, low cost, standard accuracy | `{latency:low, cost:low, accuracy:standard}` | GPT-3.5-Turbo | Top-scored model matches |
| 02-02 | High accuracy, any cost | `{latency:medium, cost:high, accuracy:critical}` | GPT-4 or Claude Opus | High-accuracy model selected |
| 02-03 | Low cost priority | `{latency:high, cost:low, accuracy:standard}` | GPT-3.5-Turbo or Claude Haiku | Cheapest adequate model |
| 02-04 | Model preference hint respected | `X-Model-Preference: claude-3-opus` + any NFR | Claude Opus boosted in ranking | Preference increases score |
| 02-05 | No available models | All providers down | HTTP 503 | Graceful error returned |

---

## TC-03: Semantic Cache

| Field | Value |
|-------|-------|
| **ID** | TC-03 |
| **Category** | Integration |
| **Component** | `src/cache/semantic_cache.py` (POC: pure-Python cosine similarity; Production: Qdrant + Ada-002) |
| **Objective** | Verify semantic cache correctly identifies hits and misses |

> ⚠️ **ADR-003:** Similarity threshold = **0.75** (reduced from original design value of 0.95 — empirical testing showed 0.95 produced 0% cache hits in demo conditions).

| # | Test Case | Input Prompt | Expected Result | Pass Criteria |
|---|-----------|-------------|-----------------|---------------|
| 03-01 | Exact cache hit | Same prompt sent twice | Second call: `cache_hit: true` | Response from cache |
| 03-02 | Semantic cache hit | *"Capital of France?"* then *"What city is France's capital?"* | Second call: `cache_hit: true` | Cosine sim ≥ 0.75 (ADR-003) |
| 03-03 | Cache miss | Completely unrelated prompt | `cache_hit: false` | Provider called |
| 03-04 | Below similarity threshold | Slightly different but distinct prompt (cosine ~0.60) | `cache_hit: false` | Threshold 0.75 respected (ADR-003) |
| 03-05 | Cache TTL expiry | Prompt cached, wait for TTL to expire | Re-caches on next call | Expired entry not served |
| 03-06 | Cache latency | Cached request | Response latency < 100ms | Performance verified |

---

## TC-04: Multi-Level Failover

| Field | Value |
|-------|-------|
| **ID** | TC-04 |
| **Category** | Integration |
| **Component** | `src/gateway/failover.py`, `src/simulator/` |
| **Objective** | Verify failover levels trigger correctly on provider failure |

| # | Test Case | Simulated Failure | Expected Behaviour | Pass Criteria |
|---|-----------|------------------|--------------------|---------------|
| 04-01 | Level 1 failover | OpenAI 503 | Retry on Azure OpenAI | Response received; `failover_count: 1` |
| 04-02 | Level 2 failover | OpenAI + Azure 503 | Retry in different region | Response received; `failover_count: 2` |
| 04-03 | Level 3 failover | All GPT-4 providers down | Switch to GPT-4-Turbo | Same family model used |
| 04-04 | Level 4 failover | Entire OpenAI family down | Switch to Claude Opus | Different family used |
| 04-05 | All providers down | All providers 503 | HTTP 503 with clear error | Graceful failure |
| 04-06 | Circuit breaker opens | 5 consecutive OpenAI failures | OpenAI bypassed for 60s | CB state = OPEN |
| 04-07 | Circuit breaker recovery | OpenAI recovers after 60s | 3 probes sent; CB = CLOSED | Normal routing resumes |
| 04-08 | Failover latency | OpenAI timeout triggers failover | Failover completes < 500ms | Timing verified |

---

## TC-05: Rate Limiting & Queue

| Field | Value |
|-------|-------|
| **ID** | TC-05 |
| **Category** | Integration |
| **Component** | `src/api/middleware/rate_limit.py` (POC: in-memory token bucket; Production: Redis Queue — ADR-002) |
| **Objective** | Verify tier-based rate limits and queue behaviour |

> ⚠️ **ADR-002:** POC uses in-memory token bucket — no Redis dependency. Production target uses Redis INCR + TTL. Tests below validate in-memory behaviour.

| # | Test Case | Tier | Input | Expected Result | Pass Criteria |
|---|-----------|------|-------|-----------------|---------------|
| 05-01 | Within limit | Free | 10 req/min | All succeed immediately | No queue delay |
| 05-02 | Exceeds limit | Free | 11th req/min | Queued, not rejected | Response eventually returned |
| 05-03 | Pro tier higher limit | Pro | 500 req/min | All succeed | No throttling |
| 05-04 | Priority ordering | Free + Enterprise burst | Mixed requests | Enterprise served first | Queue priority respected |
| 05-05 | Zero provider 429s | Any tier | Burst traffic | No 429 from providers | Queue absorbs spike |
| 05-06 | Daily quota | Free | 1,001st req/day | HTTP 429 with quota message | Daily limit enforced |

---

## TC-06: Authentication & Security

| Field | Value |
|-------|-------|
| **ID** | TC-06 |
| **Category** | Security |
| **Component** | `src/api/middleware/auth.py` |
| **Objective** | Verify authentication and input validation |

| # | Test Case | Input | Expected Result | Pass Criteria |
|---|-----------|-------|-----------------|---------------|
| 06-01 | Valid API key | Correct Bearer token | HTTP 200 | Authenticated |
| 06-02 | Missing API key | No Authorization header | HTTP 401 | Rejected before routing |
| 06-03 | Invalid API key | Wrong token | HTTP 401 | Rejected |
| 06-04 | XSS in prompt | `<script>alert(1)</script>` | Sanitised or rejected | No raw script in response |
| 06-05 | SQL injection in prompt | `'; DROP TABLE users; --` | Safely handled | No DB error |
| 06-06 | Oversized payload | 1MB request body | HTTP 413 | Payload limit enforced |
| 06-07 | Expired JWT | Expired token | HTTP 401 | Token expiry checked |

---

## TC-07: Analytics Dashboard

| Field | Value |
|-------|-------|
| **ID** | TC-07 |
| **Category** | Integration |
| **Component** | `src/analytics/collector.py`, `data/analytics.json` (POC); TimescaleDB (production) |
| **Objective** | Verify analytics data accuracy via REST API (POC). NLU conversational interface is future scope (ADR-007). |

> ⚠️ **ADR-007:** NLU conversational interface is **not implemented in POC**. TC-07-03 through TC-07-06 are **future scope test cases** — retained for production readiness planning only.

| # | Test Case | Input | Expected Result | Pass Criteria | POC Status |
|---|-----------|-------|-----------------|---------------|------------|
| 07-01 | Cost tracking | 10 requests at known model cost | `GET /v1/analytics/summary` total matches sum | Accurate cost | ✅ Implemented |
| 07-02 | Cache hit rate | 10 requests, 5 from cache | Summary shows 50% hit rate | Correct percentage | ✅ Implemented |
| 07-03 | NLU query — cost | *"What was my cost today?"* | Returns today's total cost | Correct answer | 📅 Future Scope |
| 07-04 | NLU query — provider | *"Which provider was used most this week?"* | Returns top provider | Correct answer | 📅 Future Scope |
| 07-05 | NLU query — latency | *"What is my average response time?"* | Returns P50 latency | Accurate metric | 📅 Future Scope |
| 07-06 | Ambiguous query | *"Show me the data"* | Clarification requested | Graceful fallback | 📅 Future Scope |

---

## TC-08: End-to-End Happy Path

| Field | Value |
|-------|-------|
| **ID** | TC-08 |
| **Category** | E2E |
| **Objective** | Full request lifecycle: auth → NFR parse → cache check → provider → response |

**Steps:**
1. POST `/v1/chat/completions` with valid API key and NFR headers
2. Verify HTTP 200 response
3. Verify `metadata.selected_reason` is present
4. Verify `metadata.latency_ms` < 3000
5. Verify `metadata.cost` > 0
6. Send identical request again → verify `metadata.cache_hit: true`
7. Check analytics dashboard updated with both requests

**Pass Criteria:** All 7 steps pass without error.

---

## Test Coverage Targets

| Module | Unit | Integration | Target Coverage |
|--------|------|-------------|----------------|
| `src/gateway/nfr_parser.py` | ✅ | — | >90% |
| `src/gateway/model_selector.py` | ✅ | — | >90% |
| `src/gateway/failover.py` | ✅ | ✅ | >85% |
| `src/cache/semantic_cache.py` | ✅ | ✅ | >85% |
| `src/api/middleware/auth.py` | ✅ | ✅ | >90% |
| `src/api/middleware/rate_limit.py` | ✅ | ✅ | >85% |
| `src/analytics/` | ✅ | ✅ | >80% |
| **Overall Target** | | | **>85%** |
