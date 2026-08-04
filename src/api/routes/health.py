# src/api/routes/health.py
"""GET /health — Gateway health check with provider circuit breaker status."""

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health_check(request: Request):
    """Returns gateway status, provider health, cache size, and total requests."""
    gateway = getattr(request.app.state, "gateway", None)
    if gateway is None:
        return {"status": "starting", "version": "1.0.0"}

    health = gateway.health()
    return {
        "status":         "ok",
        "version":        "1.0.0",
        "cache_size":     health["cache_size"],
        "total_requests": health["total_requests"],
        "providers":      health["providers"],
    }
