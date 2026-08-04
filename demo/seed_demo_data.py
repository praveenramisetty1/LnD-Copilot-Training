#!/usr/bin/env python3
# demo/seed_demo_data.py
"""
Pre-seeds the local cache and analytics store with synthetic demo data.
Run BEFORE starting the gateway to get realistic dashboard metrics.

Usage:
    python demo/seed_demo_data.py

Output:
    data/cache.json      — 20 pre-warmed cache entries
    data/analytics.json  — 200 synthetic request records
"""

import json
import math
import os
import re
import sys
import time
import uuid
from pathlib import Path

# ── Make src/ importable from repo root ─────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))

CACHE_FILE     = "data/cache.json"
ANALYTICS_FILE = "data/analytics.json"
STOP_WORDS = {
    "a","an","the","is","it","in","on","at","to","for","of","and","or",
    "but","not","with","this","that","was","are","be","by","from","as",
}

# ── Helpers ──────────────────────────────────────────────────────────────────

def tokenize(text: str):
    tokens = re.findall(r"\b[a-z0-9]+\b", text.lower())
    return [t for t in tokens if t not in STOP_WORDS and len(t) > 1]

def term_freq(tokens):
    freq = {}
    for t in tokens:
        freq[t] = freq.get(t, 0) + 1
    total = len(tokens) or 1
    return {t: c / total for t, c in freq.items()}

# ── Seed data ────────────────────────────────────────────────────────────────

SEED_PROMPTS = [
    ("What is the capital of France?",          "gpt-3.5-turbo", "openai"),
    ("Explain machine learning in simple terms","claude-3-haiku", "anthropic"),
    ("Write a Python hello world program",      "gpt-3.5-turbo", "openai"),
    ("What is the speed of light?",             "gemini-flash",  "google"),
    ("Summarise the history of the internet",   "claude-3-sonnet","anthropic"),
    ("What is a REST API?",                     "gpt-3.5-turbo", "openai"),
    ("How does a neural network work?",         "gpt-4-turbo",   "openai"),
    ("What is Docker?",                         "gemini-pro",    "google"),
    ("Explain quantum computing",               "claude-3-opus", "anthropic"),
    ("What are SOLID principles?",              "gpt-4",         "openai"),
    ("How do I reverse a string in Python?",    "gpt-3.5-turbo", "openai"),
    ("What is Kubernetes?",                     "gemini-pro",    "google"),
    ("Explain the CAP theorem",                 "claude-3-sonnet","anthropic"),
    ("What is a microservice architecture?",    "gpt-4-turbo",   "openai"),
    ("How does TLS work?",                      "claude-3-haiku","anthropic"),
    ("What is semantic search?",                "gemini-pro",    "google"),
    ("Explain gradient descent",                "gpt-4",         "openai"),
    ("What is a vector database?",              "claude-3-opus", "anthropic"),
    ("How does Redis work?",                    "gpt-3.5-turbo", "openai"),
    ("What is a circuit breaker pattern?",      "gpt-4-turbo",   "openai"),
]

MODEL_COSTS = {
    "gpt-4":          0.030, "gpt-4-turbo":    0.010, "gpt-3.5-turbo":  0.001,
    "claude-3-opus":  0.015, "claude-3-sonnet":0.003, "claude-3-haiku": 0.0002,
    "gemini-pro":     0.0005,"gemini-flash":   0.0001,
}

MODEL_LATENCIES = {
    "gpt-4":2000,"gpt-4-turbo":1500,"gpt-3.5-turbo":800,
    "claude-3-opus":1800,"claude-3-sonnet":1200,"claude-3-haiku":600,
    "gemini-pro":900,"gemini-flash":400,
}

TIERS   = ["free","basic","pro","enterprise"]
NFR_COMBOS = [
    {"latency":"low",   "cost":"low",   "accuracy":"standard"},
    {"latency":"low",   "cost":"medium","accuracy":"high"},
    {"latency":"medium","cost":"low",   "accuracy":"standard"},
    {"latency":"high",  "cost":"low",   "accuracy":"critical"},
    {"latency":"medium","cost":"medium","accuracy":"standard"},
]


def seed_cache() -> list:
    now = time.time()
    entries = []
    for prompt, model, provider in SEED_PROMPTS:
        tokens  = tokenize(prompt)
        if not tokens:
            continue
        vec     = term_freq(tokens)
        p_toks  = len(prompt.split()) * 2
        c_toks  = 40
        cost    = round(((p_toks + c_toks) / 1000) * MODEL_COSTS.get(model, 0.001), 6)
        entries.append({
            "id":         str(uuid.uuid4()),
            "prompt":     prompt,
            "vec":        vec,
            "content":    f"[{provider.upper()}/{model}] Cached answer to: '{prompt}'",
            "model":      model,
            "provider":   provider,
            "usage":      {"prompt_tokens": p_toks, "completion_tokens": c_toks,
                           "total_tokens": p_toks + c_toks},
            "created_at": now - 3600,
            "expires_at": now + 86400 * 7,
            "hit_count":  0,
            "last_hit":   None,
        })
    return entries


def seed_analytics(cache_entries: list) -> list:
    import random
    random.seed(42)
    records   = []
    now       = time.time()
    from src.providers.registry import MODEL_CATALOG
    all_models= list(MODEL_COSTS.keys())

    for i in range(200):
        tier         = random.choice(TIERS)
        # 40 % chance of cache hit
        cache_hit    = random.random() < 0.40
        nfr          = random.choice(NFR_COMBOS)
        ts           = now - random.randint(0, 7 * 86400)

        if cache_hit:
            entry    = random.choice(cache_entries)
            model    = entry["model"]
            provider = entry["provider"]
            latency  = random.randint(10, 80)
            cost     = 0.0
        else:
            model    = random.choice(all_models)
            provider = MODEL_CATALOG.get(model, {}).get("provider", "openai")
            base_lat = MODEL_LATENCIES.get(model, 1000)
            latency  = int(base_lat * random.uniform(0.7, 1.4))
            p_toks   = random.randint(20, 200)
            c_toks   = random.randint(20, 300)
            cost     = round(((p_toks + c_toks) / 1000) * MODEL_COSTS.get(model, 0.001), 6)

        records.append({
            "request_id":     str(uuid.uuid4()),
            "timestamp":      ts,
            "model":          model,
            "provider":       provider,
            "tier":           tier,
            "latency_ms":     latency,
            "cost":           cost,
            "cache_hit":      cache_hit,
            "failover_count": random.choices([0, 0, 0, 1, 2], weights=[70,10,5,10,5])[0],
            "nfr":            nfr,
            "success":        random.random() > 0.02,
            "error":          None,
        })

    records.sort(key=lambda r: r["timestamp"])
    return records


def main():
    Path("data").mkdir(exist_ok=True)

    print("[...] Seeding semantic cache ...")
    cache_entries = seed_cache()
    with open(CACHE_FILE, "w") as f:
        json.dump({"entries": cache_entries}, f, indent=2)
    print(f"   [OK]  {len(cache_entries)} cache entries written -> {CACHE_FILE}")

    print("[...] Seeding analytics records ...")
    analytics_records = seed_analytics(cache_entries)
    with open(ANALYTICS_FILE, "w") as f:
        json.dump({"records": analytics_records}, f, indent=2)

    cache_hits  = sum(1 for r in analytics_records if r["cache_hit"])
    total_cost  = sum(r["cost"] for r in analytics_records)
    print(f"   [OK]  {len(analytics_records)} request records written -> {ANALYTICS_FILE}")
    print(f"   [STAT] Cache hit rate : {cache_hits}/{len(analytics_records)} "
          f"= {cache_hits/len(analytics_records)*100:.1f}%")
    print(f"   [STAT] Total cost     : ${total_cost:.4f}")
    print("\n[DONE] Demo data ready. Start the gateway and explore /docs\n")


if __name__ == "__main__":
    main()
