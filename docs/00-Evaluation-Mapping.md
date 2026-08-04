# 00 — Evaluation Mapping
**Propeller Technothon | Problem Statement 4: LLM Gateway**
> Maps every judge criterion to a concrete deliverable, demo artifact, and scoring target.

---

## Scoring Weight Summary

| Category | Weight | Target Score |
|----------|--------|-------------|
| Intelligent Routing & Failover | 25% | 5.0 |
| Semantic Caching & Cost Optimization | 20% | 5.0 |
| Performance & Scalability | 20% | 4.5 |
| Rate Limiting & Queue Management | 15% | 5.0 |
| Analytics & Conversational Interface | 10% | 3.5 |
| Security & Implementation Quality | 10% | 4.5 |
| **Weighted Total** | **100%** | **≥ 4.7** |

---

## 1. Intelligent Routing & Failover (25%)

| Judge Criterion | What We Build | Demo Evidence | Score Target |
|----------------|---------------|---------------|-------------|
| NFR header parsing (Latency, Cost, Accuracy) | `src/gateway/nfr_parser.py` | Live request with all 3 headers → routing decision log | 5 |
| Model selection algorithm | `src/gateway/model_selector.py` — weighted scoring (Cost 40%, Latency 30%, Accuracy 30%) | Show scoring table in terminal output | 5 |
| Multi-level failover (L1→L2→L3→L4) | `src/gateway/failover.py` | Kill OpenAI mock → show fallback to Azure → Anthropic | 5 |
| Circuit breaker | `src/gateway/failover.py` | 5 failures → circuit opens → 60s timeout → probes | 5 |
| Failover latency < 500ms | Load test + simulator | Screenshot of P95 failover latency metric | 5 |
| Routing rule configurability | Config UI + routing_rules table | Demo rule change → behaviour change in real time | 4 |

---

## 2. Semantic Caching & Cost Optimization (20%)

| Judge Criterion | What We Build | Demo Evidence | Score Target |
|----------------|---------------|---------------|-------------|
| Vector similarity search (cosine ≥ **0.75**, ADR-003) | `src/cache/semantic_cache.py` (POC: pure-Python; Production: + Qdrant) | First call MISS, paraphrased call HIT | 5 |
| Embedding generation | POC: pure-Python tokenisation; Production: `src/cache/embedding_service.py` (Ada-002) | Show cosine similarity score in API response metadata | 4 |
| Cache hit rate > 40% | POC: in-memory cosine store | Dashboard metric: **42.2% verified** ✅ | 5 |
| Cost reduction > 45% | Cost tracker per request | Before/after cost comparison chart | 5 |
| Cache TTL & LRU eviction | `src/cache/cache_manager.py` | Config showing 7-day TTL | 4 |
| Similarity threshold configurability | Config UI | Slider for threshold 0.80–1.00 | 4 |

---

## 3. Performance & Scalability (20%)

| Judge Criterion | What We Build | Demo Evidence | Score Target |
|----------------|---------------|---------------|-------------|
| P95 cached latency < 500ms | FastAPI + Redis L1 | Locust/k6 test result screenshot | 5 |
| P95 uncached latency < 2s | End-to-end routing | Load test results | 4 |
| Throughput > 10,000 RPS | Async FastAPI + Redis | Load test graph | 4 |
| Auto-scaling design | docker-compose replicas + K8s notes in HLD | Architecture diagram | 4 |
| Horizontal scalability | Stateless gateway design | Architecture explanation | 4 |

---

## 4. Rate Limiting & Queue Management (15%)

| Judge Criterion | What We Build | Demo Evidence | Score Target |
|----------------|---------------|---------------|-------------|
| Tier-based throttling (Free/Basic/Pro/Enterprise) | `src/api/middleware/rate_limit.py` | Demo: Free tier hit limit → queued | 5 |
| Token bucket algorithm | Redis INCR + TTL | Show Redis key: ratelimit:{user}:{window} | 5 |
| Priority queue (Enterprise > Pro > Basic > Free) | Redis Sorted Set | Queue dashboard — priority ordering visible | 5 |
| Zero provider 429 errors | Queue absorbs spikes | Load test: 0 provider 429s logged | 5 |
| Dead Letter Queue | DLQ handler | Show failed request in DLQ with retry count | 4 |

---

## 5. Analytics & Conversational Interface (10%)

> ⚠️ **ADR-007 — NLU Conversational Interface = Future Scope.**
> The natural language query interface is **not implemented in the POC**. Analytics are accessible via REST API (`GET /v1/analytics/summary`). Score target adjusted from 4.5 → **3.5**. React dashboard is a production target (Path B only).

| Judge Criterion | What We Build | Demo Evidence | Score Target | POC Status |
|----------------|---------------|---------------|--------------|------------|
| Real-time analytics REST API | `src/analytics/collector.py` | `GET /v1/analytics/summary` — cost, latency, cache hit, provider distribution | 4 | ✅ Implemented |
| Provider distribution tracking | Analytics collector | API response: provider breakdown per request | 4 | ✅ Implemented |
| Cache hit rate & cost savings | Cost tracker + cache layer | **42.2% hit rate**, $0 cost on cached requests | 5 | ✅ Implemented |
| Historical request data | `data/analytics.json` | Seeded 30-day history via `demo/seed_demo_data.py` | 4 | ✅ Implemented |
| Real-time dashboard (React UI) | React + Recharts *(production)* | Path B only — not available in POC demo | 3 | 📅 Future Scope |
| Natural language analytics query | NLU pipeline *(production)* | Not implemented in POC (ADR-007) | 2 | 📅 Future Scope |
| Query accuracy > 90% | NLU pipeline *(production)* | Not applicable — NLU is future scope | N/A | 📅 Future Scope |

---

## 6. Security & Implementation Quality (10%)

| Judge Criterion | What We Build | Demo Evidence | Score Target |
|----------------|---------------|---------------|-------------|
| No hardcoded API keys | `.env.example` + Secrets config | Code review: no literals in source | 5 |
| JWT + API key auth | `src/api/middleware/auth.py` | Unauthenticated request → 401 | 5 |
| RBAC + tier enforcement | Auth middleware + DB | Lower-tier user denied higher-tier feature | 5 |
| TLS in transit | docker-compose TLS config | HTTPS endpoint demo | 4 |
| Test coverage > 80% | `tests/unit` + `tests/integration` | pytest --cov report screenshot | 4 |
| CI/CD pipeline | `.github/workflows/ci.yml` | GitHub Actions green build | 4 |
| Input validation (XSS, injection) | Pydantic + middleware | Show rejected malformed request | 5 |

---

## Deliverable → Document Cross-Reference

| Deliverable | Document | Status |
|-------------|----------|--------|
| Problem Analysis | `01-Problem-Analysis.md` | ✅ |
| Use Cases | `03-Use-Cases.md` | ✅ |
| Test Cases | `04-Test-Cases.md` | ✅ |
| Traceability Matrix | `05-Traceability-Matrix.md` | ✅ |
| High Level Design | `06-HLD.md` | ✅ |
| Security Architecture | `10-Security-Architecture.md` | ✅ |
| ROI & Business Value | `12-ROI-Business-Value.md` | ✅ |
| Pre-Mortem | `13-Premortem.md` | ✅ |
| Architecture Review | `14-Architecture-Review.md` | ✅ |

---

## 🚨 Pre-Mortem Gap Fixes — Evaluation Impact Map
> Source: `13-Premortem.md` full revision.
> Each gap below identifies which judge criterion it damages and the concrete fix required.

---

### Category 1: Intelligent Routing & Failover (25% weight — at risk)

| Gap ID | Gap Description | Criterion Damaged | Fix Required | Owner |
|--------|----------------|-------------------|-------------|-------|
| G01-A | No sequence diagrams — data flow invisible to judges | NFR parsing, model selection, failover | Add Mermaid sequence diagrams to `06-HLD.md` for UC-01, UC-02, UC-03 | Architect |
| G01-B | Config UI has zero design | Routing rule configurability | Create `docs/architecture/config-ui-design.md`; define CRUD API routes | Frontend lead |
| G02-A | `src/gateway/` is empty placeholders | All routing criteria | Implement `nfr_parser.py`, `model_selector.py`, `failover.py` (P0) | Backend lead |
| G08-B | No load test results for failover latency | Failover latency < 500ms | Run Locust scenario simulating provider failure; save to `docs/evidence/` | DevOps |

**Remediated Score Projection:** 3.5 → **4.8** after fixes applied

---

### Category 2: Semantic Caching & Cost Optimization (20% weight — at risk)

| Gap ID | Gap Description | Criterion Damaged | Fix Required | Owner |
|--------|----------------|-------------------|-------------|-------|
| G02-A | `src/cache/` is empty | Cache hit rate, cost reduction | Implement `semantic_cache.py`, `embedding_service.py`, `cache_manager.py` | Backend lead |
| G01-D | Embedding service has no offline fallback | Cache hit rate during demo | Add `EMBEDDING_MODE=mock` env var with pre-computed local embeddings | Backend lead |
| G06-A | Cache hit rate assumed (40–60%), never measured | Cost reduction evidence | Run demo seed + measure real hit rate; update `12-ROI-Business-Value.md` | Data/Analytics |
| G06-C | Ada-002 embedding cost excluded from ROI | True cost saving overstated | Add embedding cost line item to ROI model | Architect |
| G07-C | No pre-seeded analytics data | Dashboard shows $0 / 0 requests | Create `demo/seed_demo_data.py` with 500+ synthetic requests + 20 cached prompts | Demo lead |

**Remediated Score Projection:** 2.5 → **4.7** after fixes applied

---

### Category 3: Performance & Scalability (20% weight — at risk)

| Gap ID | Gap Description | Criterion Damaged | Fix Required | Owner |
|--------|----------------|-------------------|-------------|-------|
| G01-E | No load balancer in Docker Compose | Throughput > 10K RPS claim unverifiable | Add Nginx reverse proxy to `docker-compose.yml`; enable gateway replicas | DevOps |
| G08-B | No Locust/k6 load test results | P95 latency and RPS evidence | Create `tests/load/locustfile.py`; run and save results | DevOps |
| G02-E | `docker-compose.yml` doesn’t exist | System cannot start | Create `docker-compose.yml` with all 7 services + health checks | DevOps |
| G01-C | No distributed tracing | Latency breakdown unverifiable | Add OpenTelemetry + trace_id to every response metadata | Backend lead |

**Remediated Score Projection:** 2.0 → **4.2** after fixes applied

---

### Category 4: Rate Limiting & Queue Management (15% weight — at risk)

| Gap ID | Gap Description | Criterion Damaged | Fix Required | Owner |
|--------|----------------|-------------------|-------------|-------|
| G02-A | `src/api/middleware/rate_limit.py` is a `pass` stub | Tier throttling, token bucket | Implement Redis INCR + TTL token bucket per tier | Backend lead |
| G05-B | Redis is SPOF — rate limiter fails if Redis crashes | Queue management reliability | Add graceful degradation: bypass queue if Redis unavailable; log warning | Backend lead |
| G03-B | No mock provider for integration tests | Queue behaviour cannot be tested in CI | Create `src/simulator/mock_provider.py` | Backend lead |
| G05-C | No graceful shutdown / drain | In-flight requests dropped on restart | Add `@app.on_event("shutdown")` with 30s queue drain | Backend lead |

**Remediated Score Projection:** 3.0 → **4.8** after fixes applied

---

### Category 5: Analytics & Conversational Interface (10% weight — at risk)

| Gap ID | Gap Description | Criterion Damaged | Fix Required | Owner |
|--------|----------------|-------------------|-------------|-------|
| G02-B | No frontend exists | Real-time dashboard criterion | Create `frontend/` with React + MUI scaffold; 4 metric widgets minimum | Frontend lead |
| G08-C | No Grafana dashboard pre-configured | Observability evidence | Create `monitoring/grafana/dashboards/llm-gateway.json` with 6 panels | DevOps |
| G07-C | Empty dashboard at demo time | Analytics NLU demo impossible | Run `demo/seed_demo_data.py` before demo; set Grafana time range to 7 days | Demo lead |
| G08-F | No Q&A prep for analytics questions | Judge Q&A response quality | Create `demo/qna_prep.md` with top 10 judge questions + scripted answers | Architect |

**Remediated Score Projection:** 2.5 → **4.3** after fixes applied

---

### Category 6: Security & Implementation Quality (10% weight — at risk)

| Gap ID | Gap Description | Criterion Damaged | Fix Required | Owner |
|--------|----------------|-------------------|-------------|-------|
| G03-A | Zero actual test files exist | Test coverage > 80% | Implement `tests/unit/test_nfr_parser.py`, `test_model_selector.py`, `test_failover.py` | Backend lead |
| G03-E | No CI/CD pipeline | CI/CD criterion | Create `.github/workflows/ci.yml` with lint + test + coverage + security scan | DevOps |
| G04-B | No brute force protection on `/auth/token` | Auth security | Add rate limiter (5 req/min) on auth endpoints | Backend lead |
| G04-C | No OWASP Top 10 checklist | Security thoroughness | Add OWASP checklist table to `10-Security-Architecture.md` | Architect |
| G04-D | CORS not configured | Dashboard breaks in browser | Add `CORSMiddleware` to `src/api/main.py` | Backend lead |
| G08-A | No pytest coverage report | Test coverage evidence | Run `pytest --cov=src --cov-report=html`; commit screenshot to `docs/evidence/` | Backend lead |
| G08-E | No CI badge on README | Implementation quality visibility | Add GitHub Actions badge to `README.md` after CI pipeline is green | DevOps |

**Remediated Score Projection:** 1.5 → **4.5** after fixes applied

---

### ROI & Business Value (Cross-Cutting)

| Gap ID | Gap Description | Fix Required |
|--------|----------------|-------------|
| G06-B | No competitor comparison (LiteLLM, OpenRouter, PortKey) | Add competitor table to `12-ROI-Business-Value.md` showing our differentiators |
| G06-D | No sensitivity analysis on ROI | Add pessimistic (20%), base (40%), optimistic (60%) cache hit rate scenarios |
| G05-A | 99.95% availability claim unsupported | Add availability calculation: MTTF/MTTR math to `12-ROI-Business-Value.md` |

---

### Demo Narrative (Cross-Cutting)

| Gap ID | Gap Description | Fix Required |
|--------|----------------|-------------|
| G07-A | No demo script | Create `demo/demo_script.md` with minute-by-minute 15-minute walkthrough |
| G07-B | No before/after business narrative | Open demo with problem + cost statement; close with live cost-saved counter |
| G07-D | No backup demo plan | Record `demo/backup_demo.mp4`; prepare static screenshot slide deck |

---

## Remediated Score Projection Summary

| Category | Weight | Pre-Fix Score | Post-Fix Score | Weighted Gain |
|----------|--------|--------------|----------------|---------------|
| Intelligent Routing & Failover | 25% | 3.5 | 4.8 | +0.325 |
| Semantic Caching & Cost Optimization | 20% | 2.5 | 4.7 | +0.440 |
| Performance & Scalability | 20% | 2.0 | 4.2 | +0.440 |
| Rate Limiting & Queue Management | 15% | 3.0 | 4.8 | +0.270 |
| Analytics & Conversational Interface | 10% | 2.5 | 3.5 | +0.100 |
| Security & Implementation Quality | 10% | 1.5 | 4.5 | +0.300 |
| **Weighted Total** | **100%** | **2.60** | **4.63** | **+2.03** |

> ✅ All gaps fixed → projected score **4.63 / 5.0** (Excellent, approaching Outstanding)
> ⚠️ Without fixes → projected score **2.60 / 5.0** (Needs Improvement — Technothon failed)

---

## Fix Execution Checklist

> Last verified: Demo run on Python 3.14 / Windows 11 — all 8 demo scenarios PASS

```
[DONE] [ P0 ] Create requirements.txt, docker-compose.yml, Dockerfile, .env.example
[DONE] [ P0 ] Implement src/gateway/nfr_parser.py
[DONE] [ P0 ] Implement src/gateway/model_selector.py
[DONE] [ P0 ] Implement src/gateway/failover.py (+ circuit breaker)
[DONE] [ P0 ] Implement src/providers/base.py + openai_provider.py + anthropic + google
[DONE] [ P0 ] Implement src/cache/semantic_cache.py (pure-Python cosine similarity, no Redis)
[DONE] [ P0 ] Implement src/api/middleware/rate_limit.py (in-memory token bucket)
[DONE] [ P0 ] Implement src/api/middleware/auth.py (+ brute-force lockout)
[DONE] [ P0 ] Wire src/api/main.py routes (fixed: emoji removed for Windows cp1252 compat)
[ N/A] [ P0 ] Create Alembic migrations -- NOT NEEDED: POC uses local JSON, no SQL DB
[DONE] [ P0 ] Write tests/unit/test_nfr_parser.py (TC-01) -- 18 tests
[DONE] [ P0 ] Write tests/unit/test_model_selector.py (TC-02) -- 16 tests
[DONE] [ P0 ] Write tests/unit/test_failover.py (TC-04) -- 17 tests
[DONE] [ P0 ] Create .github/workflows/ci.yml
[DONE] [ P0 ] Create demo/seed_demo_data.py (seeds 20 cache + 200 analytics records)
[DONE] [ P0 ] Create demo/demo_script.md
[DONE] [ P1 ] Add Mermaid sequence diagrams to 06-HLD.md (UC-01 to UC-04)
[ --- ] [ P1 ] Create frontend/ React scaffold -- OUT OF SCOPE for backend POC
[DONE] [ P1 ] Create monitoring/grafana/dashboards/llm-gateway.json
[ --- ] [ P1 ] Run Locust load test -- cannot execute without persistent server in CI
[ --- ] [ P1 ] Run pytest --cov -- run manually: py -m pytest tests/ --cov=src
[DONE] [ P1 ] Add CORS middleware to src/api/main.py
[DONE] [ P1 ] Add brute force protection on auth (10 failures -> 5min lockout)
[DONE] [ P1 ] Add OWASP checklist to 10-Security-Architecture.md
[DONE] [ P1 ] Add competitor comparison to 12-ROI-Business-Value.md
[DONE] [ P1 ] Add availability math to 12-ROI-Business-Value.md
[DONE] [ P1 ] Add sensitivity analysis to 12-ROI-Business-Value.md
[DONE] [ P1 ] Create demo/qna_prep.md
[DONE] [ P2 ] Add OpenTelemetry tracing design notes to 06-HLD.md
[ --- ] [ P2 ] Record demo/backup_demo.mp4 -- use demo/run_demo_v2.py instead
[DONE] [ P2 ] Add CI badge to README.md
```

## Verified Demo Results (Live Run)

| Scenario | Result | Evidence |
|----------|--------|----------|
| Health check | PASS | All 3 providers CLOSED, cache_size=20, 200 pre-seeded records |
| NFR routing low-cost | PASS | Cache HIT on "capital of France", latency=3ms, cost=$0.000000 |
| NFR routing critical accuracy | PASS | claude-3-sonnet selected via Anthropic |
| Semantic cache miss then hit | PASS | Call 1 MISS, Call 2 HIT, cost saved |
| Failover + circuit breaker | PASS | OpenAI OPEN -> routed to google/gemini-flash, failover confirmed |
| Analytics summary | PASS | 206 requests, **42.2% cache hit rate**, $0.22 total cost |
| Tier access control | PASS | Free tier with critical NFR -> gemini-flash (NOT gpt-4) |
| Auth invalid key | PASS | HTTP 401 returned correctly |

**Overall: 8/8 scenarios PASS**
