"""Tests for Part 2 — Live Context Gatherer.

These tests never hit the real ilmu API; the GLM client is either mocked at the
service layer (via `glm_fn=...`) or monkey-patched at the module level for
endpoint tests.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.context import ProductForContext
from app.services import context_gatherer
from app.services.context_gatherer import gather_live_context
from app.services.glm_client import GLMClientError, GLMNotConfiguredError

SAMPLE_PRODUCTS = [
    ProductForContext(product="Vitamin C Serum 30ml", category="Skincare"),
    ProductForContext(product="Bamboo Linen Bedsheet Set", category="Home & Living"),
]

GOOD_GLM_RESPONSE = {
    "context": {
        "upcoming_events": [
            "Hari Raya Aidilfitri in 18 days",
            "Mother's Day in 33 days",
        ],
        "trending_formats": ["Unboxing videos", "Before/After reels"],
        "platform_insights": {
            "tiktok": "CPM RM 8, peaks 8-10PM",
            "facebook": "CPM RM 5, peaks 7-9PM Fri-Sun",
        },
        "seasonal_opportunity": "High — Raya gifting season",
    }
}


def test_gather_context_happy_path() -> None:
    captured: dict[str, Any] = {}

    def fake_glm(messages, **kwargs):
        captured["messages"] = messages
        captured["kwargs"] = kwargs
        return GOOD_GLM_RESPONSE

    result = gather_live_context(
        SAMPLE_PRODUCTS,
        area="Kuala Lumpur",
        today=date(2026, 4, 25),
        glm_fn=fake_glm,
    )

    assert result.area == "Kuala Lumpur"
    assert result.context.seasonal_opportunity == "High — Raya gifting season"
    assert result.context.upcoming_events == [
        "Hari Raya Aidilfitri in 18 days",
        "Mother's Day in 33 days",
    ]
    assert result.context.trending_formats == ["Unboxing videos", "Before/After reels"]
    assert result.context.platform_insights["tiktok"].startswith("CPM RM 8")
    assert captured["kwargs"].get("enable_web_search") is True
    user_msg = captured["messages"][-1]["content"]
    assert "2026-04-25" in user_msg
    assert "Kuala Lumpur" in user_msg
    assert "Vitamin C Serum 30ml" in user_msg


def test_gather_context_handles_list_shaped_platform_insights() -> None:
    weird_response = {
        "context": {
            "upcoming_events": ["Raya in 18 days"],
            "trending_formats": ["UGC"],
            "platform_insights": [
                {"platform": "TikTok", "insight": "CPM RM 8"},
                {"platform": "Facebook", "insight": "CPM RM 5"},
            ],
            "seasonal_opportunity": "High",
        }
    }

    def fake_glm(messages, **kwargs):
        return weird_response

    result = gather_live_context(
        SAMPLE_PRODUCTS,
        area="Malaysia",
        today=date(2026, 4, 25),
        glm_fn=fake_glm,
    )

    assert result.context.platform_insights == {
        "tiktok": "CPM RM 8",
        "facebook": "CPM RM 5",
    }


def test_gather_context_requires_products() -> None:
    try:
        gather_live_context([], glm_fn=lambda *a, **k: GOOD_GLM_RESPONSE)
    except ValueError as exc:
        assert "product" in str(exc).lower()
    else:
        raise AssertionError("Expected ValueError for empty product list.")


def test_endpoint_rejects_empty_products() -> None:
    client = TestClient(app)
    response = client.post("/api/v1/context/gather", json={"products": []})
    assert response.status_code == 422


def test_endpoint_returns_503_when_api_key_missing(monkeypatch) -> None:
    def fake_chat_json(*args, **kwargs):
        raise GLMNotConfiguredError("ILMU_API_KEY is not set.")

    monkeypatch.setattr(
        context_gatherer._glm, "chat_json", fake_chat_json, raising=True
    )

    client = TestClient(app)
    response = client.post(
        "/api/v1/context/gather",
        json={
            "products": [
                {"product": "Vitamin C Serum 30ml", "category": "Skincare"},
            ]
        },
    )
    assert response.status_code == 503
    assert "ILMU_API_KEY" in response.json()["detail"]


def test_endpoint_returns_502_on_glm_error(monkeypatch) -> None:
    def fake_chat_json(*args, **kwargs):
        raise GLMClientError("connection refused")

    monkeypatch.setattr(
        context_gatherer._glm, "chat_json", fake_chat_json, raising=True
    )

    client = TestClient(app)
    response = client.post(
        "/api/v1/context/gather",
        json={"products": [{"product": "X", "category": "Y"}]},
    )
    assert response.status_code == 502


def test_endpoint_happy_path(monkeypatch) -> None:
    def fake_chat_json(*args, **kwargs):
        return GOOD_GLM_RESPONSE

    monkeypatch.setattr(
        context_gatherer._glm, "chat_json", fake_chat_json, raising=True
    )

    client = TestClient(app)
    response = client.post(
        "/api/v1/context/gather",
        json={
            "products": [
                {"product": "Vitamin C Serum 30ml", "category": "Skincare"},
            ],
            "area": "Selangor",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["area"] == "Selangor"
    assert "upcoming_events" in data["context"]
    assert data["context"]["platform_insights"]["tiktok"].startswith("CPM RM 8")
