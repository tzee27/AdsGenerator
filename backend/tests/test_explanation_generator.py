"""Tests for Part 5 — Explain & Score.

The financial projection is pure Python and tested directly against the example
in the pipeline spec (RM 80 → 4,200 reach → 336 clicks → 42 sales → RM 630 →
688% ROI). The prose explanation is mocked (no real GLM calls).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.content import ContentProduct, ContentVariant
from app.schemas.context import LiveContext
from app.schemas.risk import RiskAnalysisResponse, RiskProduct
from app.schemas.strategy import AdStrategy
from app.services import explanation_generator
from app.services.explanation_generator import (
    compute_financial_projection,
    generate_explanation,
)
from app.services.glm_client import GLMClientError, GLMNotConfiguredError

SAMPLE_RISK = RiskAnalysisResponse(
    high_risk=[
        RiskProduct(
            product="Phone Case",
            units=300,
            days_to_expiry=None,
            days_unsold=21,
            exposure="RM 4,500",
            risk_score=82,
        ),
    ],
    medium_risk=[],
    low_risk=[],
)

SAMPLE_CONTEXT = LiveContext(
    upcoming_events=["Hari Raya Aidilfitri in 18 days"],
    trending_formats=["Unboxing videos"],
    platform_insights={
        "tiktok": "CPM RM 8, peaks 8-10PM",
        "facebook": "CPM RM 13, peaks 7-9PM Fri-Sun",
    },
    seasonal_opportunity="High — Raya gifting season",
)

SAMPLE_STRATEGY = AdStrategy(
    platform="TikTok",
    format="Short Video",
    audience="Males 18-30, tech interest",
    pricing="Bundle 3 for price of 2",
    timing="Friday 8PM, 5 days",
    budget="RM 80",
    angle="Raya gift idea",
    predicted_reach=4200,
    predicted_roi="688%",
)

SAMPLE_VARIANTS = [
    ContentVariant(
        headline="Phone case glow-up",
        caption="A bundle deal you can't miss.",
        call_to_action="Shop now",
        hashtags=["#TechTok", "#RayaGift"],
    ),
]

GOOD_PROSE = {
    "platform_reasons": [
        "TikTok CPM (RM 8) gives 40% more reach than Facebook (RM 13) for tech products",
        "Target audience 18-30 is 2.3x more active on TikTok than Facebook",
        "Unboxing trend +340% this week aligns with the bundle angle",
    ],
    "risks": [
        "Inventory pressure: 300 units; demand spike could leave us out of stock",
        "Tech accessory hashtags are crowded; organic reach lower than paid",
    ],
    "rewards": [
        "Bundle 3-for-2 protects margin while moving more units per buyer",
        "Raya gifting window concentrates intent into the next 2 weeks",
    ],
    "verdict": "Clear go — strong reward asymmetry and matching seasonal timing.",
}


# ---------------------------------------------------------------------------
# Financial projection tests (deterministic math)
# ---------------------------------------------------------------------------


def test_financial_projection_matches_example_with_unit_price() -> None:
    """The pipeline-spec example: RM 80 → 4,200 → 336 → 42 → RM 630 → 688%."""
    proj = compute_financial_projection(
        strategy=SAMPLE_STRATEGY,
        risk=SAMPLE_RISK,
        unit_price_rm=15.0,
    )

    assert proj.spend_rm == 80.0
    assert proj.predicted_reach == 4200
    assert proj.click_through_rate == 0.08
    assert proj.predicted_clicks == 336
    assert proj.conversion_rate == 0.125
    assert proj.predicted_sales == 42
    assert proj.average_order_value_rm == 15.0
    assert proj.predicted_revenue_rm == 630.0
    assert proj.roi_percent == 687.5
    assert "Spend RM 80" in proj.summary_line
    assert "4,200" in proj.summary_line
    assert "688%" in proj.summary_line


def test_financial_projection_derives_aov_from_risk_product() -> None:
    """If product matches a risk row, we use exposure/units as AOV."""
    proj = compute_financial_projection(
        strategy=SAMPLE_STRATEGY,
        risk=SAMPLE_RISK,
        product=ContentProduct(product="Phone Case", category="Electronics"),
    )

    assert proj.average_order_value_rm == 15.0
    assert proj.predicted_sales == 42
    assert proj.predicted_revenue_rm == 630.0


def test_financial_projection_falls_back_to_default_aov() -> None:
    """No unit_price, no product match → DEFAULT_AOV_RM (50.0)."""
    proj = compute_financial_projection(
        strategy=SAMPLE_STRATEGY,
        risk=SAMPLE_RISK,
        product=ContentProduct(product="Unknown SKU", category="Electronics"),
    )

    assert proj.average_order_value_rm == 50.0
    assert proj.predicted_revenue_rm == 42 * 50.0


def test_financial_projection_uses_per_platform_heuristics() -> None:
    """Facebook should yield different CTR/conversion than TikTok."""
    fb_strategy = SAMPLE_STRATEGY.model_copy(update={"platform": "Facebook"})

    proj = compute_financial_projection(
        strategy=fb_strategy,
        risk=SAMPLE_RISK,
        unit_price_rm=15.0,
    )

    assert proj.click_through_rate == 0.04
    assert proj.conversion_rate == 0.05
    assert proj.predicted_clicks == int(round(4200 * 0.04))
    assert proj.predicted_sales == int(round(proj.predicted_clicks * 0.05))


def test_financial_projection_handles_zero_budget() -> None:
    """Zero budget → ROI is 0, not a divide-by-zero."""
    zero_strategy = SAMPLE_STRATEGY.model_copy(update={"budget": "RM 0"})
    proj = compute_financial_projection(
        strategy=zero_strategy,
        risk=SAMPLE_RISK,
        unit_price_rm=15.0,
    )

    assert proj.spend_rm == 0.0
    assert proj.roi_percent == 0.0


def test_unknown_platform_uses_default_heuristic() -> None:
    weird = SAMPLE_STRATEGY.model_copy(update={"platform": "Tumblr"})
    proj = compute_financial_projection(
        strategy=weird,
        risk=SAMPLE_RISK,
        unit_price_rm=15.0,
    )

    assert proj.click_through_rate == 0.05


# ---------------------------------------------------------------------------
# Service-level tests (deterministic finance + mocked prose)
# ---------------------------------------------------------------------------


def test_generate_explanation_happy_path() -> None:
    captured: dict[str, Any] = {}

    def fake_glm(messages, **kwargs):
        captured["messages"] = messages
        captured["kwargs"] = kwargs
        return GOOD_PROSE

    result = generate_explanation(
        risk=SAMPLE_RISK,
        context=SAMPLE_CONTEXT,
        strategy=SAMPLE_STRATEGY,
        variants=SAMPLE_VARIANTS,
        product=ContentProduct(product="Phone Case", category="Electronics"),
        area="Kuala Lumpur",
        today=date(2026, 4, 25),
        glm_fn=fake_glm,
    )

    assert result.area == "Kuala Lumpur"
    assert result.platform_choice.platform == "TikTok"
    assert len(result.platform_choice.reasons) == 3
    assert result.platform_choice.reasons[0].startswith("TikTok CPM")
    assert result.financial_projection.predicted_revenue_rm == 630.0
    assert result.financial_projection.roi_percent == 687.5
    assert len(result.risk_vs_reward.risks) == 2
    assert len(result.risk_vs_reward.rewards) == 2
    assert result.risk_vs_reward.verdict.startswith("Clear go")
    assert captured["kwargs"].get("enable_web_search") is False
    user_msg = captured["messages"][-1]["content"]
    assert "TikTok" in user_msg
    assert "HIGH RISK" in user_msg
    assert "Phone Case" in user_msg
    assert "Hari Raya Aidilfitri in 18 days" in user_msg


def test_generate_explanation_truncates_overlong_lists() -> None:
    bloated = {
        "platform_reasons": [f"reason {i}" for i in range(20)],
        "risks": [f"risk {i}" for i in range(20)],
        "rewards": [f"reward {i}" for i in range(20)],
        "verdict": "Cautious go.",
    }

    result = generate_explanation(
        risk=SAMPLE_RISK,
        context=SAMPLE_CONTEXT,
        strategy=SAMPLE_STRATEGY,
        today=date(2026, 4, 25),
        glm_fn=lambda messages, **kwargs: bloated,
    )

    assert len(result.platform_choice.reasons) == 5
    assert len(result.risk_vs_reward.risks) == 4
    assert len(result.risk_vs_reward.rewards) == 4


def test_generate_explanation_handles_missing_prose_fields() -> None:
    minimal = {"platform_reasons": ["only one reason"]}

    result = generate_explanation(
        risk=SAMPLE_RISK,
        context=SAMPLE_CONTEXT,
        strategy=SAMPLE_STRATEGY,
        today=date(2026, 4, 25),
        glm_fn=lambda messages, **kwargs: minimal,
    )

    assert result.platform_choice.reasons == ["only one reason"]
    assert result.risk_vs_reward.risks == []
    assert result.risk_vs_reward.rewards == []
    assert result.risk_vs_reward.verdict == ""


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------


def _request_body() -> dict:
    return {
        "risk_analysis": SAMPLE_RISK.model_dump(),
        "live_context": SAMPLE_CONTEXT.model_dump(),
        "strategy": SAMPLE_STRATEGY.model_dump(),
        "content_variants": [v.model_dump() for v in SAMPLE_VARIANTS],
        "product": {"product": "Phone Case", "category": "Electronics"},
    }


def test_endpoint_happy_path(monkeypatch) -> None:
    monkeypatch.setattr(
        explanation_generator._glm,
        "chat_json",
        lambda *a, **k: GOOD_PROSE,
        raising=True,
    )

    client = TestClient(app)
    response = client.post("/api/v1/explanation/generate", json=_request_body())

    assert response.status_code == 200
    data = response.json()
    assert data["platform_choice"]["platform"] == "TikTok"
    assert len(data["platform_choice"]["reasons"]) == 3
    assert data["financial_projection"]["predicted_revenue_rm"] == 630.0
    assert data["financial_projection"]["roi_percent"] == 687.5
    assert data["risk_vs_reward"]["verdict"].startswith("Clear go")


def test_endpoint_returns_503_when_glm_key_missing(monkeypatch) -> None:
    def raise_glm(*args, **kwargs):
        raise GLMNotConfiguredError("ILMU_API_KEY is not set.")

    monkeypatch.setattr(
        explanation_generator._glm, "chat_json", raise_glm, raising=True
    )

    client = TestClient(app)
    response = client.post("/api/v1/explanation/generate", json=_request_body())
    assert response.status_code == 503


def test_endpoint_returns_502_on_glm_error(monkeypatch) -> None:
    def raise_glm(*args, **kwargs):
        raise GLMClientError("upstream failure")

    monkeypatch.setattr(
        explanation_generator._glm, "chat_json", raise_glm, raising=True
    )

    client = TestClient(app)
    response = client.post("/api/v1/explanation/generate", json=_request_body())
    assert response.status_code == 502
