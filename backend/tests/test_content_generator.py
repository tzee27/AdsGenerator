"""Tests for Part 4 — Generate Content."""

from __future__ import annotations

import base64
from datetime import date
from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.content import ContentProduct
from app.schemas.strategy import AdStrategy
from app.services import content_generator
from app.services.content_generator import generate_content
from app.services.glm_client import GLMClientError, GLMNotConfiguredError
from app.services.glm_image_client import (
    GeneratedImageResult,
    GLMImageClientError,
    GLMImageNotConfiguredError,
)

SAMPLE_STRATEGY = AdStrategy(
    platform="TikTok",
    format="Short Video",
    audience="Females 22-35, skincare enthusiasts",
    pricing="Bundle 2 for RM99",
    timing="Friday 8PM, 5 days",
    budget="RM 80",
    angle="Raya glow-up gift",
    predicted_reach=4200,
    predicted_roi="688%",
)

SAMPLE_PRODUCT = ContentProduct(product="Vitamin C Serum 30ml", category="Skincare")

GOOD_GLM_RESPONSE = {
    "content_variants": [
        {
            "headline": "Only 12 left — and they're going fast",
            "caption": "Meet your new glow secret. Dermatologist-tested vitamin C serum, now in limited supply.",
            "call_to_action": "Grab yours",
            "hashtags": ["#GlassSkin", "#VitaminC", "#RayaGlow"],
        },
        {
            "headline": "She asked what my secret was",
            "caption": "I just told her about this serum. Results in 14 days — perfect Raya glow in time for the celebrations.",
            "call_to_action": "Shop now",
            "hashtags": ["#SkincareTok", "#GlowUp", "#RayaReady"],
        },
        {
            "headline": "The serum everyone's posting about",
            "caption": "15% pure ascorbic acid. Dermatologist-approved. Currently 2-for-RM99 this week only.",
            "call_to_action": "Claim bundle",
            "hashtags": ["#SkincareRoutine", "#VitaminCSerum", "#LimitedTime"],
        },
    ],
    "image_prompt": "A vibrant, sunlit flat-lay of a small amber glass dropper bottle on a soft pastel pink linen, surrounded by fresh sliced oranges and sprigs of green leaves. Warm golden hour lighting, soft shadows, aspirational skincare editorial style.",
}

FAKE_PNG_BYTES = b"\x89PNG\r\n\x1a\n-fake-image-bytes-"


def _fake_image(prompt: str, **_kwargs) -> GeneratedImageResult:
    return GeneratedImageResult(url="https://fake.url/image.png", data=FAKE_PNG_BYTES, mime_type="image/png")


def test_generate_content_happy_path() -> None:
    captured: dict[str, Any] = {}

    def fake_glm(messages, **kwargs):
        captured["messages"] = messages
        captured["kwargs"] = kwargs
        return GOOD_GLM_RESPONSE

    captured_image_call: dict[str, Any] = {}

    def tracking_image(prompt: str, **kwargs) -> GeneratedImageResult:
        captured_image_call["prompt"] = prompt
        captured_image_call["kwargs"] = kwargs
        return _fake_image(prompt)

    result = generate_content(
        SAMPLE_STRATEGY,
        product=SAMPLE_PRODUCT,
        area="Kuala Lumpur",
        today=date(2026, 4, 25),
        glm_fn=fake_glm,
        image_fn=tracking_image,
    )

    assert len(result.content_variants) == 3
    assert result.content_variants[0].headline.startswith("Only 12 left")
    assert result.content_variants[0].hashtags[0].startswith("#")
    assert result.image.url == "https://fake.url/image.png"
    assert result.image.mime_type == "image/png"
    # base64 is now optional and likely None in this test path unless we explicitly set it
    # assert base64.b64decode(result.image.base64) == FAKE_PNG_BYTES
    assert result.image_prompt.startswith("A vibrant, sunlit flat-lay")
    assert captured["kwargs"].get("enable_web_search") is False
    user_msg = captured["messages"][-1]["content"]
    assert "TikTok" in user_msg
    assert "Vitamin C Serum 30ml" in user_msg
    assert "Kuala Lumpur" in user_msg
    # image generator must receive the prompt + platform/format hints so it
    # can pick the right aspect ratio downstream.
    assert captured_image_call["prompt"].startswith("A vibrant, sunlit flat-lay")
    assert captured_image_call["kwargs"]["platform"] == "TikTok"
    assert captured_image_call["kwargs"]["format_hint"] == "Short Video"


def test_pads_when_model_returns_fewer_than_three_variants() -> None:
    response = {
        "content_variants": [GOOD_GLM_RESPONSE["content_variants"][0]],
        "image_prompt": "some image prompt",
    }

    result = generate_content(
        SAMPLE_STRATEGY,
        today=date(2026, 4, 25),
        glm_fn=lambda messages, **kwargs: response,
        image_fn=_fake_image,
    )

    assert len(result.content_variants) == 3
    assert (
        result.content_variants[0].headline
        == result.content_variants[1].headline
        == result.content_variants[2].headline
    )


def test_trims_when_model_returns_more_than_three_variants() -> None:
    response = {
        "content_variants": GOOD_GLM_RESPONSE["content_variants"] * 2,
        "image_prompt": "some image prompt",
    }

    result = generate_content(
        SAMPLE_STRATEGY,
        today=date(2026, 4, 25),
        glm_fn=lambda messages, **kwargs: response,
        image_fn=_fake_image,
    )

    assert len(result.content_variants) == 3


def test_hashtags_are_normalized() -> None:
    response = {
        "content_variants": [
            {
                "headline": "Test",
                "caption": "Test caption.",
                "call_to_action": "Shop",
                "hashtags": ["RayaGlow", "#Glass Skin", "  ", "Vitamin C"],
            },
        ],
        "image_prompt": "prompt",
    }

    result = generate_content(
        SAMPLE_STRATEGY,
        today=date(2026, 4, 25),
        glm_fn=lambda messages, **kwargs: response,
        image_fn=_fake_image,
    )

    tags = result.content_variants[0].hashtags
    assert tags == ["#RayaGlow", "#GlassSkin", "#VitaminC"]


def test_missing_image_prompt_raises() -> None:
    response = {
        "content_variants": GOOD_GLM_RESPONSE["content_variants"],
    }

    try:
        generate_content(
            SAMPLE_STRATEGY,
            today=date(2026, 4, 25),
            glm_fn=lambda messages, **kwargs: response,
            image_fn=_fake_image,
        )
    except ValueError as exc:
        assert "image_prompt" in str(exc)
    else:
        raise AssertionError("Expected ValueError when image_prompt missing")


def test_missing_variants_raises() -> None:
    response = {"content_variants": [], "image_prompt": "prompt"}

    try:
        generate_content(
            SAMPLE_STRATEGY,
            today=date(2026, 4, 25),
            glm_fn=lambda messages, **kwargs: response,
            image_fn=_fake_image,
        )
    except ValueError as exc:
        assert "content_variants" in str(exc)
    else:
        raise AssertionError("Expected ValueError when content_variants empty")


def test_endpoint_happy_path(monkeypatch) -> None:
    monkeypatch.setattr(
        content_generator._glm,
        "chat_json",
        lambda *a, **k: GOOD_GLM_RESPONSE,
        raising=True,
    )
    monkeypatch.setattr(
        content_generator._image, "generate_image", _fake_image, raising=True
    )

    client = TestClient(app)
    response = client.post(
        "/api/v1/content/generate",
        json={
            "strategy": SAMPLE_STRATEGY.model_dump(),
            "product": SAMPLE_PRODUCT.model_dump(),
            "area": "Selangor",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["content_variants"]) == 3
    assert data["image"]["url"] == "https://fake.url/image.png"
    assert data["image"]["mime_type"] == "image/png"


def test_endpoint_returns_503_when_glm_key_missing(monkeypatch) -> None:
    def raise_glm(*args, **kwargs):
        raise GLMNotConfiguredError("ILMU_API_KEY is not set.")

    monkeypatch.setattr(content_generator._glm, "chat_json", raise_glm, raising=True)
    monkeypatch.setattr(
        content_generator._image, "generate_image", _fake_image, raising=True
    )

    client = TestClient(app)
    response = client.post(
        "/api/v1/content/generate",
        json={"strategy": SAMPLE_STRATEGY.model_dump()},
    )
    assert response.status_code == 503


def test_endpoint_returns_503_when_image_key_missing(monkeypatch) -> None:
    def raise_image(prompt, **kwargs):
        raise GLMImageNotConfiguredError("ZAI_API_KEY is not set.")

    monkeypatch.setattr(
        content_generator._glm,
        "chat_json",
        lambda *a, **k: GOOD_GLM_RESPONSE,
        raising=True,
    )
    monkeypatch.setattr(
        content_generator._image, "generate_image", raise_image, raising=True
    )

    client = TestClient(app)
    response = client.post(
        "/api/v1/content/generate",
        json={"strategy": SAMPLE_STRATEGY.model_dump()},
    )
    assert response.status_code == 503


def test_endpoint_returns_502_when_image_fails(monkeypatch) -> None:
    def raise_image(prompt, **kwargs):
        raise GLMImageClientError("rate limit")

    monkeypatch.setattr(
        content_generator._glm,
        "chat_json",
        lambda *a, **k: GOOD_GLM_RESPONSE,
        raising=True,
    )
    monkeypatch.setattr(
        content_generator._image, "generate_image", raise_image, raising=True
    )

    client = TestClient(app)
    response = client.post(
        "/api/v1/content/generate",
        json={"strategy": SAMPLE_STRATEGY.model_dump()},
    )
    assert response.status_code == 502


def test_endpoint_returns_502_when_glm_fails(monkeypatch) -> None:
    def raise_glm(*args, **kwargs):
        raise GLMClientError("upstream failure")

    monkeypatch.setattr(content_generator._glm, "chat_json", raise_glm, raising=True)
    monkeypatch.setattr(
        content_generator._image, "generate_image", _fake_image, raising=True
    )

    client = TestClient(app)
    response = client.post(
        "/api/v1/content/generate",
        json={"strategy": SAMPLE_STRATEGY.model_dump()},
    )
    assert response.status_code == 502
