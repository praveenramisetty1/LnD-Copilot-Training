# 03 — Use Cases
**Propeller Technothon | Problem Statement 4: LLM Gateway**

---

## Actors

| Actor | Description |
|-------|-------------|
| **API Consumer** | Developer/application sending LLM requests via REST |
| **Platform Admin** | Configures routing rules, model priorities, tiers |
| **Analytics User** | Views dashboard and submits NLU analytics queries |
| **LLM Provider** | External service (OpenAI, Anthropic, Google, Azure) |
| **Gateway System** | Internal orchestrator (router, cache, queue) |

---

## UC-01: NFR-Based Model Auto-Selection

**Actor:** API Consumer  
**Goal:** Receive a response from the best model matching declared NFR requirements  
**Trigger:** POST /v1/chat/completions with X-NFR-* headers

**Main Flow:**
1. Consumer sends request with `X-NFR-Latency: low`, `X-NFR-Cost: low`, `X-NFR-Accuracy: standard`
2. Auth middleware validates API key → identifies user tier
3. NFR Parser extracts and validates all three NFR header values
4. Model Selector scores each available model against NFR weights (Cost 40%, Latency 30%, Accuracy 30%)
5. Highest-scoring model (e.g., GPT-3.5-Turbo) is selected
6. Request dispatched to selected provider
7. Response returned with `metadata.selected_reason: nfr_match`

**Alternate Flow — Missing NFR Headers:**
- Gateway applies default NFR values: Latency=medium, Cost=medium, Accuracy=standard
- Flow continues from step 4

**Postcondition:** Consumer receives LLM response; routing decision logged to analytics

---

## UC-02: Semantic Cache Hit

**Actor:** API Consumer  
**Goal:** Receive a cached response for a semantically similar prompt  
**Trigger:** POST /v1/chat/completions where a similar prompt was previously cached

**Main Flow:**
1. Consumer sends prompt: *"What is the capital of France?"*
2. Gateway generates embedding via OpenAI Ada-002
3. Qdrant vector search finds cached entry with cosine similarity 0.97 (≥ 0.95 threshold)
4. Cached response returned immediately — no provider call made
5. Response includes `metadata.cache_hit: true`, `metadata.latency_ms: <50`

**Alternate Flow — Cache Miss:**
- Similarity < 0.95 → proceed to provider
- Store new embedding + response in Qdrant with 7-day TTL
- Return `metadata.cache_hit: false`

**Postcondition:** Cost saved; cache hit rate metric incremented

---

## UC-03: Multi-Level Failover

**Actor:** API Consumer, Gateway System  
**Goal:** Complete the request even when the primary provider fails  
**Trigger:** Primary provider returns 5xx or times out

**Main Flow:**
1. Request routed to GPT-4 on OpenAI (primary selection)
2. OpenAI returns 503 Service Unavailable
3. **Level 1 Failover:** Retry GPT-4 on Azure OpenAI → succeeds
4. Response returned with `metadata.failover_count: 1`

**Alternate Flow — Level 1 Fails:**
- **Level 2:** GPT-4 in different region → fails
- **Level 3:** GPT-4-Turbo (same family) → succeeds
- **Level 4:** Claude Opus (different family) → last resort

**Circuit Breaker Scenario:**
- After 5 consecutive OpenAI failures → circuit opens
- All subsequent requests bypass OpenAI for 60 seconds
- After timeout: 3 probe requests determine if OpenAI has recovered

**Postcondition:** Request fulfilled; failover event logged; provider health updated

---

## UC-04: Tier-Based Rate Limiting & Queue

**Actor:** API Consumer (Free Tier)  
**Goal:** Graceful handling when rate limit is reached  
**Trigger:** Free-tier user exceeds 10 requests/minute

**Main Flow:**
1. Free-tier user submits 11th request within 60-second window
2. Rate limiter detects token bucket is empty for this user
3. Request placed in priority queue with score = tier_priority (1) × 1M + timestamp
4. Queue processor waits for next rate limit window (new token bucket fill)
5. Request dispatched to provider when window resets
6. Response returned to consumer with added queue wait time in metadata

**Alternate Flow — Enterprise Tier:**
- Enterprise user has 5,000 req/min → queue rarely needed
- Queue priority = 20 → always processed before lower tiers

**Postcondition:** Zero provider 429 errors; consumer receives response (with delay)

---

## UC-05: Configuration via Admin UI

**Actor:** Platform Admin  
**Goal:** Update routing rules and model priorities without redeployment  
**Trigger:** Admin logs in to Configuration UI

**Main Flow:**
1. Admin authenticates with admin credentials
2. Admin navigates to Routing Rules section
3. Admin creates rule: *"If X-NFR-Accuracy=critical → always use GPT-4 or Claude Opus"*
4. Admin sets GPT-4 priority = 10, Claude Opus priority = 9 for this rule
5. Admin saves → routing_rules table updated in PostgreSQL
6. Gateway router picks up new rule on next request (no restart required)

**Postcondition:** Routing behaviour updated in real time; change logged in audit trail

---

## UC-06: Analytics Dashboard View

**Actor:** Analytics User  
**Goal:** View real-time usage, cost, and performance metrics  
**Trigger:** User opens Analytics Dashboard

**Main Flow:**
1. User opens dashboard at http://localhost:3000
2. Dashboard loads: RPS, P95 latency, cache hit rate, total cost today, error rate
3. Provider distribution pie chart shows: OpenAI 60%, Anthropic 25%, Google 15%
4. User sets date range to "Last 7 days" → trend charts update
5. User drills into a spike → sees individual request details

**Postcondition:** User gains visibility into platform performance and cost

---

## UC-07: Conversational Analytics Query

**Actor:** Analytics User  
**Goal:** Query analytics data using natural language  
**Trigger:** User types a question in the Chat Analytics interface

**Main Flow:**
1. User types: *"What was my total API cost yesterday?"*
2. NLU pipeline classifies intent: `cost_query`, entity: `date=yesterday`
3. Intent translated to SQL: `SELECT SUM(cost) FROM requests WHERE date = CURRENT_DATE - 1`
4. Query executed against TimescaleDB
5. Result returned: *"Your total API cost yesterday was $4.37"* with a bar chart

**Alternate Flow — Ambiguous Query:**
- NLU confidence < 0.7 → system asks clarifying question
- *"Do you mean cost for all providers or just OpenAI?"*

**Postcondition:** User receives accurate analytics data via natural language

---

## UC-08: Provider Health Monitoring

**Actor:** Gateway System (automated)  
**Goal:** Detect and respond to provider degradation proactively  
**Trigger:** Scheduled health check every 30 seconds

**Main Flow:**
1. Gateway pings each provider's health endpoint
2. OpenAI latency: 4,200ms (threshold: 3,000ms) → marked as degraded
3. Circuit breaker transitions OpenAI to HALF-OPEN state
4. Model Selector deprioritises OpenAI in scoring for subsequent requests
5. Grafana alert fires → on-call engineer notified
6. OpenAI recovers → after 3 successful probes → CLOSED state restored

**Postcondition:** Degraded provider automatically deprioritised; engineers alerted; no user impact

---

## Use Case Summary

| ID | Use Case | Priority | Actors |
|----|----------|----------|--------|
| UC-01 | NFR-Based Model Auto-Selection | P0 | API Consumer |
| UC-02 | Semantic Cache Hit/Miss | P0 | API Consumer, Gateway |
| UC-03 | Multi-Level Failover | P0 | API Consumer, Gateway, Provider |
| UC-04 | Tier-Based Rate Limiting & Queue | P0 | API Consumer |
| UC-05 | Configuration via Admin UI | P1 | Platform Admin |
| UC-06 | Analytics Dashboard View | P1 | Analytics User |
| UC-07 | Conversational Analytics Query | P1 | Analytics User |
| UC-08 | Provider Health Monitoring | P1 | Gateway System |
