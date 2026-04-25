"""Tests for Part 3 — Decide Ads Strategies (multi-strategy version)."""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.context import LiveContext
from app.schemas.risk import RiskAnalysisResponse, RiskProduct
from app.services import strategy_decider
from app.services.glm_client import GLMClientError, GLMNotConfiguredError
from app.services.strategy_decider import decide_strategy

SAMPLE_RISK = RiskAnalysisResponse(
    high_risk=[
        RiskProduct(
            product="Artisan Sourdough Bread",
            units=35,
            days_to_expiry=3,
            days_unsold=5,
            exposure="RM 490",
            risk_score=82,
        ),
    ],
    medium_risk=[
        RiskProduct(
            product="Vitamin C Serum 30ml",
            units=12,
            days_to_expiry=64,
            days_unsold=28,
            exposure="RM 696",
            risk_score=45,
        ),
        RiskProduct(
            product="Wireless Earbuds Pro",
            units=8,
            days_to_expiry=None,
            days_unsold=20,
            exposure="RM 1,032",
            risk_score=42,
        ),
    ],
    low_risk=[],
)

SAMPLE_CONTEXT = LiveContext(
    upcoming_events=["Hari Raya Aidilfitri in 18 days"],
    trending_formats=["Unboxing videos", "Before/After reels"],
    platform_insights={
        "tiktok": "CPM RM 8, peaks 8-10PM",
        "facebook": "CPM RM 5, peaks 7-9PM Fri-Sun",
    },
    seasonal_opportunity="High — Raya gifting season",
)


def _three_diverse_strategies() -> dict:
    """A well-formed model response with three (product, platform) distinct strategies."""
    return {
        "strategies": [
            {
                "featured_product": "Artisan Sourdough Bread",
                "rationale": "Expiry in 3 days plus risk score 82 demands rapid clearance.",
                "strategy": {
                    "platform": "TikTok",
                    "format": "Short Video",
                    "audience": "Foodies 22-40, KL urban",
                    "pricing": "Bundle 2 loaves RM15",
                    "timing": "Friday 8PM, 2 days",
                    "budget": "RM 60",
                    "angle": "Last-day-fresh deal",
                    "predicted_reach": 3000,
                    "predicted_roi": "550%",
                },
            },
            {
                "featured_product": "Vitamin C Serum 30ml",
                "rationale": "Trending skincare angle aligns with Raya glow-up season.",
                "strategy": {
                    "platform": "Instagram",
                    "format": "Reel",
                    "audience": "Females 22-35, skincare enthusiasts",
                    "pricing": "Bundle 2 for RM99",
                    "timing": "Sunday 7PM, 5 days",
                    "budget": "RM 80",
                    "angle": "Raya glow-up",
                    "predicted_reach": 4200,
                    "predicted_roi": "688%",
                },
            },
            {
                "featured_product": "Wireless Earbuds Pro",
                "rationale": "Low stock (8 units) + tech audience peaks on Facebook video Fri-Sun.",
                "strategy": {
                    "platform": "Facebook",
                    "format": "Image",
                    "audience": "Males 18-30, tech interest",
                    "pricing": "Flash Sale 30%",
                    "timing": "Saturday 9AM, 3 days",
                    "budget": "RM 70",
                    "angle": "Last 8 units only",
                    "predicted_reach": 5500,
                    "predicted_roi": "420%",
                },
            },
        ]
    }


def test_decide_strategy_happy_path_returns_three_options() -> None:
    captured: dict[str, Any] = {}

    def fake_glm(messages, **kwargs):
        captured["messages"] = messages
        captured["kwargs"] = kwargs
        return _three_diverse_strategies()

    result = decide_strategy(
        SAMPLE_RISK,
        SAMPLE_CONTEXT,
        area="Kuala Lumpur",
        today=date(2026, 4, 25),
        count=3,
        glm_fn=fake_glm,
    )

    assert result.area == "Kuala Lumpur"
    assert len(result.strategies) == 3
    products = [opt.featured_product.product for opt in result.strategies]
    assert products == [
        "Artisan Sourdough Bread",
        "Vitamin C Serum 30ml",
        "Wireless Earbuds Pro",
    ]
    platforms = [opt.strategy.platform for opt in result.strategies]
    assert platforms == ["TikTok", "Instagram", "Facebook"]
    # unit price reverse-engineered from exposure / units (e.g. 696/12 = 58.0)
    assert result.strategies[1].unit_price_rm == 58.0
    assert result.strategies[0].rationale.startswith("Expiry in 3 days")
    assert captured["kwargs"].get("enable_web_search") is False
    user_msg = captured["messages"][-1]["content"]
    assert "EXACTLY 3 strategies" in user_msg
    assert "Artisan Sourdough Bread" in user_msg


def test_decide_strategy_uses_orchestrator_supplied_unit_prices() -> None:
    """When the orchestrator passes CSV prices, those win over reverse-engineering."""

    def fake_glm(messages, **kwargs):
        return _three_diverse_strategies()

    result = decide_strategy(
        SAMPLE_RISK,
        SAMPLE_CONTEXT,
        today=date(2026, 4, 25),
        glm_fn=fake_glm,
        unit_price_lookup={
            "vitamin c serum 30ml": 79.99,
            "Artisan Sourdough Bread": 14.5,
        },
    )

    by_product = {opt.featured_product.product: opt for opt in result.strategies}
    assert by_product["Vitamin C Serum 30ml"].unit_price_rm == 79.99
    assert by_product["Artisan Sourdough Bread"].unit_price_rm == 14.5


def test_drops_duplicate_product_platform_pairs() -> None:
    duplicate = {
        "strategies": [
            {
                "featured_product": "Artisan Sourdough Bread",
                "strategy": {"platform": "TikTok", "predicted_reach": 1000},
            },
            # Exact dup of (product, platform) — must be dropped
            {
                "featured_product": "Artisan Sourdough Bread",
                "strategy": {"platform": "TikTok", "predicted_reach": 2000},
            },
            {
                "featured_product": "Vitamin C Serum 30ml",
                "strategy": {"platform": "Instagram", "predicted_reach": 3000},
            },
        ]
    }

    result = decide_strategy(
        SAMPLE_RISK,
        SAMPLE_CONTEXT,
        today=date(2026, 4, 25),
        count=3,
        glm_fn=lambda messages, **kwargs: duplicate,
    )

    assert len(result.strategies) == 3  # padded back up to 3
    pairs = {
        (opt.featured_product.product, opt.strategy.platform)
        for opt in result.strategies
    }
    assert len(pairs) == 3  # all distinct
    assert ("Artisan Sourdough Bread", "TikTok") in pairs


def test_pads_when_model_returns_fewer_than_count() -> None:
    only_one = {
        "strategies": [
            {
                "featured_product": "Artisan Sourdough Bread",
                "strategy": {"platform": "TikTok", "predicted_reach": 1000},
            }
        ]
    }

    result = decide_strategy(
        SAMPLE_RISK,
        SAMPLE_CONTEXT,
        today=date(2026, 4, 25),
        count=3,
        glm_fn=lambda messages, **kwargs: only_one,
    )

    assert len(result.strategies) == 3
    rationales = [opt.rationale for opt in result.strategies]
    # First entry keeps whatever rationale (empty here); padded ones note the fallback.
    assert any("Auto-padded fallback" in r for r in rationales)


def test_unknown_product_falls_back_to_top_high_risk() -> None:
    bad_name = {
        "strategies": [
            {
                "featured_product": "Quantum Toaster 9000",  # not in risk lists
                "strategy": {"platform": "Instagram"},
            }
        ]
    }

    result = decide_strategy(
        SAMPLE_RISK,
        SAMPLE_CONTEXT,
        today=date(2026, 4, 25),
        glm_fn=lambda messages, **kwargs: bad_name,
    )

    assert (
        result.strategies[0].featured_product.product == "Artisan Sourdough Bread"
    )


def test_count_param_is_clamped() -> None:
    captured: dict[str, Any] = {}

    def fake_glm(messages, **kwargs):
        captured["messages"] = messages
        return _three_diverse_strategies()

    result = decide_strategy(
        SAMPLE_RISK,
        SAMPLE_CONTEXT,
        today=date(2026, 4, 25),
        count=99,
        glm_fn=fake_glm,
    )
    assert len(result.strategies) <= 5  # max
    assert "EXACTLY 5 strategies" in captured["messages"][-1]["content"]


def test_backward_compat_accepts_old_single_strategy_response() -> None:
    """The old top-level {strategy: {...}} shape should still produce one option."""
    legacy = {
        "strategy": {
            "platform": "TikTok",
            "format": "Short Video",
            "predicted_reach": 4200,
            "predicted_roi": "688%",
        }
    }

    result = decide_strategy(
        SAMPLE_RISK,
        SAMPLE_CONTEXT,
        today=date(2026, 4, 25),
        count=3,
        glm_fn=lambda messages, **kwargs: legacy,
    )

    # We asked for 3 explicitly; padding fills the rest after the legacy single-strategy.
    assert len(result.strategies) == 3
    assert result.strategies[0].strategy.platform == "TikTok"
    assert result.strategies[0].strategy.predicted_reach == 4200


def test_endpoint_happy_path(monkeypatch) -> None:
    monkeypatch.setattr(
        strategy_decider._glm,
        "chat_json",
        lambda *a, **k: _three_diverse_strategies(),
        raising=True,
    )

    client = TestClient(app)
    response = client.post(
        "/api/v1/strategy/decide",
        json={
            "risk_analysis": SAMPLE_RISK.model_dump(),
            "live_context": SAMPLE_CONTEXT.model_dump(),
            "area": "Selangor",
            "count": 3,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["area"] == "Selangor"
    assert len(data["strategies"]) == 3
    assert data["strategies"][0]["strategy"]["platform"] == "TikTok"
    assert data["strategies"][0]["featured_product"]["product"] == "Artisan Sourdough Bread"


def test_endpoint_respects_count_param(monkeypatch) -> None:
    monkeypatch.setattr(
        strategy_decider._glm,
        "chat_json",
        lambda *a, **k: _three_diverse_strategies(),
        raising=True,
    )

    client = TestClient(app)
    response = client.post(
        "/api/v1/strategy/decide",
        json={
            "risk_analysis": SAMPLE_RISK.model_dump(),
            "live_context": SAMPLE_CONTEXT.model_dump(),
            "count": 2,
        },
    )

    assert response.status_code == 200
    assert len(response.json()["strategies"]) == 2


def test_endpoint_returns_503_when_api_key_missing(monkeypatch) -> None:
    def fake_chat_json(*args, **kwargs):
        raise GLMNotConfiguredError("ILMU_API_KEY is not set.")

    monkeypatch.setattr(
        strategy_decider._glm, "chat_json", fake_chat_json, raising=True
    )

    client = TestClient(app)
    response = client.post(
        "/api/v1/strategy/decide",
        json={
            "risk_analysis": SAMPLE_RISK.model_dump(),
            "live_context": SAMPLE_CONTEXT.model_dump(),
        },
    )
    assert response.status_code == 503


def test_endpoint_returns_502_on_glm_error(monkeypatch) -> None:
    def fake_chat_json(*args, **kwargs):
        raise GLMClientError("upstream failure")

    monkeypatch.setattr(
        strategy_decider._glm, "chat_json", fake_chat_json, raising=True
    )

    client = TestClient(app)
    response = client.post(
        "/api/v1/strategy/decide",
        json={
            "risk_analysis": SAMPLE_RISK.model_dump(),
            "live_context": SAMPLE_CONTEXT.model_dump(),
        },
    )
    assert response.status_code == 502
