# src/cache/semantic_cache.py
"""
Semantic cache using pure-Python cosine similarity on word-frequency vectors.
No external vector DB or embeddings API required.
Data persisted to data/cache.json.
"""

import json
import math
import os
import re
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

# NOTE: These module-level defaults are intentionally left as fallbacks.
# SemanticCache reads live env vars at __init__ time so tests can use
# monkeypatch.setenv() without reloading the module.
_DEFAULT_CACHE_FILE        = "data/cache.json"
_DEFAULT_SIMILARITY        = "0.75"
_DEFAULT_TTL_SECONDS       = "3600"
_DEFAULT_MAX_ENTRIES       = "1000"

# Common English stop-words removed before computing similarity
STOP_WORDS = {
    "a", "an", "the", "is", "it", "in", "on", "at", "to", "for",
    "of", "and", "or", "but", "not", "with", "this", "that", "was",
    "are", "be", "by", "from", "as", "what", "which", "who", "how",
    "when", "where", "why", "do", "does", "did", "has", "have", "had",
    "will", "would", "could", "should", "may", "might", "can", "i",
    "you", "he", "she", "we", "they", "my", "your", "its",
}


# ── Text utilities ─────────────────────────────────────────────────────────────

def _tokenize(text: str) -> List[str]:
    tokens = re.findall(r"\b[a-z0-9]+\b", text.lower())
    return [t for t in tokens if t not in STOP_WORDS and len(t) > 1]


def _term_freq(tokens: List[str]) -> Dict[str, float]:
    freq: Dict[str, float] = {}
    for t in tokens:
        freq[t] = freq.get(t, 0) + 1
    total = len(tokens) or 1
    return {t: c / total for t, c in freq.items()}


def _cosine_similarity(vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
    common = set(vec1) & set(vec2)
    if not common:
        return 0.0
    dot   = sum(vec1[w] * vec2[w] for w in common)
    mag1  = math.sqrt(sum(v * v for v in vec1.values()))
    mag2  = math.sqrt(sum(v * v for v in vec2.values()))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)


# ── Cache store ───────────────────────────────────────────────────────────────

class SemanticCache:
    """
    In-process semantic cache backed by a local JSON file.
    Thread-safety: adequate for single-process POC (FastAPI default worker).
    Env vars are read at instantiation time so test fixtures (monkeypatch) work.
    """

    def __init__(self):
        # Read config fresh at instantiation — allows monkeypatch in tests
        self._cache_file   = os.getenv("CACHE_FILE",                   _DEFAULT_CACHE_FILE)
        self._threshold    = float(os.getenv("CACHE_SIMILARITY_THRESHOLD", _DEFAULT_SIMILARITY))
        self._ttl_seconds  = int(os.getenv("CACHE_TTL_SECONDS",          _DEFAULT_TTL_SECONDS))
        self._max_entries  = int(os.getenv("CACHE_MAX_ENTRIES",          _DEFAULT_MAX_ENTRIES))
        self._entries: List[dict] = []
        self._load()

    # ── Public API ────────────────────────────────────────────────────────────

    def lookup(self, prompt: str) -> Optional[dict]:
        """
        Return the cached entry if a semantically similar prompt exists,
        otherwise return None.
        Reloads from disk when the in-memory list is empty so that entries
        written by a previous request (in a re-initialised instance) are
        still found.
        """
        self._evict_expired()
        if not self._entries:
            # Fallback: another GatewayRouter instance may have written to
            # disk (e.g. pytest re-initialises the lifespan per test-function
            # event-loop).  Reload so we don't lose a just-stored entry.
            self._load()
            self._evict_expired()
        if not self._entries or not prompt.strip():
            return None

        query_vec = _term_freq(_tokenize(prompt))
        best_entry = None
        best_sim   = 0.0

        for entry in self._entries:
            sim = _cosine_similarity(query_vec, entry["vec"])
            if sim > best_sim:
                best_sim   = sim
                best_entry = entry

        if best_sim >= self._threshold and best_entry:
            best_entry["hit_count"] = best_entry.get("hit_count", 0) + 1
            best_entry["last_hit"]  = time.time()
            self._save()
            return {
                "content":   best_entry["content"],
                "model":     best_entry["model"],
                "provider":  best_entry["provider"],
                "usage":     best_entry.get("usage", {}),
                "similarity": round(best_sim, 4),
            }
        return None

    def store(
        self,
        prompt:   str,
        content:  str,
        model:    str,
        provider: str,
        usage:    dict,
    ) -> None:
        """Add a new entry to the cache (LRU eviction at max capacity)."""
        self._evict_expired()

        tokens = _tokenize(prompt)
        if not tokens:
            return

        entry = {
            "id":        str(uuid.uuid4()),
            "prompt":    prompt[:500],          # Store truncated prompt for debugging
            "vec":       _term_freq(tokens),
            "content":   content,
            "model":     model,
            "provider":  provider,
            "usage":     usage,
            "created_at": time.time(),
            "expires_at": time.time() + self._ttl_seconds,
            "hit_count": 0,
            "last_hit":  None,
        }

        # LRU eviction
        if len(self._entries) >= self._max_entries:
            self._entries.sort(key=lambda e: e.get("last_hit") or e["created_at"])
            self._entries = self._entries[len(self._entries) // 4:]   # Remove oldest 25%

        self._entries.append(entry)
        self._save()

    def size(self) -> int:
        return len(self._entries)

    def clear(self) -> None:
        self._entries = []
        self._save()

    def all_entries(self) -> List[dict]:
        """Return all cache entries (without internal vec field) for analytics."""
        return [
            {k: v for k, v in e.items() if k != "vec"}
            for e in self._entries
        ]

    # ── Persistence ───────────────────────────────────────────────────────────

    def _save(self) -> None:
        Path(self._cache_file).parent.mkdir(parents=True, exist_ok=True)
        with open(self._cache_file, "w") as f:
            json.dump({"entries": self._entries}, f, indent=2)

    def _load(self) -> None:
        if not Path(self._cache_file).exists():
            return
        try:
            with open(self._cache_file) as f:
                data = json.load(f)
            self._entries = data.get("entries", [])
        except (json.JSONDecodeError, KeyError):
            self._entries = []

    def _evict_expired(self) -> None:
        now = time.time()
        before = len(self._entries)
        self._entries = [e for e in self._entries if e.get("expires_at", now + 1) > now]
        if len(self._entries) < before:
            self._save()
