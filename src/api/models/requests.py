# src/api/models/requests.py
"""Pydantic request models for the LLM Gateway POC."""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class Message(BaseModel):
    role: str      # system | user | assistant
    content: str


class RouteRequest(BaseModel):
    """
    Request body for POST /api/v1/route.

    NFR parameters can be supplied here OR via X-NFR-* request headers.
    Values in this body take precedence over headers.
    """
    messages:   List[Message]  = Field(..., min_length=1)
    nfr:        Optional[Dict[str, str]] = Field(
        default=None,
        description=(
            "NFR overrides. Keys: latency (low|medium|high), "
            "cost (low|medium|high), accuracy (standard|high|critical), "
            "model_preference (optional model name hint)."
        ),
        examples=[{"latency": "low", "cost": "low", "accuracy": "standard"}],
    )
    user_tier:  Optional[str]  = Field(
        default=None,
        description="Override tier from API key. One of: free | basic | pro | enterprise.",
    )
    request_id: Optional[str]  = Field(
        default=None,
        description="Optional idempotency / correlation ID.",
    )
    stream:     bool           = False
