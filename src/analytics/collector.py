# src/analytics/collector.py
"""
Analytics collector — records every gateway request to data/analytics.json.
No external database required. Pure Python + local JSON file.
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional

ANALYTICS_FILE = os.getenv("ANALYTICS_FILE", "data/analytics.json")
MAX_RECORDS    = 10_000   # Rotate after 10K records to keep file manageable


class AnalyticsCollector:
    """Append-only request log stored in a local JSON file."""

    def __init__(self):
        self._records: List[dict] = []
        self._load()

    # ── Write ─────────────────────────────────────────────────────────────────

    def record(
        self,
        request_id:     str,
        model:          str,
        provider:       str,
        tier:           str,
        latency_ms:     int,
        cost:           float,
        cache_hit:      bool,
        failover_count: int,
        nfr:            dict,
        success:        bool,
        error:          Optional[str] = None,
    ) -> None:
        entry = {
            "request_id":     request_id,
            "timestamp":      time.time(),
            "model":          model,
            "provider":       provider,
            "tier":           tier,
            "latency_ms":     latency_ms,
            "cost":           cost,
            "cache_hit":      cache_hit,
            "failover_count": failover_count,
            "nfr":            nfr,
            "success":        success,
            "error":          error,
        }
        self._records.append(entry)

        # Rotate if too large
        if len(self._records) > MAX_RECORDS:
            self._records = self._records[-MAX_RECORDS:]

        self._save()

    # ── Read ──────────────────────────────────────────────────────────────────

    def total_requests(self) -> int:
        return len(self._records)

    def summary(self) -> dict:
        """Return aggregated metrics for the analytics endpoint."""
        if not self._records:
            return self._empty_summary()

        total      = len(self._records)
        successful = [r for r in self._records if r["success"]]
        cache_hits = [r for r in self._records if r["cache_hit"]]
        costs      = [r["cost"] for r in successful]
        latencies  = [r["latency_ms"] for r in successful]

        # Provider distribution
        provider_counts: Dict[str, int] = {}
        for r in self._records:
            provider_counts[r["provider"]] = provider_counts.get(r["provider"], 0) + 1

        # Model distribution
        model_counts: Dict[str, int] = {}
        for r in self._records:
            model_counts[r["model"]] = model_counts.get(r["model"], 0) + 1

        # Tier distribution
        tier_counts: Dict[str, int] = {}
        for r in self._records:
            tier_counts[r["tier"]] = tier_counts.get(r["tier"], 0) + 1

        p95_latency = self._percentile(latencies, 95) if latencies else 0

        return {
            "total_requests":       total,
            "successful_requests":  len(successful),
            "error_rate":           round(1 - len(successful) / total, 4) if total else 0,
            "cache_hit_rate":       round(len(cache_hits) / total, 4) if total else 0,
            "cache_hits":           len(cache_hits),
            "total_cost":           round(sum(costs), 6),
            "avg_cost_per_request": round(sum(costs) / len(costs), 6) if costs else 0,
            "avg_latency_ms":       round(sum(latencies) / len(latencies)) if latencies else 0,
            "p95_latency_ms":       p95_latency,
            "provider_distribution":provider_counts,
            "model_distribution":   model_counts,
            "tier_distribution":    tier_counts,
            "total_failovers":      sum(r["failover_count"] for r in self._records),
        }

    def recent(self, limit: int = 50) -> List[dict]:
        """Return the most recent N records."""
        return list(reversed(self._records[-limit:]))

    def get_all(self) -> List[dict]:
        return self._records

    # ── Persistence ───────────────────────────────────────────────────────────

    def _save(self) -> None:
        Path(ANALYTICS_FILE).parent.mkdir(parents=True, exist_ok=True)
        with open(ANALYTICS_FILE, "w") as f:
            json.dump({"records": self._records}, f, indent=2)

    def _load(self) -> None:
        if not Path(ANALYTICS_FILE).exists():
            return
        try:
            with open(ANALYTICS_FILE) as f:
                data = json.load(f)
            self._records = data.get("records", [])
        except (json.JSONDecodeError, KeyError):
            self._records = []

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _percentile(data: List[float], pct: int) -> float:
        if not data:
            return 0.0
        sorted_data = sorted(data)
        idx = int(len(sorted_data) * pct / 100)
        return sorted_data[min(idx, len(sorted_data) - 1)]

    @staticmethod
    def _empty_summary() -> dict:
        return {
            "total_requests": 0, "successful_requests": 0,
            "error_rate": 0, "cache_hit_rate": 0, "cache_hits": 0,
            "total_cost": 0, "avg_cost_per_request": 0,
            "avg_latency_ms": 0, "p95_latency_ms": 0,
            "provider_distribution": {}, "model_distribution": {},
            "tier_distribution": {}, "total_failovers": 0,
        }
