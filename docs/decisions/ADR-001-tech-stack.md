# ADR-001: Tech Stack Selection

**Status**: Accepted  
**Date**: 2026-02-04  
**Deciders**: Architecture Team

---

## Context
We need to select a technology stack for the LLM Gateway Platform that balances developer productivity, performance, ecosystem maturity, and alignment with the Technothon evaluation criteria.

## Decision

| Layer | Selected | Alternatives Considered | Reason |
|-------|----------|------------------------|--------|
| API Framework | Python FastAPI | Node.js Express, Go Fiber | Async-native, automatic OpenAPI docs, strong AI ecosystem |
| Queue & Rate Limiter | **POC:** In-memory token bucket + heapq | RabbitMQ, Kafka, Redis+RQ | ADR-002: removed Redis dependency for POC portability; Production uses Redis + RQ |
| Vector DB | Qdrant | Pinecone, Milvus, Weaviate | Open-source, Docker-friendly, strong Python SDK |
| Relational DB | PostgreSQL 15 | MySQL, SQLite | JSONB support, TimescaleDB extension, industry standard |
| Time-Series | TimescaleDB | InfluxDB, Prometheus TSDB | PostgreSQL-native, no extra DB engine needed |
| Frontend | React 18 + MUI | Vue 3, Angular | Widest ecosystem, MUI for rapid UI development |
| Monitoring | Prometheus + Grafana | DataDog, New Relic | Open-source, Docker-friendly, cost-free |
| Container | Docker Compose | Kubernetes (local) | Simpler local dev; K8s noted as production target |

## Consequences
- Python FastAPI gives us async performance + built-in Swagger UI for demos
- Qdrant runs locally in Docker, avoiding cloud vector DB costs during POC
- TimescaleDB reduces infrastructure by reusing PostgreSQL for time-series data
- **POC (ADR-002):** In-memory token bucket for rate limiting and in-process priority queue — no Redis dependency required for demo execution
- **Production:** Redis serves dual purpose: L1 cache metadata + request queue (Redis Sorted Set + RQ workers)

---
