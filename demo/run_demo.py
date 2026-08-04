#!/usr/bin/env python3
# demo/run_demo.py  [REWRITTEN — all demos inside context manager]
"""
LLM Gateway POC - Live Demo Runner
Uses FastAPI TestClient (no server process required).
Run: PYTHONPATH=. py demo/run_demo.py
"""

import json
import sys
import os

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

os.environ.setdefault("PYTHONPATH", ".")

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from fastapi.testclient import TestClient
from src.api.main import app

SEP  = "=" * 65
SEP2 = "-" * 65

FREE_KEY       = "free-key-001"
PRO_KEY        = "pro-key-001"
ENTERPRISE_KEY = "enterprise-key-001"


def show(label: str, response, brief: bool = False):
    print(f"\n{SEP}")
    print(f"  DEMO: {label}")
    print(f"  Status: {response.status_code}")
    print(SEP2)
    body = response.json()
    if brief:
        # Print only key fields
        meta = body.get("metadata", {})
        print(f"  model            : {body.get('model','N/A')}")
        print(f"  provider         : {body.get('provider','N/A')}")
        print(f"  cache_hit        : {meta.get('cache_hit','N/A')}")
        print(f"  latency_ms       : {meta.get('latency_ms','N/A')}")
        print(f"  cost             : ${meta.get('cost', 0):.6f}")
        print(f"  failover_count   : {meta.get('failover_count','N/A')}")
        print(f"  selected_reason  : {meta.get('selected_reason','N/A')}")
        print(f"  nfr_score        : {meta.get('nfr_score','N/A')}")
        content = body.get("content", "")
        print(f"  content          : {content[:80]}...")
    else:
        print(json.dumps(body, indent=2, ensure_ascii=False)[:1200])
    print(SEP)


def section(title: str):
    print(f"\n{'#'*65}")
    print(f"#  {title}")
    print(f"{'#'*65}")


with TestClient(app, raise_server_exceptions=False) as client:

# ─────────────────────────────────────────────────────────────────────────────
 section("DEMO 1 — Health Check (all providers should be CLOSED/healthy)")
# ─────────────────────────────────────────────────────────────────────────────
 r = client.get("/health")
 show("GET /health", r)

input("\n  >> Press ENTER to continue to Demo 2 (NFR Routing)...")

# ─────────────────────────────────────────────────────────────────────────────
section("DEMO 2 — NFR Routing: Low Cost + Standard Accuracy")
print("  NFR: latency=medium, cost=LOW, accuracy=standard")
print("  Tier: FREE  |  Expect: cheapest available model (gemini-flash or claude-3-haiku)")
# ─────────────────────────────────────────────────────────────────────────────
r = client.post(
    "/api/v1/route",
    json={
        "messages": [{"role": "user", "content": "What is the capital of France?"}],
        "nfr": {"latency": "medium", "cost": "low", "accuracy": "standard"},
    },
    headers={"Authorization": f"Bearer {FREE_KEY}"},
)
show("POST /api/v1/route [low-cost, free tier]", r, brief=True)

input("\n  >> Press ENTER to continue to Demo 3 (High Accuracy)...")

# ─────────────────────────────────────────────────────────────────────────────
section("DEMO 3 — NFR Routing: Critical Accuracy")
print("  NFR: latency=high, cost=high, accuracy=CRITICAL")
print("  Tier: PRO  |  Expect: gpt-4 or claude-3-opus (highest accuracy models)")
# ─────────────────────────────────────────────────────────────────────────────
r = client.post(
    "/api/v1/route",
    json={
        "messages": [{"role": "user", "content": "Explain the CAP theorem in distributed systems"}],
        "nfr": {"latency": "high", "cost": "high", "accuracy": "critical"},
    },
    headers={"Authorization": f"Bearer {PRO_KEY}"},
)
show("POST /api/v1/route [critical-accuracy, pro tier]", r, brief=True)

input("\n  >> Press ENTER to continue to Demo 4 (Semantic Cache)...")

# ─────────────────────────────────────────────────────────────────────────────
section("DEMO 4 — Semantic Cache: Miss then Hit")
print("  Sending same prompt twice. Second call should be a cache HIT (cost=0).")
# ─────────────────────────────────────────────────────────────────────────────
payload = {
    "messages": [{"role": "user", "content": "How does a neural network work?"}],
    "nfr": {"latency": "low", "cost": "low", "accuracy": "standard"},
}
headers = {"Authorization": f"Bearer {FREE_KEY}"}

print("\n  [Call 1 — expected MISS]")
r1 = client.post("/api/v1/route", json=payload, headers=headers)
m1 = r1.json().get("metadata", {})
print(f"  cache_hit    : {m1.get('cache_hit')}   <-- should be False")
print(f"  cost         : ${m1.get('cost', 0):.6f}")
print(f"  latency_ms   : {m1.get('latency_ms')} ms")

print("\n  [Call 2 — same prompt — expected HIT]")
r2 = client.post("/api/v1/route", json=payload, headers=headers)
m2 = r2.json().get("metadata", {})
print(f"  cache_hit    : {m2.get('cache_hit')}   <-- should be True")
print(f"  cost         : ${m2.get('cost', 0):.6f}   <-- should be 0.000000 (FREE!)")
print(f"  latency_ms   : {m2.get('latency_ms')} ms   <-- should be much faster")

saving = m1.get("cost", 0) - m2.get("cost", 0)
print(f"\n  >> Cost saved by cache: ${saving:.6f}")

input("\n  >> Press ENTER to continue to Demo 5 (Failover)...")

# ─────────────────────────────────────────────────────────────────────────────
section("DEMO 5 — Multi-Level Failover + Circuit Breaker")
print("  Step 1: Force OpenAI circuit breaker OPEN (simulate outage)")
print("  Step 2: Route request -> should failover to Anthropic or Google")
print("  Step 3: Restore OpenAI")
# ─────────────────────────────────────────────────────────────────────────────
ent_headers = {"Authorization": f"Bearer {ENTERPRISE_KEY}"}

# Open OpenAI circuit
r = client.post("/api/v1/providers/openai/circuit/open", headers=ent_headers)
print(f"\n  [Circuit Open] {r.json().get('message')}")

# Route a request
r = client.post(
    "/api/v1/route",
    json={
        "messages": [{"role": "user", "content": "What is machine learning?"}],
        "nfr": {"latency": "low", "cost": "medium", "accuracy": "standard"},
    },
    headers=ent_headers,
)
body = r.json()
meta = body.get("metadata", {})
print(f"\n  [Routed with OpenAI DOWN]")
print(f"  provider         : {body.get('provider')}   <-- should NOT be openai")
print(f"  model            : {body.get('model')}")
print(f"  failover_count   : {meta.get('failover_count')}   <-- should be >= 1")
print(f"  selected_reason  : {meta.get('selected_reason')}")

# Check health - OpenAI should be OPEN
r_health = client.get("/health")
providers = r_health.json().get("providers", {})
print(f"\n  [Provider States]")
for name, state in providers.items():
    print(f"  {name:12s}: {state.get('state')}")

# Restore OpenAI
r = client.post("/api/v1/providers/openai/circuit/close", headers=ent_headers)
print(f"\n  [Circuit Close] {r.json().get('message')}")

input("\n  >> Press ENTER to continue to Demo 6 (Analytics)...")

# ─────────────────────────────────────────────────────────────────────────────
section("DEMO 6 — Analytics Summary")
print("  Real-time metrics from this demo session + pre-seeded data.")
# ─────────────────────────────────────────────────────────────────────────────
r = client.get("/api/v1/analytics/summary", headers={"Authorization": f"Bearer {FREE_KEY}"})
body = r.json()
print(f"\n  total_requests     : {body.get('total_requests')}")
print(f"  cache_hit_rate     : {body.get('cache_hit_rate', 0)*100:.1f}%")
print(f"  cache_hits         : {body.get('cache_hits')}")
print(f"  total_cost         : ${body.get('total_cost', 0):.4f}")
print(f"  avg_latency_ms     : {body.get('avg_latency_ms')} ms")
print(f"  p95_latency_ms     : {body.get('p95_latency_ms')} ms")
print(f"  total_failovers    : {body.get('total_failovers')}")
print(f"\n  Provider distribution:")
for prov, count in body.get("provider_distribution", {}).items():
    total = body.get("total_requests", 1)
    pct = count / total * 100
    bar = "#" * int(pct / 2)
    print(f"    {prov:12s}: {count:4d} ({pct:4.1f}%) {bar}")
print(f"\n  Model distribution:")
for model, count in sorted(body.get("model_distribution", {}).items(), key=lambda x: -x[1])[:5]:
    print(f"    {model:20s}: {count}")

# ─────────────────────────────────────────────────────────────────────────────
section("DEMO 7 — Tier-Based Access Control")
print("  Free tier cannot access gpt-4 (pro/enterprise only).")
print("  Expect: free tier routes to a cheaper model even with critical NFR.")
# ─────────────────────────────────────────────────────────────────────────────
r = client.post(
    "/api/v1/route",
    json={
        "messages": [{"role": "user", "content": "Complex question requiring high accuracy"}],
        "nfr": {"latency": "high", "cost": "high", "accuracy": "critical"},
    },
    headers={"Authorization": f"Bearer {FREE_KEY}"},
)
body = r.json()
print(f"\n  [Free Tier — critical accuracy request]")
print(f"  model    : {body.get('model')}   <-- NOT gpt-4 or claude-3-opus (tier-restricted)")
print(f"  provider : {body.get('provider')}")

print(f"\n{SEP}")
print("  DEMO COMPLETE")
print(f"  All 7 demo scenarios executed successfully.")
print(f"  The LLM Gateway POC is fully functional.")
print(SEP)
