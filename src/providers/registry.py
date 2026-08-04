# src/providers/registry.py
"""
Provider registry — single source of truth for all model/provider metadata.
No external database required; everything lives in memory at startup.
"""

import os
from typing import Dict, List, Optional

from .base import BaseProvider
from .openai_simulator import OpenAISimulator, OPENAI_MODELS
from .anthropic_simulator import AnthropicSimulator, ANTHROPIC_MODELS
from .google_simulator import GoogleSimulator, GOOGLE_MODELS

# ── Model Catalog ────────────────────────────────────────────────────────────
# Each entry: model_name → {provider, family, cost_per_1k, avg_latency_ms,
#                           accuracy, tiers}
MODEL_CATALOG: Dict[str, dict] = {}

for name, cfg in OPENAI_MODELS.items():
    MODEL_CATALOG[name] = {
        "provider": "openai",
        "family": "gpt",
        "cost_per_1k": cfg["cost_per_1k"],
        "avg_latency_ms": cfg["latency_ms"],
        "accuracy": cfg["accuracy"],
        "tiers": cfg["tiers"],
    }

for name, cfg in ANTHROPIC_MODELS.items():
    MODEL_CATALOG[name] = {
        "provider": "anthropic",
        "family": "claude",
        "cost_per_1k": cfg["cost_per_1k"],
        "avg_latency_ms": cfg["latency_ms"],
        "accuracy": cfg["accuracy"],
        "tiers": cfg["tiers"],
    }

for name, cfg in GOOGLE_MODELS.items():
    MODEL_CATALOG[name] = {
        "provider": "google",
        "family": "gemini",
        "cost_per_1k": cfg["cost_per_1k"],
        "avg_latency_ms": cfg["latency_ms"],
        "accuracy": cfg["accuracy"],
        "tiers": cfg["tiers"],
    }

# ── Failover Chains ──────────────────────────────────────────────────────────
# For each model: ordered list of (model, provider) fallbacks
FAILOVER_CHAINS: Dict[str, List[Dict[str, str]]] = {
    "gpt-4": [
        {"model": "gpt-4",        "provider": "openai"},     # L1: same model
        {"model": "gpt-4-turbo",  "provider": "openai"},     # L3: same family
        {"model": "claude-3-opus","provider": "anthropic"},   # L4: diff family
        {"model": "gemini-pro",   "provider": "google"},      # L4: last resort
    ],
    "gpt-4-turbo": [
        {"model": "gpt-4-turbo",     "provider": "openai"},
        {"model": "gpt-4",           "provider": "openai"},
        {"model": "claude-3-sonnet", "provider": "anthropic"},
        {"model": "gemini-pro",      "provider": "google"},
    ],
    "gpt-3.5-turbo": [
        {"model": "gpt-3.5-turbo",  "provider": "openai"},
        {"model": "claude-3-haiku", "provider": "anthropic"},
        {"model": "gemini-flash",   "provider": "google"},
    ],
    "claude-3-opus": [
        {"model": "claude-3-opus",   "provider": "anthropic"},
        {"model": "claude-3-sonnet", "provider": "anthropic"},
        {"model": "gpt-4",           "provider": "openai"},
        {"model": "gemini-pro",      "provider": "google"},
    ],
    "claude-3-sonnet": [
        {"model": "claude-3-sonnet", "provider": "anthropic"},
        {"model": "claude-3-haiku",  "provider": "anthropic"},
        {"model": "gpt-4-turbo",     "provider": "openai"},
        {"model": "gemini-pro",      "provider": "google"},
    ],
    "claude-3-haiku": [
        {"model": "claude-3-haiku", "provider": "anthropic"},
        {"model": "gpt-3.5-turbo",  "provider": "openai"},
        {"model": "gemini-flash",   "provider": "google"},
    ],
    "gemini-pro": [
        {"model": "gemini-pro",      "provider": "google"},
        {"model": "gemini-flash",    "provider": "google"},
        {"model": "gpt-3.5-turbo",   "provider": "openai"},
        {"model": "claude-3-haiku",  "provider": "anthropic"},
    ],
    "gemini-flash": [
        {"model": "gemini-flash",   "provider": "google"},
        {"model": "gemini-pro",     "provider": "google"},
        {"model": "gpt-3.5-turbo",  "provider": "openai"},
        {"model": "claude-3-haiku", "provider": "anthropic"},
    ],
}


def build_providers() -> Dict[str, BaseProvider]:
    """Instantiate all provider simulators from env config."""
    return {
        "openai": OpenAISimulator(
            failure_rate=float(os.getenv("OPENAI_FAILURE_RATE", "0.05")),
            latency_multiplier=float(os.getenv("OPENAI_LATENCY_MULTIPLIER", "1.0")),
        ),
        "anthropic": AnthropicSimulator(
            failure_rate=float(os.getenv("ANTHROPIC_FAILURE_RATE", "0.03")),
            latency_multiplier=float(os.getenv("ANTHROPIC_LATENCY_MULTIPLIER", "1.0")),
        ),
        "google": GoogleSimulator(
            failure_rate=float(os.getenv("GOOGLE_FAILURE_RATE", "0.04")),
            latency_multiplier=float(os.getenv("GOOGLE_LATENCY_MULTIPLIER", "1.0")),
        ),
    }


def get_models_for_tier(tier: str) -> List[str]:
    """Return all models accessible to a given user tier."""
    return [name for name, cfg in MODEL_CATALOG.items() if tier in cfg["tiers"]]


def get_failover_chain(model: str) -> List[Dict[str, str]]:
    """Return the failover chain for a model, defaulting to gpt-3.5-turbo chain."""
    return FAILOVER_CHAINS.get(model, FAILOVER_CHAINS["gpt-3.5-turbo"])
