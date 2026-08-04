# src/gateway/nfr_parser.py
"""
Parses NFR (Non-Functional Requirements) from request headers or body.
No external dependencies — pure Python validation.
"""

from dataclasses import dataclass
from typing import Optional
from fastapi import HTTPException

VALID_LATENCY  = {"low", "medium", "high"}
VALID_COST     = {"low", "medium", "high"}
VALID_ACCURACY = {"standard", "high", "critical"}

TIER_ORDER = {"free": 0, "basic": 1, "pro": 2, "enterprise": 3}
VALID_TIERS = set(TIER_ORDER.keys())


@dataclass
class NFRRequirements:
    latency: str           = "medium"    # low | medium | high
    cost: str              = "medium"    # low | medium | high
    accuracy: str          = "standard"  # standard | high | critical
    model_preference: Optional[str] = None

    def as_dict(self) -> dict:
        return {
            "latency":          self.latency,
            "cost":             self.cost,
            "accuracy":         self.accuracy,
            "model_preference": self.model_preference,
        }


def parse_nfr(
    latency:          str = "medium",
    cost:             str = "medium",
    accuracy:         str = "standard",
    model_preference: Optional[str] = None,
) -> NFRRequirements:
    """
    Validate and normalise NFR values.
    Raises HTTP 400 on invalid input.
    """
    latency  = latency.strip().lower()
    cost     = cost.strip().lower()
    accuracy = accuracy.strip().lower()

    if latency not in VALID_LATENCY:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid NFR latency '{latency}'. Must be one of: {sorted(VALID_LATENCY)}",
        )
    if cost not in VALID_COST:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid NFR cost '{cost}'. Must be one of: {sorted(VALID_COST)}",
        )
    if accuracy not in VALID_ACCURACY:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid NFR accuracy '{accuracy}'. Must be one of: {sorted(VALID_ACCURACY)}",
        )

    return NFRRequirements(
        latency=latency,
        cost=cost,
        accuracy=accuracy,
        model_preference=model_preference,
    )


def parse_nfr_from_headers(headers: dict) -> NFRRequirements:
    """Convenience wrapper — reads NFR values from HTTP request headers."""
    return parse_nfr(
        latency          = headers.get("x-nfr-latency",  "medium"),
        cost             = headers.get("x-nfr-cost",     "medium"),
        accuracy         = headers.get("x-nfr-accuracy", "standard"),
        model_preference = headers.get("x-model-preference"),
    )
