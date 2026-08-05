# Skill: DevOps

## Identity
- **Skill ID**: `devops-skill`
- **Domain**: Docker / Kubernetes / GitHub Actions / Monitoring
- **Used By**: Implementation Agent, Architecture Review Agent, Documentation Agent

---

## Purpose

Provides complete knowledge of the LLM Gateway infrastructure, CI/CD pipeline,
container strategy, and observability stack so agents can generate correct
DevOps artefacts aligned with the Technothon evaluation rubrics.

---

## CI/CD Pipeline (`.github/workflows/ci.yml`)

### Pipeline Stages

```
push / pull_request → main
        │
        ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    Lint     │────▶│    Test     │────▶│  Coverage   │────▶│  Security   │
│  (flake8,  │     │  (pytest    │     │  (≥ 80%)    │     │  (bandit)   │
│  black)    │     │   unit +    │     │             │     │             │
└─────────────┘     │ integration)│     └─────────────┘     └─────────────┘
                    └─────────────┘
```

### CI Job Definitions

```yaml
# .github/workflows/ci.yml (reference schema)
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  PYTHONPATH: .
  CACHE_SIMILARITY_THRESHOLD: "0.75"

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install flake8 black
      - run: black --check src/ tests/
      - run: flake8 src/ tests/ --max-line-length=100

  test:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements.txt --prefer-binary
      - run: pytest tests/unit/ tests/integration/ -v
              --cov=src --cov-report=xml --cov-fail-under=80

  security:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      - run: pip install bandit
      - run: bandit -r src/ -ll -x tests/
```

### CI Rules Agents Must Enforce
- No secrets or API keys in workflow files — use `${{ secrets.* }}`
- `PYTHONPATH: .` must be set in CI env for correct imports
- Coverage threshold `--cov-fail-under=80` must never be lowered without approval
- Security scan (`bandit`) must exit 0 before merge to main

---

## Docker

### `Dockerfile` (Backend)

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --prefer-binary

# Copy application source
COPY src/ ./src/
COPY .env.example .env

# Non-root user (security requirement)
RUN adduser --disabled-password --gecos "" appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `docker-compose.yml` (Local Development)

Services:
| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `gateway` | `./Dockerfile` | 8000 | FastAPI gateway |
| `redis` | `redis:7-alpine` | 6379 | L1 cache + rate limit + queue |
| `qdrant` | `qdrant/qdrant` | 6333 | L2 vector store |
| `postgres` | `postgres:15-alpine` | 5432 | Core relational DB |
| `prometheus` | `prom/prometheus` | 9090 | Metrics scraping |
| `grafana` | `grafana/grafana` | 3000 | Dashboard visualisation |

### Docker Rules Agents Must Follow
- Application must run as a **non-root user**
- No secrets in `Dockerfile` or `docker-compose.yml` — use `.env` file or Docker secrets
- Base image must be `-slim` variant to minimise attack surface
- `PYTHONPATH` must be set in the container environment
- Health checks required for `gateway` service:
  ```yaml
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
  ```

---

## Kubernetes

### Deployment Strategy

```
Namespace: llm-gateway
├── Deployments
│   ├── gateway          (replicas: 3, HPA: 3–20 based on CPU/RPS)
│   └── analytics-worker (replicas: 2)
├── Services
│   ├── gateway-svc      (ClusterIP → Ingress)
│   └── redis-svc        (ClusterIP)
├── Ingress
│   └── gateway-ingress  (NGINX, TLS termination, rate-limit annotations)
├── ConfigMaps
│   └── gateway-config   (non-secret env vars)
├── Secrets
│   └── gateway-secrets  (API keys, DB passwords — from Vault or Secrets Manager)
└── HorizontalPodAutoscaler
    └── gateway-hpa      (min: 3, max: 20, CPU target: 70%)
```

### Auto-Scaling Rules
- HPA must trigger scale-out within **< 2 minutes** of sustained high load
- Scale-in must have a 5-minute stabilisation window to avoid flapping
- Pod disruption budget: minimum 2 replicas always available during rolling update

### Rolling Update Strategy
```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 0
```

### Resource Limits (Per Gateway Pod)
```yaml
resources:
  requests:
    cpu: "500m"
    memory: "512Mi"
  limits:
    cpu: "2000m"
    memory: "2Gi"
```

---

## Monitoring Stack

### Prometheus Metrics (Expose from Gateway)

| Metric | Type | Labels | Purpose |
|--------|------|--------|---------|
| `gateway_requests_total` | Counter | `model`, `provider`, `tier`, `cache_hit` | RPS tracking |
| `gateway_request_latency_seconds` | Histogram | `model`, `cache_hit` | P50/P95/P99 latency |
| `gateway_cache_hit_rate` | Gauge | — | Cache effectiveness |
| `gateway_cost_usd_total` | Counter | `model`, `provider` | Cost tracking |
| `gateway_failover_total` | Counter | `level`, `from_provider` | Failover frequency |
| `gateway_circuit_breaker_state` | Gauge | `provider` | 0=CLOSED, 1=OPEN, 2=HALF_OPEN |
| `gateway_queue_depth` | Gauge | `tier` | Queue backpressure |

### Grafana Dashboards (Pre-built Panels)
1. **Operational Overview** — RPS, error rate, P95 latency, cache hit rate
2. **Cost Tracking** — cost/hour, cost reduction %, provider distribution
3. **Failover Health** — circuit breaker states, failover counts per level
4. **Tier Analytics** — request distribution by tier, quota utilisation
5. **Provider Performance** — latency and error rate per provider

Dashboards stored in `monitoring/grafana/dashboards/` as JSON files.

### Alerting Rules (Prometheus)

| Alert | Condition | Severity |
|-------|-----------|----------|
| `HighErrorRate` | Error rate > 0.1% for 5 min | Critical |
| `HighLatency` | P95 latency > 2 s for 5 min | Warning |
| `LowCacheHitRate` | Cache hit rate < 25% for 1 h | Warning |
| `CircuitBreakerOpen` | Any provider circuit open > 60 s | Critical |
| `QueueDepthHigh` | Any tier queue depth > 1000 for 2 min | Warning |
| `CostSpikeDetected` | Cost/hour > 2× 7-day average | Warning |

---

## Secrets Management

| Secret | Storage (POC) | Storage (Production) |
|--------|--------------|---------------------|
| LLM Provider API Keys | `.env` file (gitignored) | AWS Secrets Manager / HashiCorp Vault |
| DB Password | `.env` file | Kubernetes Secret (from Vault) |
| JWT Secret | `.env` file | Kubernetes Secret |
| Redis Password | `.env` file | Kubernetes Secret |

Rules:
- `.env` must never be committed to git — enforced by `.gitignore`
- `.env.example` must exist with all keys but no values
- In Kubernetes, secrets injected as env vars from `secretKeyRef` — never in ConfigMaps
- CI uses `${{ secrets.* }}` — no plaintext secrets in workflow files

---

## Deployment Commands

```bash
# Local development
docker-compose up -d
py -m uvicorn src.api.main:app --port 8000 --reload

# Seed demo data
py demo/seed_demo_data.py

# Build Docker image
docker build -t llm-gateway:latest .

# Apply Kubernetes manifests
kubectl apply -f k8s/ -n llm-gateway

# Check rollout status
kubectl rollout status deployment/gateway -n llm-gateway

# View logs
kubectl logs -l app=gateway -n llm-gateway --tail=100 -f
```

---

## DevOps Constraints (Agents Must Enforce)

1. No secrets committed to git — `.gitignore` must include `.env`
2. All Docker images must run as non-root users
3. CI pipeline must pass before any merge to `main`
4. Coverage threshold must not be lowered
5. Security scan (`bandit`) must exit 0
6. New Prometheus metrics must use the `gateway_` prefix
7. Grafana dashboard changes must be exported as JSON to `monitoring/`
8. HPA min replicas must be ≥ 3 for production deployments
9. Pod disruption budget must maintain ≥ 2 available replicas
10. Health check endpoint `/health` must always return 200 when service is ready
