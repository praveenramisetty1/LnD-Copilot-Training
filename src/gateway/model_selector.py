# src/gateway/model_selector.py
"""
NFR-based model scoring and selection algorithm.
Weights: Cost 40%, Latency 30%, Accuracy 30% — dynamically adjusted by NFR headers.
No external dependencies.
"""

from typing import Dict, List, Optional, Tuple

from src.providers.registry import MODEL_CATALOG

from .nfr_parser import NFRRequirements

# How each NFR value multiplies the base weight for that dimension
# "low latency needed" → latency matters MORE → higher multiplier
NFR_MULTIPLIERS: Dict[str, Dict[str, float]] = {
    "latency":  {"low": 2.0, "medium": 1.0, "high": 0.5},
    "cost":     {"low": 2.0, "medium": 1.0, "high": 0.5},
    "accuracy": {"critical": 2.0, "high": 1.5, "standard": 1.0},
}

BASE_WEIGHTS = {"cost": 0.40, "latency": 0.30, "accuracy": 0.30}


def _compute_weights(nfr: NFRRequirements) -> Dict[str, float]:
    """Apply NFR multipliers to base weights, then normalise to sum = 1.0."""
    w = {
        "cost":     BASE_WEIGHTS["cost"]     * NFR_MULTIPLIERS["cost"][nfr.cost],
        "latency":  BASE_WEIGHTS["latency"]  * NFR_MULTIPLIERS["latency"][nfr.latency],
        "accuracy": BASE_WEIGHTS["accuracy"] * NFR_MULTIPLIERS["accuracy"][nfr.accuracy],
    }
    total = sum(w.values())
    return {k: round(v / total, 4) for k, v in w.items()}


def select_model(
    nfr:                NFRRequirements,
    tier:               str,
    available_providers: List[str],
) -> Tuple[Optional[str], Optional[str], float, dict]:
    """
    Score every model accessible to `tier` and served by `available_providers`.
    Returns (model_name, provider_name, best_score, score_breakdown).
    Returns (None, None, 0.0, {}) when no candidates exist.
    """
    candidates = {
        name: cfg
        for name, cfg in MODEL_CATALOG.items()
        if tier in cfg["tiers"] and cfg["provider"] in available_providers
    }

    if not candidates:
        return None, None, 0.0, {}

    # -- Accuracy floor: critical/high NFR must exclude low-accuracy models --------
    # Rationale: if a caller declares accuracy=critical, routing to a low-accuracy
    # model defeats the purpose even if it scores better on cost/latency dimensions.
    ACCURACY_FLOOR = {"critical": 0.90, "high": 0.80, "standard": 0.0}
    floor = ACCURACY_FLOOR.get(nfr.accuracy, 0.0)
    filtered = {k: v for k, v in candidates.items() if v["accuracy"] >= floor}
    # Fall back to full pool only if the floor eliminates every candidate
    candidates = filtered if filtered else candidates
    # ------------------------------------------------------------------------------

    weights = _compute_weights(nfr)

    # Normalisation ranges across the candidate pool
    all_costs     = [c["cost_per_1k"]    for c in candidates.values()]
    all_latencies = [c["avg_latency_ms"] for c in candidates.values()]
    max_cost      = max(all_costs)     or 1e-9
    max_latency   = max(all_latencies) or 1e-9

    best_model    = None
    best_provider = None
    best_score    = -1.0
    best_breakdown: dict = {}

    for model_name, cfg in candidates.items():
        # Higher score = better on each dimension
        cost_score     = 1.0 - (cfg["cost_per_1k"]    / max_cost)
        latency_score  = 1.0 - (cfg["avg_latency_ms"] / max_latency)
        accuracy_score = cfg["accuracy"]                               # already 0-1

        # Optional preference boost (does not override NFR scoring)
        preference_boost = 0.0
        if nfr.model_preference:
            if nfr.model_preference.lower() in model_name.lower():
                preference_boost = 0.05

        final_score = (
            cost_score     * weights["cost"]
            + latency_score  * weights["latency"]
            + accuracy_score * weights["accuracy"]
            + preference_boost
        )

        if final_score > best_score:
            best_score    = final_score
            best_model    = model_name
            best_provider = cfg["provider"]
            best_breakdown = {
                "cost_score":     round(cost_score,     4),
                "latency_score":  round(latency_score,  4),
                "accuracy_score": round(accuracy_score, 4),
                "weights":        weights,
                "preference_boost": preference_boost,
                "final_score":    round(final_score,    4),
            }

    return best_model, best_provider, round(best_score, 4), best_breakdown


def rank_models(
    nfr:                NFRRequirements,
    tier:               str,
    available_providers: List[str],
) -> List[Tuple[str, str, float]]:
    """Return all candidates sorted by score descending — used for failover ordering."""
    candidates = {
        name: cfg
        for name, cfg in MODEL_CATALOG.items()
        if tier in cfg["tiers"] and cfg["provider"] in available_providers
    }
    if not candidates:
        return []

    # Apply same accuracy floor as select_model for consistency
    ACCURACY_FLOOR = {"critical": 0.90, "high": 0.80, "standard": 0.0}
    floor = ACCURACY_FLOOR.get(nfr.accuracy, 0.0)
    filtered = {k: v for k, v in candidates.items() if v["accuracy"] >= floor}
    candidates = filtered if filtered else candidates

    weights   = _compute_weights(nfr)
    all_costs     = [c["cost_per_1k"]    for c in candidates.values()]
    all_latencies = [c["avg_latency_ms"] for c in candidates.values()]
    max_cost      = max(all_costs)     or 1e-9
    max_latency   = max(all_latencies) or 1e-9

    scored = []
    for model_name, cfg in candidates.items():
        cs = 1.0 - (cfg["cost_per_1k"]    / max_cost)
        ls = 1.0 - (cfg["avg_latency_ms"] / max_latency)
        acc = cfg["accuracy"]
        score = cs * weights["cost"] + ls * weights["latency"] + acc * weights["accuracy"]
        scored.append((model_name, cfg["provider"], round(score, 4)))

    scored.sort(key=lambda x: x[2], reverse=True)
    return scored
