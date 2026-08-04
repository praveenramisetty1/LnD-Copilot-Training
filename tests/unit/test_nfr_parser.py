# tests/unit/test_nfr_parser.py
"""Unit tests for NFR header parsing — TC-01"""

import pytest
from fastapi import HTTPException

from src.gateway.nfr_parser import parse_nfr, parse_nfr_from_headers

# ── TC-01-01: All headers present ────────────────────────────────────────────

def test_parse_all_valid_values():
    nfr = parse_nfr("low", "high", "critical")
    assert nfr.latency  == "low"
    assert nfr.cost     == "high"
    assert nfr.accuracy == "critical"


def test_parse_all_medium_standard():
    nfr = parse_nfr("medium", "medium", "standard")
    assert nfr.latency  == "medium"
    assert nfr.cost     == "medium"
    assert nfr.accuracy == "standard"


# ── TC-01-02: Missing headers → defaults applied ─────────────────────────────

def test_defaults_applied_when_no_args():
    nfr = parse_nfr()
    assert nfr.latency  == "medium"
    assert nfr.cost     == "medium"
    assert nfr.accuracy == "standard"


def test_partial_defaults():
    nfr = parse_nfr(latency="low")
    assert nfr.latency  == "low"
    assert nfr.cost     == "medium"   # default
    assert nfr.accuracy == "standard" # default


# ── TC-01-03: Invalid values → HTTP 400 ──────────────────────────────────────

def test_invalid_latency_raises_400():
    with pytest.raises(HTTPException) as exc:
        parse_nfr(latency="ultra")
    assert exc.value.status_code == 400
    assert "latency" in exc.value.detail.lower()


def test_invalid_cost_raises_400():
    with pytest.raises(HTTPException) as exc:
        parse_nfr(cost="free")
    assert exc.value.status_code == 400
    assert "cost" in exc.value.detail.lower()


def test_invalid_accuracy_raises_400():
    with pytest.raises(HTTPException) as exc:
        parse_nfr(accuracy="perfect")
    assert exc.value.status_code == 400
    assert "accuracy" in exc.value.detail.lower()


# ── TC-01-04: Empty string → HTTP 400 ────────────────────────────────────────

def test_empty_latency_raises_400():
    with pytest.raises(HTTPException):
        parse_nfr(latency="")


# ── TC-01-05: Case-insensitive normalisation ──────────────────────────────────

def test_uppercase_values_normalised():
    nfr = parse_nfr("LOW", "HIGH", "CRITICAL")
    assert nfr.latency  == "low"
    assert nfr.cost     == "high"
    assert nfr.accuracy == "critical"


def test_mixed_case_normalised():
    nfr = parse_nfr("Low", "Medium", "Standard")
    assert nfr.latency  == "low"
    assert nfr.cost     == "medium"
    assert nfr.accuracy == "standard"


def test_whitespace_stripped():
    nfr = parse_nfr("  low  ", "  high  ", "  critical  ")
    assert nfr.latency  == "low"
    assert nfr.cost     == "high"
    assert nfr.accuracy == "critical"


# ── Model preference ──────────────────────────────────────────────────────────

def test_model_preference_stored():
    nfr = parse_nfr("low", "low", "standard", model_preference="gpt-4")
    assert nfr.model_preference == "gpt-4"


def test_model_preference_none_by_default():
    nfr = parse_nfr()
    assert nfr.model_preference is None


# ── as_dict() ─────────────────────────────────────────────────────────────────

def test_as_dict_returns_all_keys():
    nfr = parse_nfr("low", "medium", "high", model_preference="claude-3-opus")
    d = nfr.as_dict()
    assert d["latency"]          == "low"
    assert d["cost"]             == "medium"
    assert d["accuracy"]         == "high"
    assert d["model_preference"] == "claude-3-opus"


# ── parse_nfr_from_headers() ──────────────────────────────────────────────────

def test_parse_from_headers_full():
    headers = {
        "x-nfr-latency":  "low",
        "x-nfr-cost":     "low",
        "x-nfr-accuracy": "critical",
    }
    nfr = parse_nfr_from_headers(headers)
    assert nfr.latency  == "low"
    assert nfr.cost     == "low"
    assert nfr.accuracy == "critical"


def test_parse_from_headers_empty_uses_defaults():
    nfr = parse_nfr_from_headers({})
    assert nfr.latency  == "medium"
    assert nfr.cost     == "medium"
    assert nfr.accuracy == "standard"


def test_parse_from_headers_model_preference():
    headers = {"x-model-preference": "gemini-pro"}
    nfr = parse_nfr_from_headers(headers)
    assert nfr.model_preference == "gemini-pro"
