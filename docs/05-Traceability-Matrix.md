# 05 — Requirements Traceability Matrix (RTM)
**Propeller Technothon | Problem Statement 4: LLM Gateway**

---

## Requirements → Use Cases → Test Cases → Source Code

| Req ID | Requirement | Use Case | Test Cases | Source Module | Eval Category |
|--------|-------------|----------|------------|---------------|---------------|
| REQ-01 | NFR-based model auto-selection via X-NFR-* headers | UC-01 | TC-01, TC-02 | `src/gateway/nfr_parser.py`, `src/gateway/model_selector.py` | Routing & Failover (25%) |
| REQ-02 | Multi-level failover (L1→L4) + circuit breaker | UC-03, UC-08 | TC-04 | `src/gateway/failover.py` | Routing & Failover (25%) |
| REQ-03 | Semantic caching (cosine ≥ **0.75**, TTL 7d) | UC-02 | TC-03 | `src/cache/semantic_cache.py` (POC: pure-Python; Production: + `src/cache/embedding_service.py`) | Caching & Cost (20%) |

> ⚠️ **ADR-003:** Threshold = 0.75 (reduced from 0.95 — empirical testing confirmed 0.95 produced 0% cache hits).
| REQ-04 | Request queuing to prevent provider 429s | UC-04 | TC-05 | `src/api/middleware/rate_limit.py` | Rate Limiting (15%) |
| REQ-05 | Tier-based throttling (Free/Basic/Pro/Enterprise) | UC-04 | TC-05 | `src/api/middleware/rate_limit.py` | Rate Limiting (15%) |
| REQ-06 | Configuration UI for routing rules & model priorities | UC-05 | TC-07 (indirect) | `src/` (frontend — TBD) | Security & Quality (10%) |
| REQ-07 | Analytics dashboard (cost, latency, cache hit rate) | UC-06 | TC-07 | `src/analytics/collector.py`, `src/analytics/dashboard.py` | Analytics (10%) |
| REQ-08 | Conversational analytics interface (NLU queries) | UC-07 | TC-07-03 to 07-06 | `src/analytics/chat_interface.py` *(future scope — ADR-007)* | Analytics (10%) |

---

## Use Cases → Test Cases Cross-Reference

| Use Case | Test Cases Covering It |
|----------|----------------------|
| UC-01 NFR Model Selection | TC-01 (NFR parsing), TC-02 (model scoring) |
| UC-02 Semantic Cache Hit | TC-03 (cache hit/miss/TTL) |
| UC-03 Multi-Level Failover | TC-04 (all failover levels + circuit breaker) |
| UC-04 Rate Limiting & Queue | TC-05 (tier limits, queue priority) |
| UC-05 Config UI | TC-07-01 (indirect — routing rule change verification) |
| UC-06 Analytics Dashboard | TC-07 (cost tracking, cache hit rate, charts) |
| UC-07 Conversational Analytics *(Future Scope — ADR-007)* | TC-07-03 to 07-06 *(future scope — not executed in POC)* |
| UC-08 Provider Health Monitoring | TC-04-06, TC-04-07 (circuit breaker) |

---

## Test Cases → Evaluation Criteria Cross-Reference

| Test Case | Evaluation Category | Weight |
|-----------|-------------------|--------|
| TC-01: NFR Header Parsing | Intelligent Routing & Failover | 25% |
| TC-02: Model Selection Scoring | Intelligent Routing & Failover | 25% |
| TC-03: Semantic Cache | Semantic Caching & Cost Optimization | 20% |
| TC-04: Multi-Level Failover | Intelligent Routing & Failover | 25% |
| TC-05: Rate Limiting & Queue | Rate Limiting & Queue Management | 15% |
| TC-06: Auth & Security | Security & Implementation Quality | 10% |
| TC-07: Analytics (REST API) | Analytics & Conversational Interface | 10% |
| TC-07 NLU subset (07-03 to 07-06) | Analytics — NLU *(Future Scope, ADR-007)* | — |
| TC-08: E2E Happy Path | All categories | All |

---

## NFR Requirements Coverage Matrix

| NFR Header | Parsed | Scored | Routed | Cached | Logged |
|-----------|--------|--------|--------|--------|--------|
| X-NFR-Latency | ✅ REQ-01 | ✅ REQ-01 | ✅ REQ-01 | ✅ REQ-03 | ✅ REQ-07 |
| X-NFR-Cost | ✅ REQ-01 | ✅ REQ-01 | ✅ REQ-01 | ✅ REQ-03 | ✅ REQ-07 |
| X-NFR-Accuracy | ✅ REQ-01 | ✅ REQ-01 | ✅ REQ-01 | ✅ REQ-03 | ✅ REQ-07 |
| X-Model-Preference | ✅ REQ-01 | ✅ REQ-01 | ✅ REQ-01 | — | ✅ REQ-07 |

---

## Coverage Summary

| Area | Requirements | Use Cases | Test Cases | Status |
|------|-------------|-----------|------------|--------|
| Routing & Selection | REQ-01, REQ-02 | UC-01, UC-03, UC-08 | TC-01, TC-02, TC-04 | ✅ Fully Traced |
| Caching | REQ-03 | UC-02 | TC-03 | ✅ Fully Traced |
| Rate Limiting | REQ-04, REQ-05 | UC-04 | TC-05 | ✅ Fully Traced |
| Configuration UI | REQ-06 | UC-05 | TC-07 (partial) | ⚠️ Partially Traced |
| Analytics REST API | REQ-07 | UC-06 | TC-07-01, TC-07-02 | ✅ Fully Traced (POC) |
| Analytics NLU | REQ-08 | UC-07 | TC-07-03 to 07-06 | 📅 Future Scope (ADR-007) |
| Security | — | — | TC-06, TC-08 | ✅ Fully Traced |
