# src/gateway/router.py
"""
Main gateway orchestrator.
Flow: NFR parse → cache check → model select → failover dispatch → cache store → analytics
"""

import time
import uuid
from typing import Dict, List, Optional

from src.gateway.nfr_parser import NFRRequirements
from src.gateway.model_selector import select_model
from src.gateway.failover import FailoverManager
from src.cache.semantic_cache import SemanticCache
from src.analytics.collector import AnalyticsCollector
from src.providers.registry import build_providers


class GatewayRouter:
    """Instantiated once at app startup and shared via FastAPI app state."""

    def __init__(self):
        self.providers  = build_providers()
        self.failover   = FailoverManager(self.providers)
        self.cache      = SemanticCache()
        self.analytics  = AnalyticsCollector()

    # ── Main entry point ─────────────────────────────────────────────────────

    def route(
        self,
        messages:   List[Dict[str, str]],
        nfr:        NFRRequirements,
        tier:       str,
        request_id: Optional[str] = None,
    ) -> dict:
        request_id = request_id or str(uuid.uuid4())
        started_at = time.time()

        # 1. Semantic cache lookup
        user_prompt  = self._extract_user_prompt(messages)
        cache_result = self.cache.lookup(user_prompt)

        if cache_result:
            latency_ms = int((time.time() - started_at) * 1000)
            self.analytics.record(
                request_id=request_id, model=cache_result["model"],
                provider=cache_result["provider"], tier=tier,
                latency_ms=latency_ms, cost=0.0, cache_hit=True,
                failover_count=0, nfr=nfr.as_dict(), success=True,
            )
            return {
                "id": request_id,
                "model":    cache_result["model"],
                "provider": cache_result["provider"],
                "content":  cache_result["content"],
                "usage":    cache_result.get("usage", {}),
                "metadata": {
                    "cache_hit": True, "latency_ms": latency_ms,
                    "cost": 0.0, "failover_count": 0,
                    "selected_reason": "cache_hit", "nfr": nfr.as_dict(),
                },
            }

        # 2. Model selection
        available = self.failover.get_available_providers()
        model, provider, score, breakdown = select_model(nfr, tier, available)
        if not model:
            raise RuntimeError(
                "No models available for the requested tier and NFR combination."
            )

        # 3. Provider dispatch with multi-level failover
        response, failover_count = self.failover.execute_with_failover(model, messages)
        if not response.success:
            raise RuntimeError(response.error or "All providers failed.")

        latency_ms = int((time.time() - started_at) * 1000)

        # 4. Cache the successful response
        usage = {
            "prompt_tokens":     response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "total_tokens":      response.prompt_tokens + response.completion_tokens,
        }
        self.cache.store(
            prompt=user_prompt, content=response.content,
            model=response.model, provider=response.provider, usage=usage,
        )

        # 5. Record analytics
        self.analytics.record(
            request_id=request_id, model=response.model,
            provider=response.provider, tier=tier,
            latency_ms=latency_ms, cost=response.cost,
            cache_hit=False, failover_count=failover_count,
            nfr=nfr.as_dict(), success=True,
        )

        return {
            "id":       request_id,
            "model":    response.model,
            "provider": response.provider,
            "content":  response.content,
            "usage":    usage,
            "metadata": {
                "cache_hit":       False,
                "latency_ms":      latency_ms,
                "cost":            response.cost,
                "failover_count":  failover_count,
                "selected_reason": "nfr_match" if failover_count == 0 else "failover",
                "nfr_score":       score,
                "score_breakdown": breakdown,
                "nfr":             nfr.as_dict(),
            },
        }

    # ── Health / status ───────────────────────────────────────────────────────

    def health(self) -> dict:
        return {
            "providers":      self.failover.get_health_status(),
            "cache_size":     self.cache.size(),
            "total_requests": self.analytics.total_requests(),
        }

    # ── Private ───────────────────────────────────────────────────────────────

    def _extract_user_prompt(self, messages: List[Dict[str, str]]) -> str:
        for m in reversed(messages):
            if m.get("role") == "user":
                return m.get("content", "")
        return " ".join(m.get("content", "") for m in messages)
