# src/api/middleware/auth.py
"""
API key authentication middleware.
Keys are loaded from the API_KEYS environment variable.
Format: "key1:tier1,key2:tier2,..."
No external database required.
"""

import os
import time
from collections import defaultdict
from threading import Lock
from typing import Dict, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# ── Brute-force protection (in-memory, no Redis required) ─────────────────────
MAX_FAILURES     = int(os.getenv("AUTH_MAX_FAILURES",     "10"))
LOCKOUT_SECONDS  = int(os.getenv("AUTH_LOCKOUT_SECONDS",  "300"))  # 5 min

_bf_lock    = Lock()
_bf_records: dict = defaultdict(lambda: {"failures": 0, "locked_until": 0.0})


def _is_locked(ip: str) -> Tuple[bool, int]:
    """Return (locked, retry_after_seconds)."""
    now = time.time()
    with _bf_lock:
        rec = _bf_records[ip]
        if rec["locked_until"] > now:
            return True, int(rec["locked_until"] - now)
        return False, 0


def _record_failure(ip: str) -> None:
    now = time.time()
    with _bf_lock:
        rec = _bf_records[ip]
        rec["failures"] += 1
        if rec["failures"] >= MAX_FAILURES:
            rec["locked_until"] = now + LOCKOUT_SECONDS
            rec["failures"]     = 0   # reset counter after lockout


def _record_success(ip: str) -> None:
    with _bf_lock:
        _bf_records[ip] = {"failures": 0, "locked_until": 0.0}

# Routes that bypass authentication
PUBLIC_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}


def _load_api_keys() -> Dict[str, str]:
    """Parse API_KEYS env var into a {api_key: tier} dict."""
    raw = os.getenv(
        "API_KEYS",
        "free-key-001:free,basic-key-001:basic,pro-key-001:pro,enterprise-key-001:enterprise",
    )
    result: Dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if ":" in pair:
            key, tier = pair.split(":", 1)
            result[key.strip()] = tier.strip()
    return result


API_KEY_MAP: Dict[str, str] = _load_api_keys()


class AuthMiddleware(BaseHTTPMiddleware):
    """Validates Bearer API key, enforces brute-force lockout, sets request.state.tier."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path in PUBLIC_PATHS:
            request.state.tier = "free"
            return await call_next(request)

        # ── Brute-force check (keyed on client IP) ────────────────────────
        client_ip = request.client.host if request.client else "unknown"
        locked, retry_after = _is_locked(client_ip)
        if locked:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": (
                        f"Too many failed authentication attempts. "
                        f"Try again in {retry_after}s."
                    ),
                    "retry_after_seconds": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            _record_failure(client_ip)
            return JSONResponse(
                status_code=401,
                content={
                    "detail": (
                        "Missing API key. Add header: Authorization: Bearer {api_key}. "
                        "Demo keys: free-key-001, basic-key-001, pro-key-001, enterprise-key-001"
                    )
                },
            )

        api_key = auth_header[7:].strip()
        tier    = API_KEY_MAP.get(api_key)

        if tier is None:
            _record_failure(client_ip)
            return JSONResponse(
                status_code=401,
                content={
                    "detail": (
                        f"Invalid API key. "
                        "Demo keys: free-key-001 | basic-key-001 | pro-key-001 | enterprise-key-001"
                    )
                },
            )

        _record_success(client_ip)   # reset failure counter on success
        request.state.api_key = api_key
        request.state.tier    = tier
        return await call_next(request)
