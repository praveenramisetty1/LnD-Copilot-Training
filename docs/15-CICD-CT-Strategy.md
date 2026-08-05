# CI/CD/CT Strategy — LLM Gateway Platform
> **Document Type:** Engineering Strategy  
> **Scope:** Continuous Integration, Continuous Deployment, Continuous Testing  
> **Target Environment:** Cloud-based, high-scalability production deployment  
> **Aligns With:** ADR-001 (Tech Stack), ADR-009 (Circuit Breaker), docs/06-HLD.md  
> **Last Updated:** 2026-02  

---

## 1. Executive Summary

This document defines the end-to-end CI/CD/CT strategy for the LLM Gateway Platform. It covers:

- **Continuous Integration (CI):** Automated build, lint, test, code scanning, and coverage on every commit
- **Continuous Testing (CT):** Multi-layered testing including unit, integration, contract, load, and chaos testing at every stage of the pipeline
- **Continuous Deployment (CD):** Automated, staged delivery to cloud infrastructure (AWS EKS) with zero-downtime releases, image scanning, and production safeguards

The strategy is designed for **high scalability** (10,000+ RPS), **security-first delivery**, and **operator confidence** — every artifact that reaches production has been tested, scanned, verified, and approved.

---

## 2. Pipeline Overview

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         DEVELOPER WORKSTATION                              │
│  git commit → pre-commit hooks (lint, format, secret scan)                 │
└───────────────────────────────┬────────────────────────────────────────────┘
                                │ git push / PR
                                ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                    STAGE 1 — CONTINUOUS INTEGRATION                        │
│  Trigger: PR to develop / main                                             │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  Checkout   │→ │  Lint &      │→ │  Unit &      │→ │  Code         │  │
│  │  & Build    │  │  Format      │  │  Integration │  │  Scanning     │  │
│  └─────────────┘  └──────────────┘  │  Tests (CT)  │  │  (SAST/SCA)   │  │
│                                      └──────────────┘  └───────────────┘  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Coverage Gate (≥80%) │ Quality Gate │ PR Block on failure          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────┬────────────────────────────────────────────┘
                                │ merge to develop
                                ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                    STAGE 2 — BUILD & IMAGE SECURITY                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Docker      │→ │  Image       │→ │  Push to     │→ │  Sign Image  │  │
│  │  Build       │  │  Scan        │  │  ECR         │  │  (Cosign)    │  │
│  │  (multi-     │  │  (Trivy +    │  │              │  │              │  │
│  │  stage)      │  │  Snyk)       │  │              │  │              │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
│  Block on CRITICAL/HIGH CVEs with no fix available                         │
└───────────────────────────────┬────────────────────────────────────────────┘
                                │ image verified + signed
                                ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                    STAGE 3 — DEPLOY TO STAGING (EKS)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Helm Chart  │→ │  Deploy to   │→ │  Smoke &     │→ │  Contract    │  │
│  │  Render &    │  │  EKS Staging │  │  Sanity      │  │  Tests (CT)  │  │
│  │  Validate    │  │  Namespace   │  │  Tests       │  │              │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────────┐  ┌──────────────┐                                        │
│  │  Load Tests  │→ │  Chaos Tests │                                        │
│  │  (Locust)    │  │  (optional)  │                                        │
│  └──────────────┘  └──────────────┘                                        │
└───────────────────────────────┬────────────────────────────────────────────┘
                                │ all gates pass
                                ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                    STAGE 4 — DEPLOY TO PRODUCTION (EKS)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Manual      │→ │  Blue/Green  │→ │  Progressive │→ │  Post-Deploy │  │
│  │  Approval    │  │  or Canary   │  │  Traffic     │  │  Smoke Tests │  │
│  │  Gate        │  │  Deploy      │  │  Shift       │  │  & Alerts    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Automated Rollback on error rate spike or P95 latency breach       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Branching Strategy

```
main ──────────────────────────────────────────────► production releases (tags)
  └── develop ──────────────────────────────────────► staging deployments
        ├── feature/nfr-parser-v2                   ► feature branches
        ├── feature/semantic-cache-qdrant            
        ├── fix/circuit-breaker-threshold            
        └── chore/update-dependencies               
```

| Branch | Trigger | Target Environment |
|--------|---------|-------------------|
| `feature/*` | Push | CI only (no deploy) |
| `develop` | Merge | Auto-deploy to Staging |
| `release/*` | Push | Auto-deploy to Staging + UAT |
| `main` | Tag `v*.*.*` | Manual-gated Production deploy |

### Branch Protection Rules
- `main`: Require PR, 2 approvals, all CI checks pass, no direct push
- `develop`: Require PR, 1 approval, CI pass
- Commit signing enforced on `main`

---

## 4. Continuous Integration (CI) — Detailed

### 4.1 Pre-Commit Hooks (Developer Workstation)

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    hooks:
      - id: ruff           # lint
      - id: ruff-format    # format

  - repo: https://github.com/pre-commit/pre-commit-hooks
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: detect-private-key   # secret detection

  - repo: https://github.com/Yelp/detect-secrets
    hooks:
      - id: detect-secrets        # prevent secret commits
        args: ['--baseline', '.secrets.baseline']
```

### 4.2 CI Pipeline Jobs (GitHub Actions)

```yaml
# .github/workflows/ci.yml  (extended)
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  # ── Job 1: Lint & Format ──────────────────────────────────────────────────
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11", cache: "pip" }
      - run: pip install ruff
      - run: ruff check src/ tests/ --select E,F,I,S,B --ignore E501
      - run: ruff format --check src/ tests/

  # ── Job 2: Unit + Integration Tests (CT Layer 1 & 2) ─────────────────────
  test:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11", cache: "pip" }
      - run: pip install -r requirements.txt
      - name: Unit Tests
        env: { PYTHONPATH: ${{ github.workspace }} }
        run: pytest tests/unit/ -v --tb=short --junitxml=reports/unit.xml
      - name: Integration Tests
        env: { PYTHONPATH: ${{ github.workspace }} }
        run: pytest tests/integration/ -v --tb=short --junitxml=reports/integration.xml
      - name: Coverage Gate (≥80%)
        env: { PYTHONPATH: ${{ github.workspace }} }
        run: |
          pytest tests/unit/ tests/integration/ \
            --cov=src --cov-report=xml:reports/coverage.xml \
            --cov-report=html:reports/coverage-html \
            --cov-fail-under=80
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: test-reports
          path: reports/

  # ── Job 3: Code Scanning — SAST ───────────────────────────────────────────
  sast:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - name: Bandit SAST Scan
        run: |
          pip install bandit[toml]
          bandit -r src/ -ll -f json -o reports/bandit.json
      - name: Semgrep SAST Scan
        uses: semgrep/semgrep-action@v1
        with:
          config: >-
            p/python
            p/owasp-top-ten
            p/secrets
            p/jwt
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: sast-reports
          path: reports/bandit.json

  # ── Job 4: SCA — Dependency Vulnerability Scan ────────────────────────────
  sca:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - name: Safety — Python Dependency Scan
        run: |
          pip install safety
          safety check -r requirements.txt --json > reports/safety.json
      - name: Snyk SCA Scan
        uses: snyk/actions/python@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --severity-threshold=high --file=requirements.txt
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: sca-reports
          path: reports/safety.json

  # ── Job 5: Secret Detection ────────────────────────────────────────────────
  secret-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - name: Gitleaks Secret Scan
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### 4.3 Quality Gates — CI Must Pass Before Merge

| Gate | Tool | Threshold | Action on Fail |
|------|------|-----------|----------------|
| Lint | Ruff | 0 errors | Block PR |
| Unit Tests | pytest | 100% pass | Block PR |
| Integration Tests | pytest | 100% pass | Block PR |
| Code Coverage | pytest-cov | ≥ 80% | Block PR |
| SAST — Critical | Bandit / Semgrep | 0 critical | Block PR |
| SAST — High | Bandit / Semgrep | 0 high | Block PR |
| SCA — Critical CVE | Safety / Snyk | 0 critical | Block PR |
| SCA — High CVE | Safety / Snyk | 0 high (no fix) | Block PR |
| Secret Detection | Gitleaks | 0 secrets | Block PR |

---

## 5. Continuous Testing (CT) — Multi-Layer Strategy

```
┌──────────────────────────────────────────────────────────────┐
│                    TESTING PYRAMID                           │
│                                                              │
│                         ▲                                   │
│                        ╱ ╲  Chaos / Resilience Tests        │
│                       ╱───╲ (Staging only)                  │
│                      ╱     ╲                                │
│                     ╱───────╲ Load / Performance Tests      │
│                    ╱         ╲ (Staging + Locust)           │
│                   ╱───────────╲                             │
│                  ╱             ╲ Contract Tests             │
│                 ╱───────────────╲ (Provider API contracts)  │
│                ╱                 ╲                          │
│               ╱───────────────────╲ Integration Tests      │
│              ╱                     ╲ (FastAPI TestClient)   │
│             ╱─────────────────────────╲                     │
│            ╱   Unit Tests (66+ tests)   ╲                   │
│           ╱─────────────────────────────────╲               │
└──────────────────────────────────────────────────────────────┘
```

### 5.1 Layer 1 — Unit Tests (CI Stage)
- **Scope:** Individual functions, classes, algorithms
- **Tools:** pytest, pytest-mock
- **Files:** `tests/unit/test_nfr_parser.py`, `test_model_selector.py`, `test_failover.py`, `test_semantic_cache.py`
- **Coverage Target:** ≥ 80%
- **Run:** Every push, every PR

### 5.2 Layer 2 — Integration Tests (CI Stage)
- **Scope:** API endpoint behaviour, middleware chain, cache + router interaction
- **Tools:** pytest + FastAPI TestClient
- **Files:** `tests/integration/test_route_endpoint.py`
- **Run:** Every push, every PR

### 5.3 Layer 3 — Contract Tests (Staging Stage)
- **Scope:** Validate that provider simulator responses conform to the expected OpenAI/Anthropic/Google API contract shapes
- **Tools:** pact-python (Consumer-Driven Contract Testing)
- **Test Cases:**
  - NFR header → model selection contract
  - Failover chain contract (L1 → L4 response shape)
  - Cache hit/miss response metadata contract
- **Run:** On deploy to Staging

### 5.4 Layer 4 — Load / Performance Tests (Staging Stage)
- **Scope:** Throughput, latency P95, cache hit rate under concurrent load
- **Tools:** Locust (`tests/load/locustfile.py`)
- **Scenarios:**
  - Scenario A: 1,000 concurrent users, ramp 10 users/sec → measure P95
  - Scenario B: Cache warm-up run → verify ≥ 40% hit rate
  - Scenario C: Failover under load → verify <500ms failover time
- **Pass Criteria:**

| Metric | Target |
|--------|--------|
| P95 Latency (cached) | < 500ms |
| P95 Latency (uncached) | < 2,000ms |
| Error Rate | < 0.1% |
| Cache Hit Rate | ≥ 40% |
| Throughput | ≥ 10,000 RPS (architecture verified) |

- **Run:** On deploy to Staging, nightly on Staging

### 5.5 Layer 5 — Chaos / Resilience Tests (Staging Stage)
- **Scope:** Validate circuit breaker, failover, and rate limiting under fault conditions
- **Tools:** Chaos Toolkit / custom failure injection via provider simulator
- **Scenarios:**
  - Kill primary provider → verify L1 failover activates in < 500ms
  - Inject 5 consecutive failures → verify circuit breaker opens
  - Saturate rate limiter → verify 429 returned, no provider leak
  - Restart gateway pod mid-request → verify no data loss
- **Run:** Weekly on Staging, optional pre-production gate

### 5.6 CT Execution Matrix

| Test Layer | Dev Workstation | CI (PR) | CI (merge) | Staging | Production |
|------------|:-:|:-:|:-:|:-:|:-:|
| Unit | ✅ | ✅ | ✅ | — | — |
| Integration | ✅ | ✅ | ✅ | — | — |
| Contract | — | — | — | ✅ | — |
| Load / Performance | — | — | — | ✅ nightly | — |
| Chaos / Resilience | — | — | — | ✅ weekly | — |
| Smoke (post-deploy) | — | — | — | ✅ | ✅ |

---

## 6. Build & Image Security (STAGE 2)

### 6.1 Multi-Stage Dockerfile

```dockerfile
# ── Stage 1: Builder ────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Runtime ────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Security: non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

WORKDIR /app
COPY --from=builder /install /usr/local
COPY src/ ./src/

# Security: drop all Linux capabilities
USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "4", "--no-access-log"]
```

### 6.2 Image Vulnerability Scanning

```yaml
# In GitHub Actions — image-scan job
  image-build-scan:
    runs-on: ubuntu-latest
    needs: [test, sast, sca]
    steps:
      - uses: actions/checkout@v4

      - name: Build Docker image
        run: |
          docker build -t llm-gateway:${{ github.sha }} .

      # ── Trivy: OS + Library CVE scan ──────────────────────────────────────
      - name: Trivy Image Scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: llm-gateway:${{ github.sha }}
          format: sarif
          output: reports/trivy.sarif
          severity: CRITICAL,HIGH
          exit-code: 1          # Block pipeline on CRITICAL or HIGH with fix

      # ── Snyk: Container scan ──────────────────────────────────────────────
      - name: Snyk Container Scan
        uses: snyk/actions/docker@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          image: llm-gateway:${{ github.sha }}
          args: --severity-threshold=high

      # ── Grype: Additional CVE cross-reference ─────────────────────────────
      - name: Grype Image Scan
        uses: anchore/scan-action@v3
        with:
          image: llm-gateway:${{ github.sha }}
          fail-build: true
          severity-cutoff: high

      # ── Upload SARIF to GitHub Security tab ───────────────────────────────
      - name: Upload Trivy SARIF
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: reports/trivy.sarif

      # ── Push to ECR (only if all scans pass) ──────────────────────────────
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Push to Amazon ECR
        run: |
          aws ecr get-login-password | docker login --username AWS \
            --password-stdin ${{ secrets.ECR_REGISTRY }}
          docker tag llm-gateway:${{ github.sha }} \
            ${{ secrets.ECR_REGISTRY }}/llm-gateway:${{ github.sha }}
          docker push ${{ secrets.ECR_REGISTRY }}/llm-gateway:${{ github.sha }}

      # ── Sign image with Cosign (supply chain security) ────────────────────
      - name: Sign image with Cosign
        uses: sigstore/cosign-installer@v3
      - run: |
          cosign sign --yes \
            ${{ secrets.ECR_REGISTRY }}/llm-gateway:${{ github.sha }}
```

### 6.3 Image Scanning Gates

| Scanner | Scope | Block On | Report Destination |
|---------|-------|----------|--------------------|
| **Trivy** | OS packages + Python libs | CRITICAL / HIGH (with fix) | GitHub Security tab (SARIF) |
| **Snyk Container** | Base image + dependencies | HIGH+ | Snyk Dashboard |
| **Grype (Anchore)** | Full SBOM + CVE cross-ref | HIGH+ | CI logs + artifact |
| **Cosign** | Image signing / provenance | Unsigned image rejected | ECR image metadata |

---

## 7. Cloud Deployment Architecture (AWS EKS)

### 7.1 Infrastructure Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AWS CLOUD (us-east-1 + us-west-2)                 │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                        Route 53 (DNS Failover)                       │   │
│  └───────────────────────────────┬──────────────────────────────────────┘   │
│                                  │                                           │
│  ┌───────────────────────────────▼──────────────────────────────────────┐   │
│  │              AWS Application Load Balancer (ALB)                     │   │
│  │              WAF + Shield + SSL Termination                          │   │
│  └────────┬──────────────────────────────────────────┬─────────────────┘   │
│           │                                          │                      │
│  ┌────────▼─────────────┐              ┌─────────────▼──────────────────┐   │
│  │   EKS Cluster        │              │   EKS Cluster                  │   │
│  │   us-east-1 (Primary)│              │   us-west-2 (Secondary)        │   │
│  │                      │              │                                │   │
│  │  ┌────────────────┐  │              │  ┌────────────────────────┐    │   │
│  │  │ llm-gateway    │  │              │  │ llm-gateway (standby)  │    │   │
│  │  │ Pods (3–20)    │  │              │  │ Pods (2–10)            │    │   │
│  │  │ HPA: CPU+RPS   │  │              │  │ HPA: CPU+RPS           │    │   │
│  │  └────────────────┘  │              │  └────────────────────────┘    │   │
│  │  ┌────────────────┐  │              │                                │   │
│  │  │ Redis Cluster  │  │              │                                │   │
│  │  │ (ElastiCache)  │◄─┼─────────────┼─ Global Datastore Replication  │   │
│  │  └────────────────┘  │              │                                │   │
│  │  ┌────────────────┐  │              │                                │   │
│  │  │ Qdrant Cluster │  │              │                                │   │
│  │  │ (StatefulSet)  │  │              │                                │   │
│  │  └────────────────┘  │              │                                │   │
│  │  ┌────────────────┐  │              │                                │   │
│  │  │ TimescaleDB    │  │              │                                │   │
│  │  │ (RDS Postgres) │  │              │                                │   │
│  │  └────────────────┘  │              │                                │   │
│  └──────────────────────┘              └────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  Shared Services                                                     │   │
│  │  ┌────────────┐  ┌────────────┐  ┌──────────────┐  ┌────────────┐  │   │
│  │  │ ECR        │  │ Secrets    │  │ CloudWatch   │  │ S3 (logs,  │  │   │
│  │  │ (images)   │  │ Manager    │  │ + Grafana    │  │ artifacts) │  │   │
│  │  └────────────┘  └────────────┘  └──────────────┘  └────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Kubernetes Manifests (Key Resources)

#### Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: llm-gateway
  namespace: production
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 25%
      maxUnavailable: 0        # Zero-downtime
  selector:
    matchLabels:
      app: llm-gateway
  template:
    spec:
      containers:
        - name: llm-gateway
          image: <ECR_REGISTRY>/llm-gateway:<SHA>
          ports:
            - containerPort: 8000
          resources:
            requests:
              cpu: "500m"
              memory: "512Mi"
            limits:
              cpu: "2000m"
              memory: "2Gi"
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
          env:
            - name: API_KEYS
              valueFrom:
                secretKeyRef:
                  name: llm-gateway-secrets
                  key: api-keys
          securityContext:
            runAsNonRoot: true
            runAsUser: 1000
            readOnlyRootFilesystem: true
            allowPrivilegeEscalation: false
```

#### Horizontal Pod Autoscaler
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: llm-gateway-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: llm-gateway
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "500"    # Scale when avg RPS per pod > 500
```

#### Pod Disruption Budget
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: llm-gateway-pdb
  namespace: production
spec:
  minAvailable: 2              # Always keep at least 2 pods running
  selector:
    matchLabels:
      app: llm-gateway
```

### 7.3 Scalability Targets

| Tier | Pods | Est. RPS per Pod | Total RPS |
|------|------|-----------------|-----------|
| Minimum (3 pods) | 3 | 500 | 1,500 |
| Normal (5 pods) | 5 | 500 | 2,500 |
| High Load (10 pods) | 10 | 500 | 5,000 |
| Peak (20 pods) | 20 | 500 | 10,000+ |

Auto-scale trigger: CPU > 70% or RPS per pod > 500 → add pod within 60s.

---

## 8. Continuous Deployment (CD) — Detailed

### 8.1 CD Pipeline (GitHub Actions — CD workflow)

```yaml
# .github/workflows/cd.yml
name: CD

on:
  push:
    tags: ['v*.*.*']           # Production deploy on version tag
  workflow_run:
    workflows: ["CI"]
    branches: [develop]
    types: [completed]         # Staging deploy on CI pass for develop

jobs:
  # ── Deploy to Staging ──────────────────────────────────────────────────────
  deploy-staging:
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      - name: Verify image signature
        run: cosign verify ${{ secrets.ECR_REGISTRY }}/llm-gateway:${{ github.sha }}
      - name: Helm deploy to Staging EKS
        run: |
          aws eks update-kubeconfig --name llm-gateway-staging --region us-east-1
          helm upgrade --install llm-gateway ./helm/llm-gateway \
            --namespace staging \
            --set image.tag=${{ github.sha }} \
            --set replicaCount=2 \
            --wait --timeout 5m
      - name: Smoke Tests (Staging)
        run: pytest tests/smoke/ -v --base-url=https://staging.llm-gateway.internal

  # ── Load Tests on Staging ──────────────────────────────────────────────────
  load-test-staging:
    needs: deploy-staging
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install locust
      - run: |
          locust -f tests/load/locustfile.py \
            --headless -u 500 -r 10 -t 5m \
            --host https://staging.llm-gateway.internal \
            --csv=reports/load \
            --exit-code-on-error 1
      - uses: actions/upload-artifact@v4
        with:
          name: load-test-results
          path: reports/load*.csv

  # ── Manual Gate + Production Deploy ───────────────────────────────────────
  deploy-production:
    if: startsWith(github.ref, 'refs/tags/v')
    needs: [test, sast, sca, image-build-scan]
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://api.llm-gateway.io
    steps:
      - uses: actions/checkout@v4
      - name: Verify image signature
        run: cosign verify ${{ secrets.ECR_REGISTRY }}/llm-gateway:${{ github.sha }}
      - name: Blue/Green Deploy to Production EKS
        run: |
          aws eks update-kubeconfig --name llm-gateway-prod --region us-east-1
          helm upgrade --install llm-gateway ./helm/llm-gateway \
            --namespace production \
            --set image.tag=${{ github.sha }} \
            --set replicaCount=3 \
            --set strategy=blue-green \
            --wait --timeout 10m
      - name: Progressive Traffic Shift (Canary)
        run: |
          # Shift 10% traffic to new version
          kubectl patch virtualservice llm-gateway \
            -p '{"spec":{"http":[{"route":[{"destination":{"subset":"v2"},"weight":10},{"destination":{"subset":"v1"},"weight":90}]}]}}'
          sleep 120
          # Check error rate < 0.1% before shifting 100%
          ./scripts/check-canary-health.sh
          kubectl patch virtualservice llm-gateway \
            -p '{"spec":{"http":[{"route":[{"destination":{"subset":"v2"},"weight":100}]}]}}'
      - name: Post-Deploy Smoke Tests
        run: pytest tests/smoke/ -v --base-url=https://api.llm-gateway.io
```

### 8.2 Deployment Strategy — Blue/Green + Canary

```
Traffic Flow During Deployment

Step 1 — Baseline
  ALB → 100% → [v1 pods (3x)]

Step 2 — New version deployed (v2 pods spin up)
  ALB → 100% → [v1 pods (3x)]
              [v2 pods (3x)] ← warming up, readiness probe running

Step 3 — Canary: 10% traffic shift
  ALB → 90% → [v1 pods (3x)]
       10% → [v2 pods (3x)] ← monitor for 2 minutes

Step 4 — Automated health check
  IF error_rate(v2) < 0.1% AND p95_latency(v2) < 500ms:
       → proceed to 100% shift
  ELSE:
       → automated rollback: 100% → v1, alert team

Step 5 — Full cutover
  ALB → 100% → [v2 pods (3x)]
  v1 pods terminate (graceful 30s)
```

### 8.3 Automated Rollback Triggers

| Metric | Threshold | Action |
|--------|-----------|--------|
| HTTP 5xx error rate | > 1% over 2 min | Auto-rollback to previous version |
| P95 latency (cached) | > 600ms over 2 min | Auto-rollback |
| Circuit breaker open rate | > 50% of providers | Alert + auto-rollback |
| Pod crash loop | > 2 restarts in 5 min | Auto-rollback |
| Health check failure | 3 consecutive | Remove pod from LB immediately |

---

## 9. Secrets Management

| Secret | Storage | Access Method |
|--------|---------|---------------|
| LLM Provider API Keys | AWS Secrets Manager | External Secrets Operator → K8s Secret |
| Database credentials | AWS Secrets Manager | External Secrets Operator → K8s Secret |
| JWT signing key | AWS Secrets Manager | External Secrets Operator → K8s Secret |
| ECR credentials | IAM Role for Service Account (IRSA) | Pod-level IAM, no key needed |
| TLS certificates | AWS ACM + cert-manager | Automatic rotation |

**Rules:**
- Zero hardcoded secrets in source code (enforced by Gitleaks + detect-secrets in CI)
- All secrets rotated automatically on 90-day schedule
- Secrets access logged via CloudTrail

---

## 10. Observability Integration

The CD pipeline integrates with the monitoring stack (see `docs/guides/monitoring-guide.md`):

| Signal | Tool | CD Integration |
|--------|------|----------------|
| Metrics | Prometheus + Grafana | Canary health check reads P95 latency + error rate from Prometheus API |
| Logs | AWS CloudWatch Logs / Loki | Deployment events auto-tagged with `sha` + `version` for correlation |
| Traces | OpenTelemetry → Jaeger | Trace IDs propagated from CI test run through to production |
| Alerts | Grafana Alerting | PagerDuty notification on rollback trigger |
| Deployment Events | Grafana annotations | Each deploy annotated automatically via CD pipeline step |

---

## 11. Compliance & Audit Trail

| Requirement | Implementation |
|-------------|----------------|
| Every image traceable to a commit | Image tagged with `git SHA`, signed with Cosign |
| Every deploy auditable | GitHub Actions deploy logs + CloudTrail |
| SBOM (Software Bill of Materials) | Syft generates SBOM at build time, stored in S3 |
| CVE scan results retained | Trivy + Snyk reports stored as CI artifacts (90 days) |
| No unreviewed code in production | Branch protection: 2 approvals + CI pass mandatory |
| Secrets never in logs | Masked in GitHub Actions, CloudWatch log filters applied |

---

## 12. Environment Summary

| Environment | Trigger | EKS Cluster | Replicas | Auto-Scale | Purpose |
|-------------|---------|-------------|----------|------------|---------|
| **Dev** | Local | None | 1 (local) | No | Developer iteration |
| **Staging** | Merge to `develop` | `llm-gateway-staging` | 2 | 2–8 | Integration, load, chaos testing |
| **Production** | Tag `v*.*.*` + approval | `llm-gateway-prod` | 3 | 3–20 | Live traffic |

---

## 13. Tool Reference Summary

| Category | Tool | Purpose |
|----------|------|---------|
| **CI Orchestration** | GitHub Actions | Pipeline execution |
| **Lint / Format** | Ruff | Python code quality |
| **SAST** | Bandit, Semgrep | Static application security testing |
| **SCA** | Safety, Snyk | Dependency CVE scanning |
| **Secret Detection** | Gitleaks, detect-secrets | Pre-commit + CI secret scanning |
| **Image Scan** | Trivy, Snyk Container, Grype | Container CVE scanning |
| **Image Signing** | Cosign (Sigstore) | Supply chain security |
| **SBOM** | Syft | Software Bill of Materials generation |
| **Container** | Docker (multi-stage) | Minimal, non-root image builds |
| **Registry** | Amazon ECR | Private, immutable image registry |
| **Deploy** | Helm + GitHub Actions | Kubernetes release management |
| **Orchestration** | AWS EKS | Managed Kubernetes |
| **Auto-Scale** | HPA (CPU + RPS metrics) | Pod-level horizontal scaling |
| **Load Testing** | Locust | Performance regression detection |
| **Contract Testing** | pact-python | Provider API contract validation |
| **Chaos Testing** | Chaos Toolkit | Resilience validation |
| **Secrets** | AWS Secrets Manager + ESO | Runtime secret injection |
| **Monitoring** | Prometheus + Grafana | Canary health check + alerting |
| **Tracing** | OpenTelemetry + Jaeger | Distributed trace correlation |

---

## 14. ADR References

| ADR | Relevance |
|-----|-----------|
| ADR-001 | FastAPI framework — Uvicorn workers in Docker image |
| ADR-002 | In-memory rate limiter (POC) → Redis (production, provisioned in EKS) |
| ADR-003 | Cache threshold 0.75 — validated by CT load tests |
| ADR-004 | Simulated providers in CI/CT; real providers in production |
| ADR-009 | Circuit breaker thresholds — validated by chaos tests |
| ADR-010 | JSON analytics (POC) → TimescaleDB (production, RDS in EKS) |

---

*This document is the authoritative CI/CD/CT strategy for the LLM Gateway Platform.*  
*Owner: Architecture Team | Review Cycle: Per major release*  
*Related Docs: `docs/06-HLD.md` | `docs/10-Security-Architecture.md` | `docs/guides/monitoring-guide.md`*
