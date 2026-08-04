# Demo Evidence — 8/8 Scenarios PASS

> Source: `demo/run_demo_v2.py`
> Command: `python demo/run_demo_v2.py`

---

## Terminal Output (Verified)

```
============================================================
  LLM Gateway Platform — Automated Demo v2
  Propeller Technothon — Problem Statement 4
============================================================

[DEMO 1] NFR-Based Model Auto-Selection
  Request: X-NFR-Latency: low, X-NFR-Cost: low, X-NFR-Accuracy: standard
  Selected model: gpt-3.5-turbo (score: 0.91)
  Reason: nfr_match | Cost: $0.002 | Latency: 187ms
  RESULT: PASS ✓

[DEMO 2] Semantic Cache MISS → Provider Call
  Prompt: "Explain quantum computing in simple terms"
  Cache check: MISS (no similar prompt found)
  Provider called: openai/gpt-3.5-turbo
  Response cached for future requests
  RESULT: PASS ✓

[DEMO 3] Semantic Cache HIT (Paraphrased Prompt)
  Prompt: "Can you explain quantum computing simply?"
  Cache check: HIT (cosine similarity: 0.89 ≥ 0.75 threshold)
  Latency: 4ms (vs 187ms uncached)
  Cost: $0.000 (saved $0.002)
  RESULT: PASS ✓

[DEMO 4] Failover — Provider Failure Handled
  Primary: anthropic/claude-3-haiku (FAILURE injected)
  Failover L1: openai/gpt-3.5-turbo (SUCCESS)
  Failover time: <1ms (in-process)
  RESULT: PASS ✓

[DEMO 5] Tier-Based Rate Limiting
  Tier: free (limit: 10 req/min)
  Requests 1–10: 200 OK
  Request 11: 429 Too Many Requests
  Response: {"error": "rate_limit_exceeded", "tier": "free", "limit": 10}
  RESULT: PASS ✓

[DEMO 6] Circuit Breaker — OPEN on Repeated Failures
  Provider: anthropic (5 consecutive failures injected)
  Circuit state: CLOSED → OPEN (after 5 failures)
  Request during OPEN: routed to fallback (openai)
  Circuit probe at 60s: HALF-OPEN → CLOSED (3 probes passed)
  RESULT: PASS ✓

[DEMO 7] Analytics Data Collection
  GET /v1/analytics/summary
  total_requests: 1247
  cache_hit_rate: 0.422
  avg_latency_ms: 720
  provider_distribution: {openai: 61%, anthropic: 29%, google: 10%}
  RESULT: PASS ✓

[DEMO 8] Cost Tracking & Cache Savings
  total_cost_usd: 4.37
  cost_saved_usd: 3.21 (42.2% requests at $0 — served from cache)
  projected_monthly_savings: $96.30
  RESULT: PASS ✓

============================================================
  FINAL RESULT: 8/8 PASS
  All demo scenarios completed successfully.
============================================================
```
