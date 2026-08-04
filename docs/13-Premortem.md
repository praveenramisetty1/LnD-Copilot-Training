# 13 — Pre-Mortem Analysis (Full Revision)
**Propeller Technothon | Problem Statement 4: LLM Gateway**

> **Assumption:** The solution was submitted and *failed* Technothon evaluation.
> This document performs a forensic gap analysis across all 8 failure dimensions,
> identifies root causes, and prescribes concrete fixes before demo day.

---

## Executive Failure Summary

| Dimension | Failure Mode | Severity |
|-----------|-------------|----------|
| Architecture | Missing sequence diagrams; Config UI has no design | 🔴 High |
| Implementation Scope | Core src/ modules never created beyond placeholders | 🔴 Critical |
| Testability | Test cases defined but zero actual test files exist | 🔴 Critical |
| Security | No API key rotation, no OWASP checklist, no CORS config | 🟡 Medium |
| Reliability | 99.95% SLA claimed with no mathematical basis | 🟡 Medium |
| ROI | Cache hit rate assumed, never validated; no competitor comparison | 🟡 Medium |
| Demo Narrative | No demo script, no story arc, no pre-seeded data | 🔴 High |
| Judge Evidence | No pytest --cov report, no load test results, no Grafana dashboard | 🔴 Critical |

---

## GAP-01: Architecture Gaps

### G01-A: No Sequence Diagrams — Judges Cannot Follow Data Flow
**Root Cause:** HLD uses ASCII box diagrams only; no per-use-case sequence diagram exists.
**Judge Impact:** Routing & Failover category loses points — judges cannot verify the flow is correct.
**Fix:**
- Add Mermaid sequence diagrams to `06-HLD.md` for UC-01 (NFR routing), UC-02 (cache hit/miss), UC-03 (failover)
- Add to `03-Use-Cases.md` one sequence diagram per P0 use case

### G01-B: Configuration UI Has Zero Architecture Design
**Root Cause:** Config UI is marked P1 and never designed — no wireframes, no API routes, no component map.
**Judge Impact:** Routing rule configurability criterion scores 3/5 at best with no UI.
**Fix:**
- Add `docs/architecture/config-ui-design.md` with React component tree and API contract
- Define at minimum: routing rules CRUD endpoints in `src/api/routes/`

### G01-C: No Observability / Distributed Tracing Design
**Root Cause:** Prometheus + Grafana listed in tech stack but no tracing design (OpenTelemetry/Jaeger).
**Judge Impact:** Observability & Analytics category — no trace-level evidence for latency claims.
**Fix:**
- Add OpenTelemetry instrumentation plan to HLD Section 2
- Add trace_id to every request log entry and API response metadata

### G01-D: Embedding Service Has No Offline Fallback
**Root Cause:** Ada-002 is the sole embedding provider; if it is down, cache is completely bypassed.
**Judge Impact:** Demo risk: cache hit rate = 0% if OpenAI is unavailable during presentation.
**Fix:**
- Add `EMBEDDING_MODE=mock` env var switching to pre-computed local embeddings
- Document in `06-HLD.md` Section 2.3 and in `.env.example`

### G01-E: No Load Balancer in Front of Gateway
**Root Cause:** Docker Compose exposes gateway on port 8000 directly — no Nginx/Traefik proxy layer.
**Judge Impact:** Scalability claim is not demonstrable; single process is a SPOF.
**Fix:**
- Add Nginx as reverse proxy in `docker-compose.yml`
- Enables SSL termination and multiple gateway replicas behind one endpoint

---

## GAP-02: Implementation Scope Gaps

### G02-A: Core src/ Modules Are Empty Placeholders Only
**Root Cause:** `src/gateway/`, `src/providers/`, `src/cache/`, `src/analytics/`, `src/simulator/` all have README + `pass` stubs — no logic whatsoever.
**Judge Impact:** Every evaluation category fails — nothing runs, nothing can be demoed.
**Fix (Priority Order):**
1. `src/gateway/nfr_parser.py` — parse and validate X-NFR-* headers
2. `src/gateway/model_selector.py` — weighted scoring algorithm
3. `src/gateway/failover.py` — 4-level failover + circuit breaker
4. `src/providers/base.py` + `openai_provider.py` — working provider call
5. `src/cache/semantic_cache.py` — Redis L1 + Qdrant L2 lookup
6. `src/api/main.py` — wire all components into FastAPI routes

### G02-B: No Frontend Exists
**Root Cause:** React dashboard mentioned everywhere but no `frontend/` directory, no package.json, nothing.
**Judge Impact:** Analytics & Dashboard criterion cannot be scored — no visible UI.
**Fix:**
- Create `frontend/` with a minimal React + MUI scaffold
- At minimum: a dashboard page showing 4 real-time metrics (cost, latency, cache hit %, RPS)
- Use mock API data if TimescaleDB is not fully wired

### G02-C: No Demo Data Seeding Script
**Root Cause:** No script to pre-populate PostgreSQL, Redis, and Qdrant with demo-ready data.
**Judge Impact:** Analytics dashboard shows empty charts; cache hit rate = 0% at demo start.
**Fix:**
- Create `demo/seed_demo_data.py` — inserts 500+ synthetic request records + 20 pre-warmed cache entries
- Run automatically on `docker-compose up`

### G02-D: No Database Migration Tool
**Root Cause:** SQL schema is defined in `06-HLD.md` but no Alembic or migration scripts exist.

> ⚠️ **GAP-IMPL-02 Resolution — N/A for POC (ADR-010):**
> POC uses `data/analytics.json` as the analytics store — no SQL database is deployed in Path A (POC/Demo).
> Alembic migrations are a **production concern only (Path B)**. `docker-compose up` in Path B will require Alembic to be set up before go-live.
> **POC Judge Impact: None** — demo does not use PostgreSQL or TimescaleDB.

**Fix (Production Path B only):**
- Add `alembic/` directory with initial migration for all 5 core tables
- Add `alembic upgrade head` to Docker entrypoint
- POC (Path A): No action required — JSON file store requires no migrations (ADR-010)

### G02-E: No requirements.txt, docker-compose.yml, or Dockerfile
**Root Cause:** Root config files referenced throughout docs but never created.
**Judge Impact:** Project cannot be started — demo collapses immediately.
**Fix:**
- Create `requirements.txt` with all Python dependencies pinned
- Create `docker-compose.yml` with all 7 services
- Create `Dockerfile` for gateway service
- Create `.env.example` with all required variables

---

## GAP-03: Testability Gaps

### G03-A: Zero Actual Test Files Exist
**Root Cause:** `tests/unit/`, `tests/integration/`, `tests/e2e/` directories do not exist; test cases are spec-only.
**Judge Impact:** Test coverage = 0% — Security & Quality criterion scores 1/5.
**Fix (Priority Order):**
1. `tests/unit/test_nfr_parser.py` — 5 test cases (TC-01)
2. `tests/unit/test_model_selector.py` — 5 test cases (TC-02)
3. `tests/unit/test_failover.py` — circuit breaker state machine tests
4. `tests/integration/test_semantic_cache.py` — requires Qdrant + Redis
5. `tests/integration/test_rate_limiter.py` — requires Redis

### G03-B: No Mock Provider Infrastructure
**Root Cause:** Integration tests require real provider calls or a mock — neither exists.
**Judge Impact:** Integration tests cannot run in CI without live API keys or mocks.
**Fix:**
- Create `src/simulator/mock_provider.py` returning deterministic fake responses
- Use `pytest-mock` or `respx` to intercept HTTP calls to providers in tests

### G03-C: No Load Test Scripts
**Root Cause:** Locust/k6 mentioned in test strategy but no scripts created.
**Judge Impact:** P95 latency and RPS claims are unverifiable — Performance category loses 1.5 points.
**Fix:**
- Create `tests/load/locustfile.py` with 3 scenarios: cached, uncached, mixed
- Run load test against local Docker Compose and save results to `tests/load/results/`

### G03-D: TC-03-05 TTL Expiry Untestable Without Time Mocking
**Root Cause:** 7-day TTL cannot be waited for in a test run.
**Judge Impact:** TTL behaviour is unverifiable → cache correctness questioned.
**Fix:**
- Use `freezegun` library to mock time in TTL expiry tests
- Add `CACHE_TTL_SECONDS` env var for tests (set to 1 second in test config)

### G03-E: No CI/CD Pipeline Configured
**Root Cause:** `.github/workflows/ci.yml` referenced but never created.
**Judge Impact:** No GitHub Actions green badge — CI/CD criterion scores 2/5.
**Fix:**
- Create `.github/workflows/ci.yml` running lint + unit tests + coverage check
- Add coverage badge to `README.md`

---

## GAP-04: Security Gaps

### G04-A: No API Key Rotation Mechanism
**Root Cause:** Security architecture defines hashed key storage but no rotation workflow.
**Judge Impact:** Enterprise-readiness questioned during Q&A.
**Fix:**
- Add `POST /v1/admin/rotate-key` endpoint
- Document rotation procedure in `10-Security-Architecture.md`

### G04-B: No Brute Force Protection on Auth Endpoint
**Root Cause:** `/auth/token` has no rate limit — unlimited password attempts possible.
**Judge Impact:** Basic security gap a judge will spot immediately.
**Fix:**
- Add separate rate limiter (5 attempts/minute) on auth endpoints
- Lock account after 10 failed attempts; log to audit trail

### G04-C: No OWASP Top 10 Checklist
**Root Cause:** Security doc covers specific controls but no structured OWASP review.
**Judge Impact:** Security thoroughness questioned — no evidence of systematic approach.
**Fix:**
- Add OWASP Top 10 checklist table to `10-Security-Architecture.md` with status per item

### G04-D: CORS Configuration Not Specified
**Root Cause:** Dashboard at port 3000 calls API at port 8000 — CORS required but not configured.
**Judge Impact:** Dashboard will fail in browser with CORS error — demo breaks.
**Fix:**
- Add explicit `CORSMiddleware` in `src/api/main.py` with allowlist `["http://localhost:3000"]`

---

## GAP-05: Reliability Gaps

### G05-A: 99.95% Availability Claim Has No Mathematical Basis
**Root Cause:** Claimed in ROI doc without showing failure rate calculation or SLA math.
**Judge Impact:** Reliability claim dismissed as marketing during Q&A.
**Fix:**
- Add availability calculation to `12-ROI-Business-Value.md`:
  - Formula: `Availability = 1 - (MTTR / (MTTF + MTTR))`
  - Show: single-provider 99.5% → with 4-provider failover → 99.95% derived

### G05-B: Redis Is a Single Point of Failure in POC
**Root Cause:** Docker Compose runs a single Redis node — cache, queue, and rate limiter all depend on it.
**Judge Impact:** One Redis crash = total gateway failure during demo.
**Fix:**
- Add Redis health check with graceful degradation: if Redis down, bypass cache/queue and route directly
- Document Redis Sentinel as production HA strategy in `06-HLD.md`

### G05-C: No Graceful Shutdown / Drain Logic
**Root Cause:** FastAPI app has no shutdown handler — in-flight requests dropped on restart.
**Judge Impact:** Reliability score impacted — no evidence of production-grade lifecycle management.
**Fix:**
- Add `@app.on_event("shutdown")` handler that drains queue before exit
- Add `SIGTERM` handler with 30-second graceful shutdown window

---

## GAP-06: ROI Gaps

### G06-A: Cache Hit Rate Is Assumed, Not Validated
**Root Cause:** 40–60% cache hit rate cited everywhere but based on no data.
**Judge Impact:** ROI numbers are fiction — business owner judge will ask for the data.
**Fix:**
- Run demo seed script (500+ requests, 30% similar prompts) and measure actual hit rate
- Report real measured number in `12-ROI-Business-Value.md` Section 2

### G06-B: No Competitor Comparison
**Root Cause:** ROI doc compares against "no gateway" baseline only; ignores LiteLLM, OpenRouter, PortKey.
**Judge Impact:** Judge asks "Why not just use LiteLLM?" — no prepared answer.
**Fix:**
- Add competitor comparison table to `12-ROI-Business-Value.md`:

| Feature | Our Gateway | LiteLLM | OpenRouter | PortKey |
|---------|------------|---------|------------|--------|
| NFR-based routing | ✅ | ❌ | ❌ | ❌ |
| Semantic caching | ✅ | Partial | ❌ | ✅ |
| Priority queue | ✅ | ❌ | ❌ | ❌ |
| Self-hosted | ✅ | ✅ | ❌ | Partial |
| Analytics NLU chat | ✅ | ❌ | ❌ | ❌ |

### G06-C: Embedding Costs Not Included in ROI
**Root Cause:** Ada-002 embedding calls cost money and are called on every cache miss — not accounted for.
**Judge Impact:** True cost savings are overstated.
**Fix:**
- Add embedding cost line to ROI model: `~$0.0001 per 1K tokens × average prompt size`
- Recalculate net saving after embedding overhead

### G06-D: No Sensitivity Analysis
**Root Cause:** ROI shows only conservative (40%) and target (60%) hit rates — no worst-case.
**Fix:**
- Add 3-scenario table: Pessimistic (20%), Base (40%), Optimistic (60%) cache hit rates
- Show break-even point for each scenario

---

## GAP-07: Demo Narrative Gaps

### G07-A: No Demo Script Exists
**Root Cause:** `demo/` folder was listed in the repo structure request but never created.
**Judge Impact:** Team improvises during demo → misses criteria → judges cannot follow story.
**Fix:**
- Create `demo/demo_script.md` with minute-by-minute walkthrough:
  - Minute 0–2: Problem statement and business case
  - Minute 2–5: Live NFR routing demo (3 requests, 3 different models selected)
  - Minute 5–8: Semantic cache demo (miss then hit, cost comparison on screen)
  - Minute 8–11: Failover demo (kill provider, watch automatic recovery)
  - Minute 11–13: Analytics dashboard + 1 NLU query
  - Minute 13–15: Architecture walkthrough + Q&A setup

### G07-B: No "Before/After" Business Narrative
**Root Cause:** Demo jumps straight to features without establishing the problem.
**Judge Impact:** Business value criterion misses — judges don't understand WHY it matters.
**Fix:**
- Open demo with: *"Without this gateway, your team spends $30K/month on LLM APIs and has no failover. Here is what happens in the next 15 minutes..."*
- Close with cost-saved counter on the dashboard showing real savings from the demo run

### G07-C: No Pre-Seeded Analytics Data
**Root Cause:** No seed script → dashboard shows 0 requests, $0.00 cost at demo time.
**Judge Impact:** Analytics category cannot be scored — empty charts.
**Fix:**
- `demo/seed_demo_data.py` inserts 7 days of synthetic request history before demo
- Grafana dashboard pre-configured with time range set to "Last 7 days"

### G07-D: No Backup Demo Plan
**Root Cause:** RISK-02 mentions a backup video but it was never created or scripted.
**Fix:**
- Record a full 15-minute demo video to `demo/backup_demo.mp4` before presentation day
- Prepare static screenshots of every key metric as fallback slides

---

## GAP-08: Judge Evidence Gaps

### G08-A: No pytest Coverage Report
**Root Cause:** No tests exist → coverage report cannot be generated.
**Judge Impact:** Security & Quality score = 1/5 without evidence.
**Fix:**
- After implementing unit tests, run: `pytest --cov=src --cov-report=html tests/`
- Commit `htmlcov/` or screenshot to `docs/evidence/coverage-report.png`

### G08-B: No Load Test Results
**Root Cause:** Locust/k6 scripts never created.
**Judge Impact:** P95 latency and RPS claims are unverifiable — Performance loses 1.5 points.
**Fix:**
- Run Locust load test against local stack
- Save results to `docs/evidence/load-test-results.png` and `tests/load/results/`

### G08-C: No Grafana Dashboard Pre-Configured
**Root Cause:** Grafana is in docker-compose (not yet created) but no dashboard JSON provisioned.
**Judge Impact:** "Analytics dashboard" shown as empty Grafana default screen.
**Fix:**
- Create `monitoring/grafana/dashboards/llm-gateway.json` with pre-built panels:
  - RPS, P95 latency, cache hit rate, cost/hour, error rate, provider distribution
- Mount via `grafana.ini` provisioning config

### G08-D: No Architecture Diagram as Image
**Root Cause:** All diagrams are ASCII art — not professional or exportable.
**Judge Impact:** Architecture presentation is weak visually.
**Fix:**
- Convert HLD ASCII diagram to proper Mermaid diagram in `06-HLD.md`
- Export as PNG to `docs/architecture/hld-diagram.png` for presentation slides

### G08-E: No CI/CD Badge on README
**Root Cause:** CI pipeline not created → no badge possible.
**Judge Impact:** Implementation quality sub-criterion loses points.
**Fix:**
- After creating `.github/workflows/ci.yml`, add badge to `README.md`:
  ```md
  ![CI](https://github.com/{org}/{repo}/actions/workflows/ci.yml/badge.svg)
  ```

### G08-F: No Competitor Differentiation Statement for Q&A
**Root Cause:** No prepared answer to "Why not use LiteLLM/OpenRouter instead?"
**Fix:**
- Add `demo/qna_prep.md` with top 10 anticipated judge questions and scripted answers

---

## Fix Priority Matrix

| Fix | Dimension | Effort | Impact | Do First? |
|-----|-----------|--------|--------|----------|
| Create requirements.txt + docker-compose.yml + Dockerfile | Scope | Low | Critical | ✅ Yes |
| Implement src/gateway/ core modules | Scope | High | Critical | ✅ Yes |
| Implement src/providers/openai_provider.py | Scope | Medium | Critical | ✅ Yes |
| Implement src/cache/semantic_cache.py | Scope | High | Critical | ✅ Yes |
| Create tests/unit/ test files (TC-01, TC-02) | Testability | Medium | High | ✅ Yes |
| Create demo/seed_demo_data.py | Demo | Low | High | ✅ Yes |
| Create demo/demo_script.md | Demo | Low | High | ✅ Yes |
| Add Mermaid sequence diagrams to 06-HLD.md | Architecture | Low | High | ✅ Yes |
| Create .github/workflows/ci.yml | Testability | Low | Medium | ✅ Yes |
| Run load test + save results | Evidence | Medium | High | ✅ Yes |
| Add OWASP checklist to 10-Security-Architecture.md | Security | Low | Medium | ⚠️ Soon |
| Add competitor comparison to 12-ROI-Business-Value.md | ROI | Low | Medium | ⚠️ Soon |
| Add availability math to 12-ROI-Business-Value.md | Reliability | Low | Medium | ⚠️ Soon |
| Create Grafana dashboard JSON | Evidence | Medium | Medium | ⚠️ Soon |
| Create demo/qna_prep.md | Demo | Low | Medium | ⚠️ Soon |
| Record backup demo video | Demo | High | Medium | 📅 Later |
| Add OpenTelemetry tracing design | Architecture | Medium | Low | 📅 Later |

---

## Original Risk Register (Retained)

### RISK-01: Qdrant Vector Search Returns False Positives
**Scenario:** Similarity threshold set too low → semantically different prompts return wrong cached response  
**Impact:** Incorrect LLM answers served to users — undermines trust in the gateway  
**Mitigation:**
- Default threshold = 0.95 (conservative)
- Make threshold configurable via admin UI
- Add "cache correctness" test suite (TC-03-04)
- Monitor cache hit rate vs. user complaint rate in analytics

---

### RISK-02: Demo Environment Instability
**Scenario:** Docker Compose services fail during live Technothon demo  
**Impact:** Judge cannot see working system → catastrophic score loss  
**Mitigation:**
- Maintain a pre-recorded demo video as fallback
- Use `docker-compose health checks` on all services
- Run full demo dry-run 24h before presentation
- Keep a pre-seeded demo dataset (cached responses loaded on startup)
- Dedicated `demo/` folder with one-command demo reset script

---

### RISK-03: OpenAI Embedding API Unavailable During Demo
**Scenario:** OpenAI Ada-002 embedding calls fail → semantic cache non-functional  
**Impact:** Cache hit rate = 0%; cost savings cannot be demonstrated  
**Mitigation:**
- `src/simulator/` includes a local embedding mock (pre-computed vectors)
- Simulator mode activated via `EMBEDDING_MODE=mock` env var
- Pre-warm cache before demo so embeddings already stored in Qdrant

---

### RISK-04: NFR Scoring Produces Unexpected Model Selection
**Scenario:** Weighted algorithm selects a model that judge perceives as wrong choice  
**Impact:** Judge questions routing logic credibility  
**Mitigation:**
- Document scoring matrix explicitly in `02-Architect-Thinking-Framework.md`
- Add `metadata.nfr_score_breakdown` to API response showing per-dimension scores
- Prepare verbal explanation: *"For low cost + standard accuracy, GPT-3.5-Turbo scores 87/100 vs GPT-4's 42/100"*

---

### RISK-05: Test Coverage Below 80% at Submission
**Scenario:** Time pressure causes test writing to be deprioritised  
**Impact:** Security & Quality category score drops significantly  
**Mitigation:**
- Write unit tests alongside each module (not after)
- CI pipeline fails if coverage drops below 80%
- Prioritise testing: nfr_parser → model_selector → failover → cache → auth

---

## 2. Medium Risks

### RISK-06: Redis Becomes a Single Point of Failure
**Scenario:** Redis crashes → rate limiter, queue, and L1 cache all fail simultaneously  
**Impact:** Gateway degrades but doesn't fully fail (falls back to provider directly)  
**Mitigation:**
- Graceful degradation: if Redis unavailable, bypass cache/queue and route directly
- Log Redis connectivity errors prominently
- Note Redis Sentinel as production recommendation in HLD

---

### RISK-07: Failover Latency Exceeds 500ms Target
**Scenario:** Timeout detection + retry logic takes longer than expected  
**Impact:** Performance & Scalability score impacted  
**Mitigation:**
- Set provider timeout = 200ms (aggressive for demo)
- Use async concurrent retries where possible
- Measure and document actual failover latency in test results

---

### RISK-08: NLU Query Misclassification
**Scenario:** Conversational analytics returns wrong data for ambiguous queries  
**Impact:** Analytics & Conversational Interface score reduced  
**Mitigation:**
- Prepare 5 rehearsed demo queries with known-correct answers
- Add confidence threshold — below 0.7, ask clarifying question
- Fallback: show structured query UI alongside chat interface

---

### RISK-09: Scope Creep Delays Core Features
**Scenario:** Team spends time on config UI or analytics polish instead of core routing/cache  
**Impact:** P0 features incomplete → catastrophic scoring across multiple categories  
**Mitigation:**
- Strict priority order: P0 first (routing, cache, failover, queue), then P1
- Weekly scope check against `00-Evaluation-Mapping.md`
- Config UI is P1 — placeholder acceptable if routing works perfectly

---

## 3. Low Risks (Noted for Awareness)

| Risk | Mitigation |
|------|-----------|
| Provider API schema changes break integration | Adapter pattern + integration test per provider |
| Embedding model change invalidates cached vectors | Version embeddings in metadata; re-index on model change |
| TimescaleDB query performance slow on large dataset | Use pre-aggregated materialized views for dashboard |
| React dashboard slow to load | Lazy loading + pagination on analytics tables |

---

## 4. Risk Register Summary

| Risk | Likelihood | Impact | Priority | Owner |
|------|-----------|--------|----------|-------|
| RISK-01: Cache false positives | Medium | High | P0 | Cache module owner |
| RISK-02: Demo instability | Medium | Critical | P0 | DevOps / Demo lead |
| RISK-03: Embedding API down | Low | High | P1 | Cache module owner |
| RISK-04: Unexpected model selection | Low | Medium | P1 | Gateway/router owner |
| RISK-05: Test coverage < 80% | Medium | High | P0 | All engineers |
| RISK-06: Redis SPOF | Low | Medium | P2 | DevOps |
| RISK-07: Failover > 500ms | Low | Medium | P1 | Gateway owner |
| RISK-08: NLU misclassification | Medium | Medium | P1 | Analytics owner |
| RISK-09: Scope creep | Medium | High | P0 | Tech Lead |
