# Evidence Directory — LLM Gateway Platform

> Purpose: Evaluation evidence for Propeller Technothon judges
> Status: POC Demo Verified — 8/8 PASS

---

## Contents

| File | Evidence Type | Status |
|------|--------------|--------|
| `demo-8-pass-output.md` | Terminal output — all 8 demo scenarios PASS | ✅ |
| `analytics-summary-output.md` | Analytics API response — 42.2% cache hit rate | ✅ |
| `ci-pipeline-status.md` | CI pipeline — lint + test + coverage + bandit PASS | ✅ |
| `nfr-routing-evidence.md` | NFR header routing — model selection verified | ✅ |
| `cache-hit-evidence.md` | Semantic cache — MISS then HIT for paraphrased prompt | ✅ |
| `failover-evidence.md` | Failover + circuit breaker — triggered and recovered | ✅ |

---

## Key Metrics (Verified)

| Metric | Target | Achieved |
|--------|--------|----------|
| Cache hit rate | > 40% | **42.2%** ✅ |
| API latency P95 (cached) | < 500ms | **3–5ms** ✅ |
| API latency P95 (uncached) | < 2s | **~720ms avg** ✅ |
| Failover time | < 500ms | **Instant (in-process)** ✅ |
| Error rate | < 0.1% | **0 errors** ✅ |
| Demo scenarios passing | 8/8 | **8/8** ✅ |
