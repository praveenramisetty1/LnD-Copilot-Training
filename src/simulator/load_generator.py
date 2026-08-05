# src/simulator/load_generator.py
"""
Synthetic load generator — sends batches of requests to the running gateway.
Used for demo warm-up and manual load testing without Locust.

Usage:
    PYTHONPATH=. python src/simulator/load_generator.py --requests 50 --concurrency 5
"""

import argparse
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

GATEWAY_URL = "http://localhost:8000"

API_KEYS = {
    "free":       "free-key-001",
    "basic":      "basic-key-001",
    "pro":        "pro-key-001",
    "enterprise": "enterprise-key-001",
}

PROMPTS = [
    "What is the capital of France?",
    "Explain machine learning in simple terms",
    "Write a Python hello world program",
    "What is the speed of light?",
    "How does a neural network work?",
    "What is Docker and why use it?",
    "Explain the CAP theorem in distributed systems",
    "What is a REST API?",
    "How do I reverse a string in Python?",
    "What is a microservice architecture?",
    "What is semantic search?",
    "Explain gradient descent",
    "What is a vector database?",
    "How does Redis work?",
    "What is a circuit breaker pattern?",
]

NFR_COMBOS = [
    {"latency": "low",    "cost": "low",    "accuracy": "standard"},
    {"latency": "low",    "cost": "medium", "accuracy": "high"},
    {"latency": "medium", "cost": "low",    "accuracy": "standard"},
    {"latency": "high",   "cost": "low",    "accuracy": "critical"},
    {"latency": "medium", "cost": "medium", "accuracy": "standard"},
]


def _send_request(prompt: str, nfr: dict, tier: str) -> dict:
    api_key = API_KEYS.get(tier, "free-key-001")
    start = time.time()
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                f"{GATEWAY_URL}/api/v1/route",
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    "nfr": nfr,
                },
                headers={"Authorization": f"Bearer {api_key}"},
            )
            body    = resp.json()
            elapsed = int((time.time() - start) * 1000)
            if resp.status_code == 200:
                return {
                    "status":     200,
                    "model":      body.get("model"),
                    "provider":   body.get("provider"),
                    "cache_hit":  body.get("metadata", {}).get("cache_hit", False),
                    "cost":       body.get("metadata", {}).get("cost", 0),
                    "latency_ms": elapsed,
                }
            return {"status": resp.status_code, "error": body}
    except Exception as e:
        return {"status": 0, "error": str(e)}


def run(total: int = 20, concurrency: int = 3, tiers: list = None):
    tiers = tiers or ["free", "basic", "pro"]
    tasks = [
        (random.choice(PROMPTS), random.choice(NFR_COMBOS), random.choice(tiers))
        for _ in range(total)
    ]

    results   = []
    succeeded = 0
    cache_hits = 0
    total_cost = 0.0
    latencies  = []

    print(f"\n⚡  Sending {total} requests (concurrency={concurrency})…\n")
    start_all = time.time()

    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = {ex.submit(_send_request, *t): t for t in tasks}
        for i, future in enumerate(as_completed(futures), 1):
            r = future.result()
            results.append(r)
            if r.get("status") == 200:
                succeeded   += 1
                cache_hits  += 1 if r.get("cache_hit") else 0
                total_cost  += r.get("cost", 0)
                latencies.append(r.get("latency_ms", 0))
            dot = "✅" if r.get("status") == 200 else "❌"
            print(f"  {dot} [{i:>3}/{total}] "
                  f"{r.get('model','?'):20} "
                  f"{'HIT' if r.get('cache_hit') else 'MISS':4}  "
                  f"{r.get('latency_ms','?')}ms")

    elapsed_total = time.time() - start_all
    avg_lat = int(sum(latencies) / len(latencies)) if latencies else 0
    p95_lat = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0

    print(f"""
── Summary ──────────────────────────────────────────────
  Total requests  : {total}
  Succeeded       : {succeeded}
  Cache hits      : {cache_hits}  ({cache_hits/total*100:.1f}%)
  Total cost      : ${total_cost:.6f}
  Avg latency     : {avg_lat}ms
  P95 latency     : {p95_lat}ms
  Elapsed time    : {elapsed_total:.1f}s
  Throughput      : {total/elapsed_total:.1f} req/s
──────────────────────────────────────────────────────────
""")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LLM Gateway load generator")
    parser.add_argument("--requests",    type=int, default=20,  help="Total requests")
    parser.add_argument("--concurrency", type=int, default=3,   help="Concurrent workers")
    parser.add_argument("--tiers",       nargs="+",
                        default=["free", "basic", "pro"],
                        help="Tiers to mix (free basic pro enterprise)")
    args = parser.parse_args()
    run(args.requests, args.concurrency, args.tiers)
