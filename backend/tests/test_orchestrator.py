"""Tests for the two-phase orchestrator (Parts 1-3 in Phase A, 4-5 in Phase B).

GLM-text and GLM-Image are mocked at the call boundary. The fake GLM dispatches
on the caller's system prompt because the orchestrator passes the same `glm_fn`
down to all four LLM-using parts.
"""

from __future__ import annotations

import base64
from datetime import date
from io import BytesIO

from fastapi.testclient import TestClient

from app.main import app
from app.services import content_generator, context_gatherer
from app.services import explanation_generator, strategy_decider
from app.services.glm_client import GLMClientError, GLMNotConfiguredError
from app.services.glm_image_client import (
    GeneratedImageBytes,
    GLMImageClientError,
    GLMImageNotConfiguredError,
)
from app.services.orchestrator import (
    OrchestratorError,
    run_phase_a,
    run_phase_b,
)

TODAY = date(2026, 4, 25)
FAKE_PNG_BYTES = b"\x89PNG\r\n\x1a\n-orchestrator-test-image-"

CSV_HEADER = "product_name,category,stock_level,price,date_added,expiry_date"
SAMPLE_CSV_ROWS = [
    # High risk: 3d to expiry, 40d unsold, RM4500 exposure -> 82
    "Old Yogurt,Groceries,300,15.00,2026-03-16,2026-04-28",
    # Medium risk: 5d to expiry, fresh, RM450 exposure -> 45
    "Bread,Groceries,45,10.00,2026-04-20,2026-04-28",
    # Low risk: fresh, low exposure
    "Phone Case,Electronics,10,20.00,2026-04-23,",
]


def _csv(rows=None) -> str:
    rows = rows if rows is not None else SAMPLE_CSV_ROWS
    return "\n".join([CSV_HEADER, *rows]) + "\n"


# ---------------------------------------------------------------------------
# Mocked GLM responses per part
# ---------------------------------------------------------------------------

GOOD_CONTEXT = {
    "context": {
        "upcoming_events": ["Hari Raya in 18 days", "11.11 in 7 months"],
        "trending_formats": ["Unboxing videos", "Before/After reels"],
        "platform_insights": {
            "tiktok": "CPM RM 8, peaks 8-10PM",
            "facebook": "CPM RM 5, peaks 7-9PM Fri-Sun",
        },
        "seasonal_opportunity": "High — Raya gifting season",
    }
}

GOOD_STRATEGIES_3 = {
    "strategies": [
        {
            "featured_product": "Old Yogurt",
            "rationale": "Risk score 82 + 3-day expiry needs urgent clearance.",
            "strategy": {
                "platform": "TikTok",
                "format": "Short Video",
                "audience": "Females 25-40, household groceries",
                "pricing": "Bundle 2 for RM25",
                "timing": "Friday 8PM, 5 days",
                "budget": "RM 80",
                "angle": "Last-day-fresh deal",
                "predicted_reach": 4200,
                "predicted_roi": "850%",
            },
        },
        {
            "featured_product": "Bread",
            "rationale": "Bakery shoppers respond well to Facebook image carousels.",
            "strategy": {
                "platform": "Facebook",
                "format": "Image",
                "audience": "Homemakers 28-50",
                "pricing": "BOGO",
                "timing": "Saturday 9AM, 2 days",
                "budget": "RM 60",
                "angle": "Weekend brunch staple",
                "predicted_reach": 3200,
                "predicted_roi": "420%",
            },
        },
        {
            "featured_product": "Phone Case",
            "rationale": "Tech category trending on Instagram this week.",
            "strategy": {
                "platform": "Instagram",
                "format": "Reel",
                "audience": "Males 18-30, tech interest",
                "pricing": "Flash Sale 30%",
                "timing": "Sunday 8PM, 3 days",
                "budget": "RM 50",
                "angle": "Drop-test hero",
                "predicted_reach": 2800,
                "predicted_roi": "280%",
            },
        },
    ]
}

GOOD_CONTENT = {
    "content_variants": [
        {
            "headline": "Last 3 days — half off before it's gone",
            "caption": "Fresh yogurt, dropping price daily until expiry. Stock up now.",
            "call_to_action": "Grab pack",
            "hashtags": ["#FreshDeal", "#Groceries"],
        },
        {
            "headline": "Why pay full price when it expires Sunday?",
            "caption": "Smart shoppers grab end-of-shelf bargains. So should you.",
            "call_to_action": "Shop now",
            "hashtags": ["#SmartShopping"],
        },
        {
            "headline": "300 units — gone by the weekend",
            "caption": "Tag a friend who deserves a deal.",
            "call_to_action": "Tag and grab",
            "hashtags": ["#TagAFriend"],
        },
    ],
    "image_prompt": "A bright supermarket cooler shelf stocked with rows of yogurt cups, warm overhead lighting, shallow depth of field, hyper-realistic editorial style.",
}

GOOD_EXPLANATION = {
    "platform_reasons": [
        "TikTok matches the impulse-buy mindset for time-pressured grocery deals.",
        "TikTok CPM RM 8 outperforms Facebook RM 5 for short-shelf-life angles.",
        "Females 25-40 over-index on TikTok shopping content this quarter.",
    ],
    "risks": [
        "Three-day expiry window leaves little room for delivery delays.",
        "Discount may bleed margin if conversion lags.",
    ],
    "rewards": [
        "Clears RM4,500 of capital exposure before write-off.",
        "Builds short-term brand awareness during Raya gifting season.",
    ],
    "verdict": "Clear go — limited downside, high inventory-clearance upside.",
}


def _fake_image(prompt: str, **_kwargs) -> GeneratedImageBytes:
    return GeneratedImageBytes(data=FAKE_PNG_BYTES, mime_type="image/png")


def _make_dispatching_glm():
    """Fake GLM that picks the right JSON shape based on caller's system prompt."""

    def fake_glm(messages, **kwargs) -> dict:
        system = ""
        for msg in messages:
            if msg.get("role") == "system":
                system = msg.get("content", "")
                break
        if "advertising strategist assistant with live web-search" in system:
            return GOOD_CONTEXT
        if "performance-marketing strategist" in system:
            return GOOD_STRATEGIES_3
        if "performance-marketing copywriter" in system:
            return GOOD_CONTENT
        if "senior marketing analyst" in system:
            return GOOD_EXPLANATION
        raise AssertionError(f"Unrecognised system prompt: {system[:120]!r}")

    return fake_glm


# ---------------------------------------------------------------------------
# Service-level: Phase A
# ---------------------------------------------------------------------------


def test_phase_a_happy_path_returns_three_options() -> None:
    result = run_phase_a(
        _csv(),
        area="Kuala Lumpur",
        today=TODAY,
        count=3,
        glm_fn=_make_dispatching_glm(),
    )

    assert result.metadata.area == "Kuala Lumpur"
    assert len(result.strategies) == 3
    products = [opt.featured_product.product for opt in result.strategies]
    assert products == ["Old Yogurt", "Bread", "Phone Case"]
    # Categories should be enriched from the CSV (strategy decider doesn't see them)
    assert result.strategies[0].featured_product.category == "Groceries"
    assert result.strategies[2].featured_product.category == "Electronics"
    # Unit prices should match the CSV (orchestrator passes price_lookup)
    assert result.strategies[0].unit_price_rm == 15.0
    assert result.strategies[2].unit_price_rm == 20.0
    # Risk analysis + live context echoed back
    assert result.risk_analysis.high_risk[0].product == "Old Yogurt"
    assert result.live_context.seasonal_opportunity.startswith("High")
    # Timing tracked for all three Phase A parts
    assert set(result.metadata.timing_ms) == {"risk", "context", "strategy"}


def test_phase_a_count_param_propagates() -> None:
    result = run_phase_a(
        _csv(),
        today=TODAY,
        count=2,
        glm_fn=_make_dispatching_glm(),
    )
    assert len(result.strategies) == 2


def test_phase_a_propagates_context_failure() -> None:
    glm = _make_dispatching_glm()

    def failing_glm(messages, **kwargs):
        for m in messages:
            if m.get("role") == "system" and "live web-search" in m.get("content", ""):
                raise GLMClientError("ilmu transient 5xx")
        return glm(messages, **kwargs)

    try:
        run_phase_a(_csv(), today=TODAY, glm_fn=failing_glm)
    except OrchestratorError as exc:
        assert exc.failed_part == "context"
        assert isinstance(exc.original, GLMClientError)
        assert exc.completed["risk"] is True
        assert exc.completed["context"] is False
    else:
        raise AssertionError("Expected OrchestratorError when context fails")


def test_phase_a_propagates_strategy_failure() -> None:
    glm = _make_dispatching_glm()

    def failing_glm(messages, **kwargs):
        for m in messages:
            if m.get("role") == "system" and "performance-marketing strategist" in m.get(
                "content", ""
            ):
                raise GLMClientError("strategy stage broke")
        return glm(messages, **kwargs)

    try:
        run_phase_a(_csv(), today=TODAY, glm_fn=failing_glm)
    except OrchestratorError as exc:
        assert exc.failed_part == "strategy"
        assert exc.completed["risk"] is True
        assert exc.completed["context"] is True
        assert exc.completed["strategy"] is False
    else:
        raise AssertionError("Expected OrchestratorError when strategy fails")


# ---------------------------------------------------------------------------
# Service-level: Phase B
# ---------------------------------------------------------------------------


def test_phase_b_happy_path() -> None:
    phase_a = run_phase_a(_csv(), today=TODAY, glm_fn=_make_dispatching_glm())

    result = run_phase_b(
        selected=phase_a.strategies[0],  # Old Yogurt + TikTok
        risk=phase_a.risk_analysis,
        context=phase_a.live_context,
        today=TODAY,
        glm_fn=_make_dispatching_glm(),
        image_fn=_fake_image,
    )

    assert result.metadata.featured_product.product == "Old Yogurt"
    assert result.metadata.unit_price_rm == 15.0
    assert len(result.content.content_variants) == 3
    assert base64.b64decode(result.content.image.base64) == FAKE_PNG_BYTES
    assert result.explanation.platform_choice.platform == "TikTok"
    assert result.explanation.financial_projection.average_order_value_rm == 15.0
    assert set(result.metadata.timing_ms) == {"content", "explanation"}


def test_phase_b_uses_other_options_aov() -> None:
    """Picking a different option must thread that option's unit_price into AOV."""
    # Need count=3 so the Phone Case option (3rd in the mock) survives.
    phase_a = run_phase_a(_csv(), today=TODAY, count=3, glm_fn=_make_dispatching_glm())

    # Pick the Phone Case option (RM 20)
    phone_option = next(
        o for o in phase_a.strategies if o.featured_product.product == "Phone Case"
    )

    result = run_phase_b(
        selected=phone_option,
        risk=phase_a.risk_analysis,
        context=phase_a.live_context,
        today=TODAY,
        glm_fn=_make_dispatching_glm(),
        image_fn=_fake_image,
    )

    assert result.explanation.financial_projection.average_order_value_rm == 20.0


def test_phase_b_propagates_content_failure() -> None:
    phase_a = run_phase_a(_csv(), today=TODAY, glm_fn=_make_dispatching_glm())

    glm = _make_dispatching_glm()

    def failing_glm(messages, **kwargs):
        for m in messages:
            if m.get("role") == "system" and "copywriter" in m.get("content", ""):
                raise GLMClientError("rate limited at content stage")
        return glm(messages, **kwargs)

    try:
        run_phase_b(
            selected=phase_a.strategies[0],
            risk=phase_a.risk_analysis,
            context=phase_a.live_context,
            today=TODAY,
            glm_fn=failing_glm,
            image_fn=_fake_image,
        )
    except OrchestratorError as exc:
        assert exc.failed_part == "content"
        assert exc.completed["content"] is False
        assert exc.featured_product is not None
    else:
        raise AssertionError("Expected OrchestratorError when content fails")


def test_phase_b_propagates_image_failure() -> None:
    phase_a = run_phase_a(_csv(), today=TODAY, glm_fn=_make_dispatching_glm())

    def boom_image(prompt: str, **_kwargs) -> GeneratedImageBytes:
        raise GLMImageClientError("GLM-Image timeout")

    try:
        run_phase_b(
            selected=phase_a.strategies[0],
            risk=phase_a.risk_analysis,
            context=phase_a.live_context,
            today=TODAY,
            glm_fn=_make_dispatching_glm(),
            image_fn=boom_image,
        )
    except OrchestratorError as exc:
        assert exc.failed_part == "content"
        assert isinstance(exc.original, GLMImageClientError)
    else:
        raise AssertionError("Expected OrchestratorError when GLM-Image fails")


def test_phase_b_propagates_explanation_failure() -> None:
    phase_a = run_phase_a(_csv(), today=TODAY, glm_fn=_make_dispatching_glm())

    glm = _make_dispatching_glm()

    def failing_glm(messages, **kwargs):
        for m in messages:
            if m.get("role") == "system" and "marketing analyst" in m.get("content", ""):
                raise GLMClientError("downstream failure on explanation")
        return glm(messages, **kwargs)

    try:
        run_phase_b(
            selected=phase_a.strategies[0],
            risk=phase_a.risk_analysis,
            context=phase_a.live_context,
            today=TODAY,
            glm_fn=failing_glm,
            image_fn=_fake_image,
        )
    except OrchestratorError as exc:
        assert exc.failed_part == "explanation"
        assert exc.completed["content"] is True
        assert exc.completed["explanation"] is False
    else:
        raise AssertionError("Expected OrchestratorError when explanation fails")


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------


def _patch_all_providers(monkeypatch, *, glm_fn=None, image_fn=None) -> None:
    glm_fn = glm_fn or _make_dispatching_glm()
    image_fn = image_fn or _fake_image

    for module in (
        context_gatherer,
        strategy_decider,
        content_generator,
        explanation_generator,
    ):
        monkeypatch.setattr(module._glm, "chat_json", glm_fn, raising=True)
    monkeypatch.setattr(content_generator._image, "generate_image", image_fn, raising=True)


def test_strategies_endpoint_happy_path(monkeypatch) -> None:
    _patch_all_providers(monkeypatch)

    client = TestClient(app)
    response = client.post(
        "/api/v1/ads/strategies",
        files={"file": ("inventory.csv", BytesIO(_csv().encode("utf-8")), "text/csv")},
        data={"area": "Penang", "count": "3"},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert {"risk_analysis", "live_context", "strategies", "metadata"} <= data.keys()
    assert len(data["strategies"]) == 3
    assert data["metadata"]["area"] == "Penang"
    assert data["strategies"][0]["featured_product"]["product"] == "Old Yogurt"
    assert data["strategies"][0]["featured_product"]["category"] == "Groceries"
    assert data["strategies"][0]["unit_price_rm"] == 15.0


def test_strategies_endpoint_respects_count(monkeypatch) -> None:
    _patch_all_providers(monkeypatch)
    client = TestClient(app)
    response = client.post(
        "/api/v1/ads/strategies",
        files={"file": ("inventory.csv", BytesIO(_csv().encode("utf-8")), "text/csv")},
        data={"count": "2"},
    )
    assert response.status_code == 200
    assert len(response.json()["strategies"]) == 2


def test_strategies_endpoint_rejects_non_csv() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/ads/strategies",
        files={"file": ("inventory.txt", BytesIO(b"x"), "text/plain")},
    )
    assert response.status_code == 400


def test_strategies_endpoint_returns_422_for_bad_csv() -> None:
    client = TestClient(app)
    bad = b"product_name,category,stock_level,price\nX,Y,1,1.00\n"
    response = client.post(
        "/api/v1/ads/strategies",
        files={"file": ("inventory.csv", BytesIO(bad), "text/csv")},
    )
    assert response.status_code == 422


def test_strategies_endpoint_returns_502_when_part_fails(monkeypatch) -> None:
    glm = _make_dispatching_glm()

    def failing_glm(messages, **kwargs):
        for m in messages:
            if m.get("role") == "system" and "performance-marketing strategist" in m.get(
                "content", ""
            ):
                raise GLMClientError("strategy stage broke")
        return glm(messages, **kwargs)

    _patch_all_providers(monkeypatch, glm_fn=failing_glm)

    client = TestClient(app)
    response = client.post(
        "/api/v1/ads/strategies",
        files={"file": ("inventory.csv", BytesIO(_csv().encode("utf-8")), "text/csv")},
    )

    assert response.status_code == 502
    detail = response.json()["detail"]
    assert detail["failed_part"] == "strategy"
    assert detail["completed"]["risk"] is True
    assert detail["completed"]["context"] is True


def test_strategies_endpoint_returns_503_when_glm_key_missing(monkeypatch) -> None:
    def raise_unconfigured(messages, **kwargs):
        raise GLMNotConfiguredError("ILMU_API_KEY is not set.")

    _patch_all_providers(monkeypatch, glm_fn=raise_unconfigured)

    client = TestClient(app)
    response = client.post(
        "/api/v1/ads/strategies",
        files={"file": ("inventory.csv", BytesIO(_csv().encode("utf-8")), "text/csv")},
    )
    assert response.status_code == 503


def test_finalize_endpoint_happy_path(monkeypatch) -> None:
    _patch_all_providers(monkeypatch)

    client = TestClient(app)
    # Run Phase A first to get a real selected_strategy + intermediates
    a_resp = client.post(
        "/api/v1/ads/strategies",
        files={"file": ("inventory.csv", BytesIO(_csv().encode("utf-8")), "text/csv")},
    )
    assert a_resp.status_code == 200
    a_data = a_resp.json()

    finalize_payload = {
        "selected_strategy": a_data["strategies"][0],
        "risk_analysis": a_data["risk_analysis"],
        "live_context": a_data["live_context"],
        "area": "Penang",
    }
    response = client.post("/api/v1/ads/finalize", json=finalize_payload)

    assert response.status_code == 200, response.text
    data = response.json()
    assert {"content", "explanation", "metadata"} <= data.keys()
    assert data["metadata"]["featured_product"]["product"] == "Old Yogurt"
    assert len(data["content"]["content_variants"]) == 3
    assert data["content"]["image"]["mime_type"] == "image/png"
    assert (
        base64.b64decode(data["content"]["image"]["base64"]) == FAKE_PNG_BYTES
    )


def test_finalize_endpoint_returns_502_when_image_fails(monkeypatch) -> None:
    def raise_image(prompt: str, **_kwargs):
        raise GLMImageClientError("rate limit")

    _patch_all_providers(monkeypatch, image_fn=raise_image)

    client = TestClient(app)
    a_resp = client.post(
        "/api/v1/ads/strategies",
        files={"file": ("inventory.csv", BytesIO(_csv().encode("utf-8")), "text/csv")},
    )
    a_data = a_resp.json()

    finalize_payload = {
        "selected_strategy": a_data["strategies"][0],
        "risk_analysis": a_data["risk_analysis"],
        "live_context": a_data["live_context"],
    }
    response = client.post("/api/v1/ads/finalize", json=finalize_payload)
    assert response.status_code == 502
    detail = response.json()["detail"]
    assert detail["failed_part"] == "content"


def test_finalize_endpoint_returns_503_when_image_key_missing(monkeypatch) -> None:
    def raise_image(prompt: str, **_kwargs):
        raise GLMImageNotConfiguredError("ZAI_API_KEY is not set.")

    _patch_all_providers(monkeypatch, image_fn=raise_image)

    client = TestClient(app)
    a_resp = client.post(
        "/api/v1/ads/strategies",
        files={"file": ("inventory.csv", BytesIO(_csv().encode("utf-8")), "text/csv")},
    )
    a_data = a_resp.json()

    finalize_payload = {
        "selected_strategy": a_data["strategies"][0],
        "risk_analysis": a_data["risk_analysis"],
        "live_context": a_data["live_context"],
    }
    response = client.post("/api/v1/ads/finalize", json=finalize_payload)
    assert response.status_code == 503
