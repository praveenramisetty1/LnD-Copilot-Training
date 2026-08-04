# src/api/routes/analytics.py
"""
Analytics and provider control endpoints.
GET  /api/v1/analytics/summary   — aggregated metrics
GET  /api/v1/analytics/recent    — last N request records
GET  /api/v1/analytics/cache     — semantic cache contents
POST /api/v1/providers/{p}/circuit/open  — force circuit breaker OPEN  (demo)
POST /api/v1/providers/{p}/circuit/close — force circuit breaker CLOSED (demo)
"""

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/analytics/summary")
async def analytics_summary(request: Request):
    """Aggregated metrics: cost, latency, cache hit rate, provider distribution."""
    return request.app.state.gateway.analytics.summary()


@router.get("/analytics/recent")
async def analytics_recent(request: Request, limit: int = 20):
    """Return the most recent N request records."""
    return {"records": request.app.state.gateway.analytics.recent(limit)}


@router.get("/analytics/cache")
async def cache_status(request: Request):
    """Return current semantic cache size and up to 20 recent entries."""
    gw = request.app.state.gateway
    return {
        "cache_size":        gw.cache.size(),
        "similarity_threshold": float(__import__("os").getenv("CACHE_SIMILARITY_THRESHOLD", "0.75")),
        "entries":           gw.cache.all_entries()[:20],
    }


@router.get("/analytics/providers")
async def provider_health(request: Request):
    """Return circuit breaker state for all providers."""
    return request.app.state.gateway.failover.get_health_status()


# ── Demo / testing controls ──────────────────────────────────────────────────

@router.post("/providers/{provider}/circuit/open")
async def open_circuit(provider: str, request: Request):
    """
    Force a provider's circuit breaker to OPEN state.
    Use this during demos to simulate a provider outage and trigger failover.
    """
    success = request.app.state.gateway.failover.force_open(provider)
    return {
        "success":  success,
        "provider": provider,
        "action":   "circuit_opened",
        "message":  f"Provider '{provider}' is now DOWN. Next requests will failover." if success
                    else f"Provider '{provider}' not found.",
    }


@router.post("/providers/{provider}/circuit/close")
async def close_circuit(provider: str, request: Request):
    """
    Force a provider's circuit breaker to CLOSED (healthy) state.
    Use this to recover a provider after a demo outage.
    """
    success = request.app.state.gateway.failover.force_close(provider)
    return {
        "success":  success,
        "provider": provider,
        "action":   "circuit_closed",
        "message":  f"Provider '{provider}' is now UP." if success
                    else f"Provider '{provider}' not found.",
    }
