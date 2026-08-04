# src/api/middleware/rate_limit.py
"""
In-memory token bucket rate limiter — tier-based throttling.
No Redis required for POC. Uses a simple dict + timestamp approach.

Tier limits (requests per minute):
  free       →    10 / min
  basic      →   100 / min
  pro        →   500 / min
  enterprise → 5,000 / min
"""

import time
from collections import defaultdict
from typing import Dict, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# ── Tier configuration ────────────────────────────────────────────────────────

TIER_LIMITS: Dict[str, int] = {
    "free":       10,
    "basic":      100,
    "pro":        500,
    "enterprise": 5_000,
}

WINDOW_SECONDS = 60   # rolling window size

# Routes that skip rate limiting
EXEMPT_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}


# ── Token bucket store (in-memory) ────────────────────────────────────────────
# Structure: {user_key: (request_count, window_start_timestamp)}

_buckets: Dict[str, Tuple[int, float]] = defaultdict(lambda: (0, time.time()))


def _check_rate_limit(user_key: str, tier: str) -> Tuple[bool, int, int]:
    """
    Check whether the request is within quota.

    Returns:
        (allowed: bool, remaining: int, retry_after_seconds: int)
    """
    limit      = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
    now        = time.time()
    count, win_start = _buckets[user_key]

    # New window?
    if now - win_start >= WINDOW_SECONDS:
        _buckets[user_key] = (1, now)
        return True, limit - 1, 0

    if count < limit:
        _buckets[user_key] = (count + 1, win_start)
        return True, limit - count - 1, 0

    retry_after = int(WINDOW_SECONDS - (now - win_start)) + 1
    return False, 0, retry_after


# ── Middleware ────────────────────────────────────────────────────────────────

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Enforces per-user, per-tier token bucket rate limiting.
    Must be added AFTER AuthMiddleware so request.state.tier is available.
    """

    async def dispatch(self, request: Request, call_next):
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        tier     = getattr(request.state, "tier",    "free")
        api_key  = getattr(request.state, "api_key", request.client.host if request.client else "anon")
        user_key = f"{api_key}:{tier}"

        allowed, remaining, retry_after = _check_rate_limit(user_key, tier)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": (
                        f"Rate limit exceeded for tier '{tier}'. "
                        f"Limit: {TIER_LIMITS.get(tier, 10)} req/{WINDOW_SECONDS}s. "
                        f"Retry after {retry_after}s."
                    ),
                    "tier":         tier,
                    "limit":        TIER_LIMITS.get(tier, 10),
                    "window_s":     WINDOW_SECONDS,
                    "retry_after":  retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"]     = str(TIER_LIMITS.get(tier, 10))
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"]    = str(WINDOW_SECONDS)
        return response
