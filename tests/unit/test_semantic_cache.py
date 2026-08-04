# tests/unit/test_semantic_cache.py
"""Unit tests for semantic cache — TC-03"""

import time

import pytest

from src.cache.semantic_cache import SemanticCache, _cosine_similarity, _tokenize

# ── Text utility unit tests ───────────────────────────────────────────────────

def test_tokenize_lowercases():
    assert "HELLO" not in _tokenize("HELLO world")
    assert "hello" in _tokenize("HELLO world")

def test_tokenize_removes_stop_words():
    tokens = _tokenize("what is the capital of France")
    assert "the" not in tokens
    assert "is"  not in tokens
    assert "of"  not in tokens
    assert "capital" in tokens
    assert "france"  in tokens

def test_tokenize_empty_string():
    assert _tokenize("") == []

def test_cosine_similarity_identical_vectors():
    v = {"python": 0.5, "code": 0.5}
    assert abs(_cosine_similarity(v, v) - 1.0) < 1e-6

def test_cosine_similarity_zero_overlap():
    v1 = {"python": 1.0}
    v2 = {"java":   1.0}
    assert _cosine_similarity(v1, v2) == 0.0

def test_cosine_similarity_partial_overlap():
    v1 = {"python": 0.5, "code": 0.5}
    v2 = {"python": 0.5, "java": 0.5}
    sim = _cosine_similarity(v1, v2)
    assert 0.0 < sim < 1.0

def test_cosine_similarity_empty_vectors():
    assert _cosine_similarity({}, {}) == 0.0


# ── SemanticCache ─────────────────────────────────────────────────────────────

@pytest.fixture
def cache(tmp_path, monkeypatch):
    monkeypatch.setenv("CACHE_FILE", str(tmp_path / "cache.json"))
    monkeypatch.setenv("CACHE_SIMILARITY_THRESHOLD", "0.75")
    monkeypatch.setenv("CACHE_TTL_SECONDS", "3600")
    monkeypatch.setenv("CACHE_MAX_ENTRIES", "100")
    return SemanticCache()


# TC-03-01: exact cache hit
def test_exact_cache_hit(cache):
    cache.store("What is the capital of France?", "Paris", "gpt-3.5-turbo", "openai", {})
    result = cache.lookup("What is the capital of France?")
    assert result is not None
    assert result["content"]  == "Paris"
    assert result["model"]    == "gpt-3.5-turbo"
    assert result["provider"] == "openai"


# TC-03-02: semantic cache hit (paraphrased prompt)
def test_semantic_cache_hit_paraphrase(cache):
    cache.store("What is the capital of France?", "Paris", "gpt-3.5-turbo", "openai", {})
    result = cache.lookup("Which city is the capital of France?")
    # Both prompts share key tokens: capital, france
    assert result is not None
    assert result["content"] == "Paris"


# TC-03-03: cache miss on unrelated prompt
def test_cache_miss_unrelated_prompt(cache):
    cache.store("What is the capital of France?", "Paris", "gpt-3.5-turbo", "openai", {})
    result = cache.lookup("Explain quantum entanglement in physics")
    assert result is None


# TC-03-04: below threshold → miss
def test_below_threshold_is_miss(tmp_path, monkeypatch):
    monkeypatch.setenv("CACHE_FILE", str(tmp_path / "cache.json"))
    monkeypatch.setenv("CACHE_SIMILARITY_THRESHOLD", "0.99")  # very strict
    monkeypatch.setenv("CACHE_TTL_SECONDS", "3600")
    monkeypatch.setenv("CACHE_MAX_ENTRIES", "100")
    c = SemanticCache()
    c.store("What is the capital of France?", "Paris", "gpt-3.5-turbo", "openai", {})
    result = c.lookup("Tell me France capital city name please")
    assert result is None


# TC-03-05: TTL expiry
def test_expired_entry_not_served(tmp_path, monkeypatch):
    monkeypatch.setenv("CACHE_FILE", str(tmp_path / "cache.json"))
    monkeypatch.setenv("CACHE_SIMILARITY_THRESHOLD", "0.75")
    monkeypatch.setenv("CACHE_TTL_SECONDS", "1")   # 1-second TTL
    monkeypatch.setenv("CACHE_MAX_ENTRIES", "100")
    c = SemanticCache()
    c.store("What is the capital of France?", "Paris", "gpt-3.5-turbo", "openai", {})
    time.sleep(1.1)                                 # let TTL expire
    c._evict_expired()
    result = c.lookup("What is the capital of France?")
    assert result is None


# TC-03-06: cache latency (fast lookup)
def test_cache_lookup_is_fast(cache):
    cache.store("What is the capital of France?", "Paris", "gpt-3.5-turbo", "openai", {})
    start = time.time()
    cache.lookup("What is the capital of France?")
    elapsed_ms = (time.time() - start) * 1000
    assert elapsed_ms < 100  # must be under 100ms


# size(), clear()
def test_size_increments_on_store(cache):
    assert cache.size() == 0
    cache.store("Prompt A", "Resp A", "gpt-3.5-turbo", "openai", {})
    assert cache.size() == 1
    cache.store("Prompt B", "Resp B", "gpt-3.5-turbo", "openai", {})
    assert cache.size() == 2

def test_clear_empties_cache(cache):
    cache.store("Prompt A", "Resp A", "gpt-3.5-turbo", "openai", {})
    cache.clear()
    assert cache.size() == 0

def test_all_entries_excludes_vec_field(cache):
    cache.store("Prompt A", "Resp A", "gpt-3.5-turbo", "openai", {"total_tokens": 30})
    entries = cache.all_entries()
    assert len(entries) == 1
    assert "vec" not in entries[0]

def test_hit_count_increments(cache):
    cache.store("What is Python?", "A language", "gpt-3.5-turbo", "openai", {})
    cache.lookup("What is Python?")
    cache.lookup("What is Python?")
    entries = cache.all_entries()
    assert entries[0]["hit_count"] >= 1

def test_empty_prompt_not_cached(cache):
    cache.store("", "Some response", "gpt-3.5-turbo", "openai", {})
    assert cache.size() == 0
