# tests/unit/test_model_selector.py
"""Unit tests for NFR-based model scoring and selection — TC-02"""

from src.gateway.model_selector import rank_models, select_model
from src.gateway.nfr_parser import parse_nfr

ALL_PROVIDERS = ["openai", "anthropic", "google"]


# ── TC-02-01: Low cost + standard accuracy selects cheapest model ─────────────

def test_low_cost_standard_selects_cheap_model():
    nfr = parse_nfr("medium", "low", "standard")
    model, provider, score, breakdown = select_model(nfr, "free", ALL_PROVIDERS)
    # Cheapest models: gemini-flash ($0.0001), claude-3-haiku ($0.0002)
    assert model in ["gemini-flash", "claude-3-haiku"]
    assert score > 0
    assert provider in ALL_PROVIDERS


# ── TC-02-02: Critical accuracy selects premium model ────────────────────────

def test_critical_accuracy_selects_premium_model():
    nfr = parse_nfr("medium", "high", "critical")
    model, provider, score, breakdown = select_model(nfr, "pro", ALL_PROVIDERS)
    # High-accuracy models: gpt-4 (0.95), claude-3-opus (0.94), gpt-4-turbo (0.93)
    assert model in ["gpt-4", "claude-3-opus", "gpt-4-turbo"]
    assert score > 0


# ── TC-02-03: Low latency selects fastest model ───────────────────────────────

def test_low_latency_selects_fast_model():
    nfr = parse_nfr("low", "high", "standard")
    model, provider, score, breakdown = select_model(nfr, "free", ALL_PROVIDERS)
    # Fastest models: gemini-flash (400ms), claude-3-haiku (600ms)
    assert model in ["gemini-flash", "claude-3-haiku", "gpt-3.5-turbo"]
    assert score > 0


# ── TC-02-04: Free tier cannot access GPT-4 or Claude-3-Opus ─────────────────

def test_free_tier_blocked_from_premium_models():
    nfr = parse_nfr("medium", "high", "critical")
    model, provider, score, breakdown = select_model(nfr, "free", ALL_PROVIDERS)
    assert model not in ["gpt-4", "claude-3-opus"]


def test_pro_tier_can_access_gpt4():
    nfr = parse_nfr("medium", "high", "critical")
    model, provider, score, breakdown = select_model(nfr, "pro", ALL_PROVIDERS)
    assert model in ["gpt-4", "claude-3-opus", "gpt-4-turbo"]


def test_basic_tier_cannot_access_gpt4():
    nfr = parse_nfr("medium", "high", "critical")
    model, provider, score, breakdown = select_model(nfr, "basic", ALL_PROVIDERS)
    assert model not in ["gpt-4", "claude-3-opus"]
    assert model in ["gpt-4-turbo", "claude-3-sonnet", "gemini-pro"]


# ── TC-02-05: No available providers returns None ─────────────────────────────

def test_no_providers_returns_none():
    nfr = parse_nfr()
    model, provider, score, breakdown = select_model(nfr, "free", [])
    assert model    is None
    assert provider is None
    assert score    == 0.0
    assert breakdown == {}


def test_unavailable_provider_excluded():
    nfr = parse_nfr("medium", "low", "standard")
    # Only google available
    model, provider, score, _ = select_model(nfr, "free", ["google"])
    assert provider == "google"
    assert model in ["gemini-flash", "gemini-pro"]


# ── TC-02-06: Score breakdown is present and valid ───────────────────────────

def test_score_breakdown_keys_present():
    nfr = parse_nfr("low", "low", "standard")
    _, _, _, breakdown = select_model(nfr, "basic", ALL_PROVIDERS)
    assert "cost_score"     in breakdown
    assert "latency_score"  in breakdown
    assert "accuracy_score" in breakdown
    assert "weights"        in breakdown
    assert "final_score"    in breakdown


def test_score_breakdown_weights_sum_to_one():
    nfr = parse_nfr("low", "low", "critical")
    _, _, _, breakdown = select_model(nfr, "pro", ALL_PROVIDERS)
    weights = breakdown["weights"]
    total = weights["cost"] + weights["latency"] + weights["accuracy"]
    assert abs(total - 1.0) < 0.01


def test_scores_are_between_zero_and_one():
    nfr = parse_nfr("medium", "medium", "standard")
    _, _, score, breakdown = select_model(nfr, "enterprise", ALL_PROVIDERS)
    assert 0.0 <= breakdown["cost_score"]     <= 1.0
    assert 0.0 <= breakdown["latency_score"]  <= 1.0
    assert 0.0 <= breakdown["accuracy_score"] <= 1.0


# ── Model preference boost ────────────────────────────────────────────────────

def test_model_preference_influences_selection():
    nfr_no_pref   = parse_nfr("medium", "medium", "standard")
    nfr_with_pref = parse_nfr("medium", "medium", "standard", model_preference="gpt-4")
    model_no_pref, _, _, _   = select_model(nfr_no_pref,   "pro", ALL_PROVIDERS)
    model_with_pref, _, _, _ = select_model(nfr_with_pref, "pro", ALL_PROVIDERS)
    # With preference for gpt-4, it should be selected or its score boosted
    _, _, score_no_pref,   _ = select_model(nfr_no_pref,   "pro", ALL_PROVIDERS)
    _, _, score_with_pref, _ = select_model(nfr_with_pref, "pro", ALL_PROVIDERS)
    assert score_with_pref >= score_no_pref  # preference never reduces score


# ── rank_models() ────────────────────────────────────────────────────────────

def test_rank_models_returns_list():
    nfr = parse_nfr("low", "low", "standard")
    ranked = rank_models(nfr, "pro", ALL_PROVIDERS)
    assert isinstance(ranked, list)
    assert len(ranked) > 0


def test_rank_models_sorted_descending():
    nfr = parse_nfr("low", "low", "standard")
    ranked = rank_models(nfr, "pro", ALL_PROVIDERS)
    scores = [r[2] for r in ranked]
    assert scores == sorted(scores, reverse=True)


def test_rank_models_empty_providers():
    nfr = parse_nfr()
    ranked = rank_models(nfr, "free", [])
    assert ranked == []


def test_rank_models_tuple_structure():
    nfr = parse_nfr()
    ranked = rank_models(nfr, "free", ALL_PROVIDERS)
    for entry in ranked:
        assert len(entry) == 3
        model_name, provider_name, score = entry
        assert isinstance(model_name,   str)
        assert isinstance(provider_name, str)
        assert isinstance(score,         float)
