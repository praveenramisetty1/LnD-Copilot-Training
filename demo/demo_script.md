# Demo Script — LLM Gateway POC
**Propeller Technothon | Problem Statement 4**
**Duration: 15 minutes | Presenter guide — follow step-by-step**

---

## Pre-Demo Checklist (30 min before)
```
□ Gateway running:  PYTHONPATH=. uvicorn src.api.main:app --reload --port 8000
□ Demo data seeded: PYTHONPATH=. python demo/seed_demo_data.py
□ Browser tabs open:
    Tab 1 → http://localhost:8000/docs   (Swagger UI)
    Tab 2 → http://localhost:8000/health
    Tab 3 → http://localhost:8000/api/v1/analytics/summary
□ Terminal visible in VS Code (for log output)
□ Backup video ready: demo/backup_demo.mp4
```

---

## Minute 0–2: Problem Statement & Business Case

**Say:**
> "Without this gateway, every team calling LLMs faces three problems:
> 1. They pay full API price — even for repeated questions.
> 2. One provider outage means total downtime.
> 3. They have no idea what they're spending or why.
>
> In the next 15 minutes I'll show how our LLM Gateway solves all three —
> with NFR-based routing, semantic caching, and automatic failover."

**Show:** Architecture diagram from `docs/06-HLD.md` (copy to slide)

---

## Minute 2–5: NFR-Based Model Selection (DEMO 1)

**Open Swagger UI → POST /api/v1/route**

**Call 1 — Low cost, standard accuracy (expect gemini-flash or claude-3-haiku)**
```json
Authorization: Bearer free-key-001

{
  "messages": [{"role": "user", "content": "What is the capital of France?"}],
  "nfr": {"latency": "medium", "cost": "low", "accuracy": "standard"}
}
```

**Point out in response:**
- `"model": "gemini-flash"` ← cheapest model selected
- `"metadata.selected_reason": "nfr_match"`
- `"metadata.nfr_score": 0.87` ← scoring was applied
- `"metadata.cost": 0.000004` ← ultra cheap

**Call 2 — Critical accuracy (expect gpt-4 or claude-3-opus)**
```json
Authorization: Bearer pro-key-001

{
  "messages": [{"role": "user", "content": "What is the capital of France?"}],
  "nfr": {"latency": "high", "cost": "high", "accuracy": "critical"}
}
```

**Point out:**
- `"model": "gpt-4"` ← premium model auto-selected for critical accuracy
- `"metadata.cache_hit": true` ← same question, served from cache!

**Say:**
> "Two requests — different NFRs — different models selected automatically.
> No code change. No hardcoded model names. Just headers."

---

## Minute 5–8: Semantic Cache (DEMO 2)

**Call 3 — Paraphrased version of same question**
```json
Authorization: Bearer free-key-001

{
  "messages": [{"role": "user", "content": "Which city is the capital of France?"}],
  "nfr": {"latency": "low", "cost": "low", "accuracy": "standard"}
}
```

**Point out:**
- `"metadata.cache_hit": true` ← different wording, same cache hit!
- `"metadata.latency_ms": 12` ← 12ms vs 800ms uncached
- `"metadata.cost": 0.0` ← zero API cost

**Open analytics:** `GET /api/v1/analytics/summary`

**Point out:**
- `cache_hit_rate` → 40–50% after seeded data
- `total_cost` → compare with what it would have been without cache

**Say:**
> "The cache uses cosine similarity on word-frequency vectors.
> No external vector DB. No embeddings API call.
> Pure Python — and it saved us \$0 on that last request."

---

## Minute 8–11: Failover (DEMO 3)

**Step 1 — Show current health:**
```
GET /health
```
> All providers: CLOSED (healthy)

**Step 2 — Force OpenAI down:**
```
POST /api/v1/providers/openai/circuit/open
Authorization: Bearer enterprise-key-001
```

**Step 3 — Send a request:**
```json
Authorization: Bearer enterprise-key-001

{
  "messages": [{"role": "user", "content": "Explain the theory of relativity"}],
  "nfr": {"latency": "low", "cost": "medium", "accuracy": "high"}
}
```

**Point out:**
- `"provider": "anthropic"` ← automatically failed over!
- `"metadata.failover_count": 1`
- Request still succeeded — user never saw an error

**Step 4 — Restore OpenAI:**
```
POST /api/v1/providers/openai/circuit/close
```

**Say:**
> "OpenAI went down. The gateway detected it in under 500ms,
> fell back to Anthropic, and the user received a response.
> The circuit breaker will now probe OpenAI and recover automatically."

---

## Minute 11–13: Analytics Dashboard (DEMO 4)

**Open:** `GET /api/v1/analytics/summary`

**Point out:**
- `total_requests` — traffic volume
- `cache_hit_rate` — cost savings evidence
- `provider_distribution` — which providers are being used
- `avg_latency_ms` and `p95_latency_ms` — performance evidence
- `total_cost` and `avg_cost_per_request` — spend visibility

**Open:** `GET /api/v1/analytics/recent?limit=5`

**Say:**
> "Every request is logged — model used, provider, cost, latency,
> cache hit, failover count, tier, and NFR parameters.
> This is your full audit trail and cost ledger in one place."

---

## Minute 13–15: Architecture Walkthrough + Q&A Setup

**Show diagram:** `docs/06-HLD.md` request lifecycle

**Say:**
> "Every request flows through: Auth → NFR Parse → Semantic Cache → Model Selector
> → Failover Manager → Provider → Cache Store → Analytics.
> All state lives in local JSON files — no Redis, no PostgreSQL needed for the POC.
> In production this maps directly to Redis + Qdrant + TimescaleDB."

**Hand to judges:**
> "We have Q&A prep in `demo/qna_prep.md` covering the 10 most likely questions.
> Score projections are in `docs/14-Architecture-Review.md`.
> What would you like to explore first?"

---

## Emergency Fallback

If the live demo breaks:
1. Play `demo/backup_demo.mp4`
2. Show static screenshots from `docs/evidence/`
3. Walk through the code in VS Code (nfr_parser.py → model_selector.py → failover.py)
