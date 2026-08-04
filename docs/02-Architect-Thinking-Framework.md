# 02 — Architect Thinking Framework
**Propeller Technothon | Problem Statement 4: LLM Gateway**

---

## 1. Architectural Philosophy

The LLM Gateway is designed around five guiding principles:

| Principle | Application |
|-----------|------------|
| **Separation of Concerns** | API layer, routing engine, cache, providers, and analytics are fully decoupled modules |
| **Fail Fast, Recover Smart** | Circuit breakers open immediately on failure; multi-level failover ensures recovery |
| **Cost as a First-Class NFR** | Cost optimization (caching, model scoring) is a core feature, not an afterthought |
| **Observable by Default** | Every request emits structured metrics, traces, and logs |
| **Configuration Over Code** | Routing rules, model priorities, and tier limits are config-driven, not hardcoded |

---

## 2. The 10 Architect Roles — Applied to LLM Gateway

| Role | How We Address It |
|------|------------------|
| **1. AI Platform Strategist** | Multi-provider strategy, NFR-driven routing, cost visibility, roadmap (A/B testing, fine-tuning) |
| **2. Intelligent Routing Architect** | Weighted scoring algorithm (Cost 40%, Latency 30%, Accuracy 30%), 4-level failover |
| **3. Performance Optimization Architect** | Semantic caching (L1 Redis + L2 Qdrant), async FastAPI, embedding reuse |
| **4. Scalability & Resilience Architect** | Stateless gateway, horizontal scaling, circuit breaker, priority queue |
| **5. Data Architect for AI Systems** | Vector DB schema, TimescaleDB time-series, PostgreSQL relational model |
| **6. Integration Architect** | Provider abstraction layer, unified API surface, OpenAI-compatible interface |
| **7. Security & Compliance Architect** | API key + JWT auth, RBAC, TLS, secrets management, input validation |
| **8. Analytics & Observability Architect** | Real-time dashboard, NLU query interface, Prometheus + Grafana |
| **9. UX Architect** | Configuration UI, developer-friendly API (OpenAI-compatible), clear error messages |
| **10. Technical Leader & Communicator** | ADRs, structured documentation, clear demo narrative, team alignment |

---

## 3. Key Architectural Decisions

### ADR-001: Python FastAPI over Node.js / Go
- **Why:** Native async support, automatic OpenAPI docs for demo, rich AI/ML ecosystem
- **Trade-off:** Slightly lower raw throughput than Go — acceptable for POC scale

### ADR-002: Qdrant over Pinecone for Vector DB
- **Why:** Open-source, runs in Docker, no cloud account needed for demo
- **Trade-off:** Pinecone has better managed scaling — noted as production upgrade path

### ADR-003: Redis Dual-Purpose (Cache L1 + Queue)
- **Why:** Reduces infrastructure complexity for POC; Redis supports both hot cache and sorted-set priority queue
- **Trade-off:** For production, Kafka would replace Redis Queue for durability

### ADR-004: OpenAI-Compatible API Surface
- **Why:** Clients migrating from direct OpenAI can onboard with zero code changes
- **Trade-off:** Slight abstraction overhead in request translation

### ADR-005: TimescaleDB over InfluxDB
- **Why:** Reuses existing PostgreSQL engine, no second time-series DB to operate
- **Trade-off:** InfluxDB has better native time-series query performance at scale

---

## 4. Quality Attribute Scenarios

| Quality Attribute | Scenario | Response Measure |
|------------------|----------|-----------------|
| **Performance** | 10,000 concurrent requests hit gateway | P95 cached < 500ms, P95 uncached < 2s |
| **Availability** | OpenAI goes down during peak traffic | Failover to Azure OpenAI within 300ms, 0 user-visible errors |
| **Cost Efficiency** | Same question asked 1,000 times | 95%+ served from cache; ~$0 provider cost |
| **Security** | Unauthenticated request to /v1/chat/completions | HTTP 401, request rejected before routing |
| **Modifiability** | Add a new LLM provider | Implement `BaseProvider`, register in config — no core changes |
| **Observability** | Spike in error rate at 2am | Grafana alert fires within 60s; on-call notified |

---

## 5. Trade-off Analysis

### Semantic Cache Threshold (0.95)
| Threshold | Cache Hit Rate | Risk of Wrong Answer |
|-----------|---------------|---------------------|
| 0.80 | Very High | High (semantically different prompts matched) |
| 0.90 | High | Medium |
| **0.95** | **Balanced** | **Low — our choice** |
| 0.99 | Low | Near zero |

### Model Selection: Explicit Preference vs. NFR Scoring
- **Explicit Preference (`X-Model-Preference`):** Client knows best model → respect it
- **NFR Scoring:** Client expresses needs → gateway decides → more flexible, better cost control
- **Our approach:** NFR scoring is primary; explicit preference is a hint that boosts score, not a hard override

---

## 6. Architectural Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Qdrant cold start slows first embedding lookup | Medium | Medium | Pre-warm cache on startup with common prompts |
| Redis becomes single point of failure | Low | High | Redis Sentinel / Cluster in production |
| Provider API schema changes break integration | Medium | High | Adapter pattern + integration tests per provider |
| Embedding model changes invalidate cached vectors | Low | High | Version embeddings; re-index on model change |
| NLU misinterprets analytics query | Medium | Medium | Confidence threshold; fallback to structured query UI |

---

## 7. Architecture Evolution Path

```
Phase 1 (POC/Technothon)
  → Single-node Docker Compose
  → OpenAI + Anthropic + Google + Azure providers
  → Redis + Qdrant + PostgreSQL

Phase 2 (Production MVP)
  → Kubernetes (EKS/GKE) with horizontal pod autoscaling
  → Kafka replaces Redis Queue for durability
  → Pinecone replaces Qdrant for managed vector scaling

Phase 3 (Enterprise)
  → Multi-region active-active
  → A/B testing framework
  → Fine-tuned model routing
  → Budget alerts and FinOps dashboard
```
