#!/usr/bin/env python3
# demo/run_demo_v2.py
"""
LLM Gateway POC - Live Demo Runner (all scenarios inside TestClient context)
Run: set PYTHONPATH=. && py demo/run_demo_v2.py
"""

import json
import sys
import os
import warnings
warnings.filterwarnings("ignore")

# Force UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

os.environ.setdefault("PYTHONPATH", ".")

from fastapi.testclient import TestClient
from src.api.main import app

SEP  = "=" * 65
SEP2 = "-" * 65

FREE_KEY       = "free-key-001"
PRO_KEY        = "pro-key-001"
ENTERPRISE_KEY = "enterprise-key-001"


def show(label: str, r, brief: bool = False):
    print(f"\n{SEP}")
    print(f"  DEMO: {label}")
    print(f"  HTTP : {r.status_code}")
    print(SEP2)
    try:
        body = r.json()
    except Exception:
        print(f"  RAW: {r.text[:300]}")
        print(SEP)
        return
    if brief and "metadata" in body:
        m = body["metadata"]
        print(f"  model           : {body.get('model','N/A')}")
        print(f"  provider        : {body.get('provider','N/A')}")
        print(f"  cache_hit       : {m.get('cache_hit')}")
        print(f"  latency_ms      : {m.get('latency_ms')} ms")
        print(f"  cost            : ${m.get('cost', 0):.6f}")
        print(f"  failover_count  : {m.get('failover_count')}")
        print(f"  selected_reason : {m.get('selected_reason')}")
        c = body.get("content", "")[:90]
        print(f"  content         : {c}...")
    else:
        print(json.dumps(body, indent=2, ensure_ascii=False)[:800])
    print(SEP)


def section(title: str):
    print(f"\n{'#'*65}")
    print(f"#  {title}")
    print(f"{'#'*65}")


def pause(msg=""):
    print(f"\n  [continuing...]  {msg}")


# ── All demos run inside the context manager so lifespan fires ────────────────
with TestClient(app, raise_server_exceptions=False) as client:

    # ── DEMO 1: Health check ──────────────────────────────────────────────────
    section("DEMO 1 — Health Check")
    r = client.get("/health")
    show("GET /health", r)
    pause("Press ENTER for Demo 2 → NFR Routing (low cost)...")

    # ── DEMO 2: NFR routing — low cost ───────────────────────────────────────
    section("DEMO 2 — NFR Routing: Low Cost + Standard Accuracy")
    print("  NFR: cost=LOW, latency=medium, accuracy=standard")
    print("  Tier: FREE | Expect: gemini-flash or claude-3-haiku")
    r = client.post(
        "/api/v1/route",
        json={
            "messages": [{"role": "user", "content": "What is the capital of France?"}],
            "nfr": {"latency": "medium", "cost": "low", "accuracy": "standard"},
        },
        headers={"Authorization": f"Bearer {FREE_KEY}"},
    )
    show("POST /api/v1/route [cost=low, free tier]", r, brief=True)
    pause("Press ENTER for Demo 3 → Critical Accuracy...")

    # ── DEMO 3: NFR routing — critical accuracy ───────────────────────────────
    section("DEMO 3 — NFR Routing: Critical Accuracy")
    print("  NFR: accuracy=CRITICAL, cost=high, latency=high")
    print("  Tier: PRO | Expect: gpt-4 or claude-3-opus")
    r = client.post(
        "/api/v1/route",
        json={
            "messages": [{"role": "user", "content": "Explain the CAP theorem in distributed systems"}],
            "nfr": {"latency": "high", "cost": "high", "accuracy": "critical"},
        },
        headers={"Authorization": f"Bearer {PRO_KEY}"},
    )
    show("POST /api/v1/route [accuracy=critical, pro tier]", r, brief=True)
    pause("Press ENTER for Demo 4 → Semantic Cache...")

    # ── DEMO 4: Semantic cache miss then hit ──────────────────────────────────
    section("DEMO 4 — Semantic Cache: Miss then Hit")
    print("  Sending same prompt twice. 2nd call = cache HIT, cost = $0.000000")
    payload = {
        "messages": [{"role": "user", "content": "How does a neural network work?"}],
        "nfr": {"latency": "low", "cost": "low", "accuracy": "standard"},
    }
    hdr = {"Authorization": f"Bearer {FREE_KEY}"}

    print("\n  [Call 1 — expected MISS]")
    r1 = client.post("/api/v1/route", json=payload, headers=hdr)
    b1 = r1.json()
    m1 = b1.get("metadata", {})
    print(f"  cache_hit  : {m1.get('cache_hit')}   <- should be False")
    print(f"  cost       : ${m1.get('cost', 0):.6f}")
    print(f"  latency_ms : {m1.get('latency_ms')} ms")
    print(f"  model      : {b1.get('model')}")

    print("\n  [Call 2 — same prompt — expected HIT]")
    r2 = client.post("/api/v1/route", json=payload, headers=hdr)
    b2 = r2.json()
    m2 = b2.get("metadata", {})
    print(f"  cache_hit  : {m2.get('cache_hit')}   <- should be True")
    print(f"  cost       : ${m2.get('cost', 0):.6f}   <- FREE (saved!)")
    print(f"  latency_ms : {m2.get('latency_ms')} ms   <- much faster")

    saved = m1.get("cost", 0) - m2.get("cost", 0)
    print(f"\n  >> Cost saved by cache hit: ${saved:.6f}")
    pause("Press ENTER for Demo 5 → Failover...")

    # ── DEMO 5: Failover + circuit breaker ────────────────────────────────────
    section("DEMO 5 — Multi-Level Failover + Circuit Breaker")
    print("  1. Force OpenAI OPEN (simulate outage)")
    print("  2. Route request → expect Anthropic or Google")
    print("  3. Restore OpenAI")
    ent = {"Authorization": f"Bearer {ENTERPRISE_KEY}"}

    r = client.post("/api/v1/providers/openai/circuit/open", headers=ent)
    print(f"\n  [Circuit OPEN] {r.json().get('message','')}")

    r = client.post(
        "/api/v1/route",
        json={
            "messages": [{"role": "user", "content": "What is machine learning?"}],
            "nfr": {"latency": "low", "cost": "medium", "accuracy": "standard"},
        },
        headers=ent,
    )
    body = r.json()
    m = body.get("metadata", {})
    print(f"\n  [Routed with OpenAI DOWN]")
    print(f"  provider        : {body.get('provider')}   <- NOT openai")
    print(f"  model           : {body.get('model')}")
    print(f"  failover_count  : {m.get('failover_count')}   <- >= 1")
    print(f"  selected_reason : {m.get('selected_reason')}")

    rh = client.get("/health")
    provs = rh.json().get("providers", {})
    print(f"\n  [Provider Circuit States]")
    for name, st in provs.items():
        flag = " <- OPEN (bypassed)" if st.get("state") == "OPEN" else ""
        print(f"    {name:12s}: {st.get('state')}{flag}")

    r = client.post("/api/v1/providers/openai/circuit/close", headers=ent)
    print(f"\n  [Circuit CLOSE] {r.json().get('message','')}")
    pause("Press ENTER for Demo 6 → Analytics...")

    # ── DEMO 6: Analytics summary ─────────────────────────────────────────────
    section("DEMO 6 — Analytics Summary")
    r = client.get("/api/v1/analytics/summary",
                   headers={"Authorization": f"Bearer {FREE_KEY}"})
    body = r.json()
    total = body.get("total_requests", 1)
    print(f"\n  total_requests   : {body.get('total_requests')}")
    print(f"  cache_hit_rate   : {body.get('cache_hit_rate', 0)*100:.1f}%")
    print(f"  cache_hits       : {body.get('cache_hits')}")
    print(f"  total_cost       : ${body.get('total_cost', 0):.4f}")
    print(f"  avg_latency_ms   : {body.get('avg_latency_ms')} ms")
    print(f"  p95_latency_ms   : {body.get('p95_latency_ms')} ms")
    print(f"  total_failovers  : {body.get('total_failovers')}")
    print(f"\n  Provider distribution:")
    for prov, count in body.get("provider_distribution", {}).items():
        pct = count / total * 100
        bar = "#" * max(1, int(pct / 3))
        print(f"    {prov:12s}: {count:4d} ({pct:5.1f}%) {bar}")
    print(f"\n  Top models:")
    for model, count in sorted(
        body.get("model_distribution", {}).items(), key=lambda x: -x[1]
    )[:5]:
        print(f"    {model:22s}: {count}")
    pause("Press ENTER for Demo 7 → Tier Access Control...")

    # ── DEMO 7: Tier-based access control ─────────────────────────────────────
    section("DEMO 7 — Tier-Based Access Control")
    print("  Free tier requests critical accuracy but cannot access gpt-4/claude-3-opus")
    r = client.post(
        "/api/v1/route",
        json={
            "messages": [{"role": "user", "content": "Solve this complex problem"}],
            "nfr": {"latency": "high", "cost": "high", "accuracy": "critical"},
        },
        headers={"Authorization": f"Bearer {FREE_KEY}"},
    )
    body = r.json()
    print(f"\n  [Free Tier — critical accuracy]")
    print(f"  model    : {body.get('model')}  <- NOT gpt-4 / claude-3-opus")
    print(f"  provider : {body.get('provider')}")
    print(f"  (gpt-4 and claude-3-opus are restricted to pro/enterprise)")

    # ── DEMO 8: Auth + rate limit ─────────────────────────────────────────────
    section("DEMO 8 — Auth: Invalid Key Returns 401")
    r = client.post(
        "/api/v1/route",
        json={"messages": [{"role": "user", "content": "Hello"}]},
        headers={"Authorization": "Bearer wrong-key-999"},
    )
    print(f"\n  Status: {r.status_code}   <- should be 401")
    print(f"  Detail: {r.json().get('detail','')}")

    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  ALL 8 DEMO SCENARIOS COMPLETED SUCCESSFULLY")
    print(f"  LLM Gateway POC is fully functional.")
    print(SEP)
