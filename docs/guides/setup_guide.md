# Setup Guide — LLM Gateway Platform

> Status: Updated | Version: 1.1

---

> ## ⚠️ Two Setup Paths
>
> | Path | When to Use | Docker Required? |
> |------|------------|------------------|
> | **Path A — POC / Demo** | Running the demo, evaluation, quick start | ❌ No |
> | **Path B — Full Stack** | Production-like setup with all services | ✅ Yes |
>
> **For evaluation and demo purposes, use Path A.** Path B describes the production target architecture (ADR-002, ADR-010).

---

## PATH A — POC / Demo Setup (No Docker Required)

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Backend runtime |
| Git | 2.40+ | Version control |

---

### Windows Setup (ADR-005, ADR-006)

```powershell
# 1. Confirm the Python Launcher is available (use py, not python)
py --version

# 2. Install dependencies via the py launcher
py -m pip install --prefer-binary -r requirements.txt

# 3. Set PYTHONPATH before running
$env:PYTHONPATH = "."

# 4. Start the server
py -m uvicorn src.api.main:app --reload
```

> **Note:** All emoji characters have been removed from source files to prevent Windows cp1252 encoding errors (ADR-005).

---

### A.1. Clone the Repository

```bash
git clone <repo-url>
cd llm-gateway
```

---

### A.2. Configure Environment

```bash
cp .env.example .env
```

For POC demo, providers are simulated (ADR-004) — real API keys are not required:

```env
OPENAI_API_KEY=sk-demo
ANTHROPIC_API_KEY=sk-ant-demo
GOOGLE_API_KEY=demo
CACHE_SIMILARITY_THRESHOLD=0.75
SIMULATE_PROVIDERS=true
```

---

### A.3. Install Dependencies

```bash
# Linux / macOS
pip install -r requirements.txt

# Windows
py -m pip install --prefer-binary -r requirements.txt
```

---

### A.4. Seed Demo Data

```bash
python demo/seed_demo_data.py
```

Seeds `data/analytics.json` with realistic request history for meaningful dashboard metrics.

---

### A.5. Start the Gateway

```bash
# Linux / macOS
uvicorn src.api.main:app --reload --port 8000

# Windows
py -m uvicorn src.api.main:app --reload --port 8000
```

---

### A.6. Verify Installation

```bash
curl http://localhost:8000/health
# Expected: {"status": "ok", "version": "1.0.0"}
```

---

### A.7. Access Services (POC)

| Service | URL |
|---------|-----|
| API Gateway | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |

> ⚠️ **POC Note:** The React Analytics Dashboard (port 3000) and Grafana (port 3001) are **not available in Path A** — they are part of the full production stack (Path B). Analytics data is accessible via `GET /v1/analytics/summary`.

---

### A.8. Run the Demo Script

```bash
python demo/run_demo_v2.py
```

Expected output: **8/8 scenarios PASS**. See `demo/demo_script.md` for the 15-minute live walkthrough and `demo/qna_prep.md` for judge Q&A preparation.

---

### A.9. Running Tests

```bash
# Linux / macOS
pytest tests/unit/
pytest tests/integration/
pytest --cov=src tests/

# Windows
py -m pytest --cov=src tests/
```

---

## PATH B — Full Stack Setup (Docker Required)

> This path reflects the **production target architecture** (ADR-002, ADR-010). Not required for POC evaluation.

### Prerequisites

| Tool | Version | Purpose |
|------|---------|------|
| Docker | 24+ | Container runtime |
| Docker Compose | 2.20+ | Local orchestration |
| Python | 3.11+ | Backend runtime |
| Node.js | 18+ | Frontend runtime |
| Git | 2.40+ | Version control |

### B.1. Clone & Configure

```bash
git clone <repo-url>
cd llm-gateway
cp .env.example .env
# Edit .env with real API keys and POSTGRES_PASSWORD
```

### B.2. Start All Services

```bash
docker-compose up -d
```

Starts: FastAPI (8000), PostgreSQL (5432), Redis (6379), Qdrant (6333), Grafana (3001), Prometheus (9090).

### B.3. Access Services (Full Stack)

| Service | URL |
|---------|-----|
| API Gateway | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| Analytics Dashboard | http://localhost:3000 |
| Grafana | http://localhost:3001 |
| Qdrant Dashboard | http://localhost:6333/dashboard |

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| `pip` not recognised | Python not in PATH | Use `py -m pip` on Windows (ADR-006) |
| `UnicodeEncodeError: cp1252` | Non-ASCII characters in source | All emojis removed (ADR-005); check `.env` for non-ASCII values |
| `httpx` deprecation warning | httpx version mismatch | Pin `httpx==0.24.1` in `requirements.txt` |
| `TestClient` returns 500 | PYTHONPATH not set | `export PYTHONPATH=.` (Linux) or `$env:PYTHONPATH="."` (Windows) |
| Cache hit rate 0% | Threshold too high | Ensure `CACHE_SIMILARITY_THRESHOLD=0.75` in `.env` (ADR-003) |
| Port 8000 already in use | Another process running | Add `--port 8001` to uvicorn command |
| Module not found | Missing install step | Re-run `pip install -r requirements.txt` |
| Demo seed fails | Missing `data/` directory | Run `mkdir data` then retry `python demo/seed_demo_data.py` |

---

---

## Kubernetes Deployment Guide

> 📅 **Future Scope — Production Path only.** The POC runs on a single machine (Path A). Kubernetes is the production scaling target.

### Helm Chart Structure (Designed)

```
helm/llm-gateway/
├── Chart.yaml
├── values.yaml
├── templates/
│   ├── deployment.yaml       ← gateway replicas
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── hpa.yaml              ← horizontal pod autoscaler
│   ├── configmap.yaml
│   └── secret.yaml
```

### Key Kubernetes Settings (Designed)

```yaml
# values.yaml (production target)
replicaCount: 3
resources:
  requests: { cpu: 500m, memory: 512Mi }
  limits:   { cpu: 2000m, memory: 2Gi }
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
  targetCPUUtilizationPercentage: 70
```

---

## Production Hardening Checklist

> These steps apply to **Path B (Full Stack)** production deployments only.

| Step | Action | Status |
|------|--------|--------|
| Secrets management | Move API keys from `.env` to HashiCorp Vault or AWS Secrets Manager | 📅 Future |
| TLS termination | Configure TLS at ingress (cert-manager + Let's Encrypt) | 📅 Future |
| Database hardening | Enable PostgreSQL SSL, restrict pg_hba.conf, rotate passwords | 📅 Future |
| Rate limit persistence | Replace in-memory token bucket with Redis INCR + TTL (ADR-002) | 📅 Future |
| Cache persistence | Replace pure-Python cache with Qdrant + Ada-002 (ADR-003) | 📅 Future |
| Analytics migration | Migrate `data/analytics.json` to TimescaleDB (ADR-010) | 📅 Future |
| JWT auth | Enable JWT for Admin UI (GAP-IMPL-03) | 📅 Future |
| Alembic migrations | Run `alembic upgrade head` on first deploy (GAP-IMPL-02) | 📅 Future |
| Monitoring | Import Grafana dashboard, configure Prometheus alerts | 📅 Future |
| Load testing | Validate 10,000 RPS target with Locust before go-live (NFR-08) | 📅 Future |
