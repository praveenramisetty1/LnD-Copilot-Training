# src/api/models/responses.py
"""Pydantic response models for the LLM Gateway POC."""

from pydantic import BaseModel
from typing import Any, Dict, Optional


class UsageStats(BaseModel):
    prompt_tokens:     int = 0
    completion_tokens: int = 0
    total_tokens:      int = 0


class ResponseMetadata(BaseModel):
    cache_hit:       bool
    latency_ms:      int
    cost:            float
    failover_count:  int
    selected_reason: str                        # cache_hit | nfr_match | failover
    nfr:             Dict[str, Any]  = {}
    nfr_score:       Optional[float] = None
    score_breakdown: Optional[Dict[str, Any]] = None


class RouteResponse(BaseModel):
    id:       str
    model:    str
    provider: str
    content:  str
    usage:    UsageStats
    metadata: ResponseMetadata
