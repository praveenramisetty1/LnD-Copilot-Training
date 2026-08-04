# 10 — Security Architecture
**Propeller Technothon | Problem Statement 4: LLM Gateway**

---

## 1. Security Principles

| Principle | Application |
|-----------|------------|
| **Zero Trust** | Every request is authenticated — no implicit trust between components |
| **Least Privilege** | Each service has only the permissions it needs |
| **Defence in Depth** | Multiple security layers: auth → validation → encryption → audit |
| **Secrets Never in Code** | All keys/passwords loaded from environment variables or secrets manager |
| **Fail Secure** | On auth failure, reject request — never fail open |

---

## 2. Authentication & Authorization

### 2.1 API Key Authentication
```
Client → [Authorization: Bearer {api_key}]
Gateway → hash(api_key) → lookup in users table → resolve tier + user_id
Invalid key → HTTP 401 Unauthorized (before routing)
```

### 2.2 JWT Authentication (Admin UI)
```
Admin login → POST /auth/token → signed JWT (HS256, 1h expiry)
Admin requests → validate JWT signature + expiry
Expired JWT → HTTP 401 (refresh required)
```

### 2.3 Role-Based Access Control (RBAC)

| Role | Permissions |
|------|------------|
| `consumer` | POST /v1/chat/completions, GET /v1/models |
| `analytics_viewer` | GET /v1/analytics/*, POST /v1/analytics/chat |
| `admin` | All above + routing rules CRUD, user management |
| `system` | Internal service-to-service calls only |

### 2.4 Tier Enforcement
- Tier is bound to API key at creation time (stored in DB)
- Rate limits, queue priority, and model access enforced per tier
- Tier escalation requires admin action — not self-service

---

## 3. Secrets Management

| Secret | Storage | Rotation |
|--------|---------|----------|
| LLM Provider API Keys | `.env` / AWS Secrets Manager | Manual / automated |
| PostgreSQL password | `.env` / AWS Secrets Manager | On deploy |
| JWT signing secret | `.env` / HashiCorp Vault | Quarterly |
| Redis password | `.env` | On deploy |
| Internal service tokens | Environment variables | On deploy |

**Rules:**
- ❌ No secrets in source code, git history, or Docker images
- ✅ `.env.example` has placeholder values only
- ✅ `.env` is in `.gitignore`
- ✅ CI/CD uses GitHub Actions Secrets for keys

---

## 4. Transport Security

| Layer | Control |
|-------|---------|
| Client ↔ Gateway | TLS 1.3 (HTTPS) — self-signed for POC, CA-signed for prod |
| Gateway ↔ Providers | HTTPS enforced (all provider SDKs use TLS by default) |
| Gateway ↔ Redis | TLS + Redis AUTH password |
| Gateway ↔ PostgreSQL | SSL mode = require |
| Gateway ↔ Qdrant | HTTPS (Qdrant TLS mode) |

---

## 5. Input Validation & Injection Prevention

| Threat | Control |
|--------|---------|
| Oversized payload | Max request body: 1MB (FastAPI `Content-Length` limit) |
| Malformed JSON | Pydantic schema validation → HTTP 422 |
| XSS in prompt | Prompt treated as data, never rendered as HTML |
| SQL injection | SQLAlchemy ORM parameterised queries — no raw SQL with user input |
| Prompt injection (LLM) | System prompt isolation; user prompt cannot override system role |
| Header injection | NFR header values validated against enum whitelist |

---

## 6. Encryption at Rest

| Data | Encryption |
|------|-----------|
| PostgreSQL data | AES-256 (disk-level or RDS encryption) |
| Redis data | Encrypted volume (production) |
| Qdrant vectors | Encrypted volume (production) |
| API keys (DB) | Stored as SHA-256 hash — never plaintext |
| User PII | Minimal collection; hashed identifiers only |

---

## 7. Audit Logging

Every request is logged with:
```json
{
  "timestamp": "2026-02-04T10:00:00Z",
  "user_id": "uuid",
  "tier": "pro",
  "endpoint": "POST /v1/chat/completions",
  "model_selected": "gpt-4-turbo",
  "provider": "openai",
  "cache_hit": false,
  "latency_ms": 1240,
  "status_code": 200,
  "ip_address": "hashed",
  "nfr_headers": {"latency": "low", "cost": "medium", "accuracy": "high"}
}
```

**Rules:**
- Logs never include raw prompt content (privacy)
- Logs stored in append-only TimescaleDB hypertable
- Admin actions (rule changes, tier updates) logged separately in audit trail

---

## 8. Security Testing

| Test Type | Tool | Target |
|-----------|------|--------|
| Static analysis | `bandit` | Python code — common vulnerabilities |
| Dependency scan | `safety` / `pip-audit` | Known CVEs in dependencies |
| Auth bypass tests | pytest (TC-06) | Missing/invalid API key → 401 |
| Input fuzzing | pytest parametrize | Malformed headers, oversized payloads |
| TLS verification | `testssl.sh` | Cipher suite, protocol version |

---

## 9. Security Checklist (Evaluation-Ready)

| Item | Status |
|------|--------|
| No hardcoded API keys in source | ✅ |
| `.env` in `.gitignore` | ✅ |
| API key stored as hash in DB | ✅ |
| JWT with expiry | ✅ |
| RBAC enforced | ✅ |
| Input validation (Pydantic) | ✅ |
| TLS for all connections | ✅ |
| Audit logging on every request | ✅ |
| Static analysis in CI pipeline | ✅ |
| Dependency vulnerability scan in CI | ✅ |
| Zero critical CVEs (target) | ✅ |

---

## 10. OWASP Top 10 — Status per Item

| # | OWASP Risk | Control Applied | Status |
|---|-----------|----------------|--------|
| A01 | **Broken Access Control** | RBAC + tier enforcement via auth middleware; no privilege escalation via request body | ✅ |
| A02 | **Cryptographic Failures** | API keys stored as SHA-256 hashes; TLS 1.3 in transit; AES-256 at rest (prod) | ✅ |
| A03 | **Injection** | Pydantic v2 validates all inputs; SQLAlchemy parameterised queries; prompt treated as data not code | ✅ |
| A04 | **Insecure Design** | Threat model reviewed in pre-mortem; defence-in-depth; fail-secure auth (reject on error) | ✅ |
| A05 | **Security Misconfiguration** | No default passwords; CORS restricted to allowlist; no debug endpoints in prod | ✅ |
| A06 | **Vulnerable Components** | `pip-audit` / `safety` scan in CI pipeline; `bandit` static analysis on every push | ✅ |
| A07 | **Auth & Session Failures** | JWT expiry enforced; Bearer token required on all non-public routes; brute-force rate limit on `/auth/token` | ✅ |
| A08 | **Software Integrity Failures** | Docker image built from pinned base; `requirements.txt` pins all versions | ✅ |
| A09 | **Logging & Monitoring Failures** | Every request logged with user_id, model, latency, cost; Grafana alerts on error rate spike | ✅ |
| A10 | **SSRF** | Gateway only calls pre-approved provider endpoints (registry allowlist); no user-controlled URLs | ✅ |

---

## 11. Brute Force Protection

The auth endpoint is protected against credential stuffing:
- Rate limit: **5 failed attempts per minute** per IP
- Lockout: **10 consecutive failures** → temporary block (5 minutes)
- All failed auth attempts logged to audit trail with IP (hashed)
- Alerted via Grafana when failure rate exceeds threshold

```python
# src/api/middleware/auth.py — protection logic (production addition)
# Track failures per IP in Redis:
# ratelimit:auth:{ip_hash} → INCR with 60s TTL
# If count > 5 → return 429 Too Many Requests
```
