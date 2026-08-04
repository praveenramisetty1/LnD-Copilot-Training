# Setup Guide — LLM Gateway Platform

> Status: Draft | Version: 1.0

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Docker | 24+ | Container runtime |
| Docker Compose | 2.20+ | Local orchestration |
| Python | 3.11+ | Backend runtime |
| Node.js | 18+ | Frontend runtime |
| Git | 2.40+ | Version control |

---

## 1. Clone the Repository

```bash
git clone <repo-url>
cd llm-gateway
```

---

## 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and fill in your API keys and settings. At minimum:

```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
POSTGRES_PASSWORD=changeme
```

---

## 3. Start All Services

```bash
docker-compose up -d
```

This starts:
- FastAPI gateway on port `8000`
- PostgreSQL on port `5432`
- Redis on port `6379`
- Qdrant on port `6333`
- Grafana on port `3001`
- Prometheus on port `9090`

---

## 4. Verify Installation

```bash
curl http://localhost:8000/health
# Expected: {"status": "ok", "version": "1.0.0"}
```

---

## 5. Access Services

| Service | URL |
|---------|-----|
| API Gateway | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Analytics Dashboard | http://localhost:3000 |
| Grafana | http://localhost:3001 |
| Qdrant Dashboard | http://localhost:6333/dashboard |

---

## 6. Running Tests

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# All tests with coverage
pytest --cov=src tests/
```

---

_TODO: Add Kubernetes deployment guide, production hardening steps_
