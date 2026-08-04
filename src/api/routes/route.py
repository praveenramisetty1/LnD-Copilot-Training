# src/api/routes/route.py
"""
POST /api/v1/route — Main LLM Gateway routing endpoint.
Accepts messages + NFR parameters, returns routed LLM response.
"""

from fastapi import APIRouter, HTTPException, Request

from src.api.models.requests import RouteRequest
from src.api.models.responses import RouteResponse
from src.gateway.nfr_parser import parse_nfr

router = APIRouter()


@router.post("/route", response_model=RouteResponse)
async def route_request(body: RouteRequest, request: Request):
    """
    Route an LLM request through the gateway.

    NFR parameters can be supplied in the request body (nfr field)
    OR via X-NFR-* headers. Body values take precedence.

    The gateway will:
    1. Check semantic cache for a similar prompt
    2. Select the best model based on NFR + user tier
    3. Dispatch to the selected provider with failover
    4. Return the response with full routing metadata
    """
    gateway = request.app.state.gateway

    # Resolve NFR — body takes precedence over headers
    nfr_body = body.nfr or {}
    nfr = parse_nfr(
        latency          = nfr_body.get("latency")  or request.headers.get("x-nfr-latency",  "medium"),
        cost             = nfr_body.get("cost")     or request.headers.get("x-nfr-cost",     "medium"),
        accuracy         = nfr_body.get("accuracy") or request.headers.get("x-nfr-accuracy", "standard"),
        model_preference = nfr_body.get("model_preference") or request.headers.get("x-model-preference"),
    )

    # Resolve tier — body takes precedence over request.state (set by auth middleware)
    tier = body.user_tier or getattr(request.state, "tier", "free")

    # Convert Pydantic messages to plain dicts
    messages = [{"role": m.role, "content": m.content} for m in body.messages]

    try:
        result = gateway.route(
            messages   = messages,
            nfr        = nfr,
            tier       = tier,
            request_id = body.request_id,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return RouteResponse(**result)
