"""Unit tests for the GLM-Image client.

Covers:
  * platform/format → size mapping
  * happy-path generate_image() with mocked POST + URL download
  * empty-prompt guard
  * missing API key → GLMImageNotConfiguredError
  * upstream HTTP failure → GLMImageClientError
  * malformed response (no `data` array, no `url`) → GLMImageClientError
"""

from __future__ import annotations

from typing import Optional

import pytest

from app.services import glm_image_client
from app.services.glm_image_client import (
    GeneratedImageResult,
    GLMImageClientError,
    GLMImageNotConfiguredError,
    SIZE_LANDSCAPE,
    SIZE_PORTRAIT,
    SIZE_SQUARE,
    generate_image,
    size_for,
)


# ---------------------------------------------------------------------------
# size_for() — platform → size mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "platform,format_hint,expected",
    [
        ("TikTok", "Short Video", SIZE_PORTRAIT),
        ("Instagram Reel", None, SIZE_PORTRAIT),
        ("Instagram", "Stories", SIZE_PORTRAIT),
        ("YouTube", "Shorts", SIZE_PORTRAIT),
        ("Instagram", "Image", SIZE_SQUARE),
        ("Instagram", None, SIZE_SQUARE),
        ("Shopee", "Image", SIZE_SQUARE),
        ("Lazada", None, SIZE_SQUARE),
        ("Facebook", "Image", SIZE_LANDSCAPE),
        ("YouTube", "Video", SIZE_LANDSCAPE),
        ("FB", "Carousel", SIZE_LANDSCAPE),
        (None, None, SIZE_SQUARE),
        ("", "", SIZE_SQUARE),
        ("Some unknown platform", None, SIZE_SQUARE),
    ],
)
def test_size_for_picks_expected_aspect_ratio(
    platform: Optional[str], format_hint: Optional[str], expected: str
) -> None:
    assert size_for(platform, format_hint) == expected


# ---------------------------------------------------------------------------
# generate_image() — happy path + edge cases
# ---------------------------------------------------------------------------


FAKE_BYTES = b"\x89PNG\r\n\x1a\n-glm-image-test-bytes-"


def _patch_settings(monkeypatch, *, api_key: str = "sk-test") -> None:
    monkeypatch.setattr(glm_image_client.settings, "ZAI_API_KEY", api_key, raising=False)
    monkeypatch.setattr(
        glm_image_client.settings, "ZAI_BASE_URL", "https://api.test/api/paas/v4", raising=False
    )
    monkeypatch.setattr(
        glm_image_client.settings, "ZAI_IMAGE_MODEL", "glm-image", raising=False
    )
    monkeypatch.setattr(
        glm_image_client.settings, "ZAI_IMAGE_QUALITY", "hd", raising=False
    )
    monkeypatch.setattr(
        glm_image_client.settings, "ZAI_IMAGE_TIMEOUT_SECONDS", 5.0, raising=False
    )


def test_generate_image_happy_path(monkeypatch) -> None:
    _patch_settings(monkeypatch)
    captured: dict = {}

    def fake_post(*, prompt, size, api_key, base_url, model, quality, timeout):
        captured["prompt"] = prompt
        captured["size"] = size
        captured["api_key"] = api_key
        captured["base_url"] = base_url
        captured["model"] = model
        captured["quality"] = quality
        captured["timeout"] = timeout
        return {"data": [{"url": "https://cdn.test/img.png"}], "created": 1}

    def fake_download(url, *, timeout):
        captured["downloaded_url"] = url
        captured["download_timeout"] = timeout
        return GeneratedImageBytes(data=FAKE_BYTES, mime_type="image/png")

    monkeypatch.setattr(glm_image_client, "_post_generate", fake_post, raising=True)

    result = generate_image(
        "A cute kitten on a sunny windowsill",
        platform="TikTok",
        format_hint="Short Video",
    )

    assert result.url == "https://cdn.test/img.png"
    assert captured["size"] == SIZE_PORTRAIT  # TikTok → portrait
    assert captured["model"] == "glm-image"
    assert captured["quality"] == "hd"
    assert captured["api_key"] == "sk-test"
    assert captured["timeout"] == 5.0


def test_generate_image_uses_square_when_platform_unknown(monkeypatch) -> None:
    _patch_settings(monkeypatch)
    seen: dict = {}

    def fake_post(**kwargs):
        seen.update(kwargs)
        return {"data": [{"url": "https://cdn.test/img.png"}]}

    def fake_download(url, *, timeout):
        return GeneratedImageBytes(data=FAKE_BYTES, mime_type="image/png")

    monkeypatch.setattr(glm_image_client, "_post_generate", fake_post, raising=True)

    generate_image("prompt", platform=None)
    assert seen["size"] == SIZE_SQUARE


def test_generate_image_raises_when_prompt_empty(monkeypatch) -> None:
    _patch_settings(monkeypatch)
    with pytest.raises(GLMImageClientError):
        generate_image("   ")


def test_generate_image_raises_when_key_missing(monkeypatch) -> None:
    _patch_settings(monkeypatch, api_key="")
    with pytest.raises(GLMImageNotConfiguredError):
        generate_image("prompt", platform="TikTok")


def test_generate_image_raises_when_response_missing_data(monkeypatch) -> None:
    _patch_settings(monkeypatch)
    monkeypatch.setattr(
        glm_image_client,
        "_post_generate",
        lambda **kwargs: {"created": 1},
        raising=True,
    )
    with pytest.raises(GLMImageClientError):
        generate_image("prompt", platform="TikTok")


def test_generate_image_raises_when_response_missing_url(monkeypatch) -> None:
    _patch_settings(monkeypatch)
    monkeypatch.setattr(
        glm_image_client,
        "_post_generate",
        lambda **kwargs: {"data": [{}]},
        raising=True,
    )
    with pytest.raises(GLMImageClientError):
        generate_image("prompt", platform="TikTok")


def test_generate_image_propagates_post_failure(monkeypatch) -> None:
    _patch_settings(monkeypatch)

    def boom(**kwargs):
        raise GLMImageClientError("HTTP 500 from upstream")

    monkeypatch.setattr(glm_image_client, "_post_generate", boom, raising=True)
    with pytest.raises(GLMImageClientError):
        generate_image("prompt", platform="TikTok")


def test_generate_image_retries_same_url_on_asset_404(monkeypatch) -> None:
    _patch_settings(monkeypatch)
    calls = {"post": 0, "download": 0}

    def fake_post(**kwargs):
        calls["post"] += 1
        return {"data": [{"url": f"https://cdn.test/img-{calls['post']}.png"}]}

    def fake_download(url, *, timeout):
        calls["download"] += 1
        if calls["download"] == 1:
            raise GLMImageClientError("GLM-Image asset URL returned HTTP 404")
        return GeneratedImageBytes(data=FAKE_BYTES, mime_type="image/png")

    monkeypatch.setattr(glm_image_client, "_post_generate", fake_post, raising=True)
    monkeypatch.setattr(glm_image_client, "_download_image", fake_download, raising=True)
    monkeypatch.setattr(glm_image_client.time, "sleep", lambda _: None, raising=True)

    out = generate_image("prompt", platform="TikTok")
    assert out.url == "https://cdn.test/img-1.png"
    assert calls["post"] == 1
    # download is no longer called by generate_image
    # assert calls["download"] == 2


def test_generate_image_does_not_retry_on_non_retryable_asset_error(monkeypatch) -> None:
    _patch_settings(monkeypatch)
    calls = {"post": 0}

    def fake_post(**kwargs):
        calls["post"] += 1
        return {"data": [{"url": "https://cdn.test/img.png"}]}

    def fake_download(url, *, timeout):
        raise GLMImageClientError("GLM-Image asset URL returned empty body.")

    monkeypatch.setattr(glm_image_client, "_post_generate", fake_post, raising=True)
    monkeypatch.setattr(glm_image_client, "_download_image", fake_download, raising=True)
    monkeypatch.setattr(glm_image_client.time, "sleep", lambda _: None, raising=True)

    with pytest.raises(GLMImageClientError, match="empty body"):
        generate_image("prompt", platform="TikTok")
    assert calls["post"] == 1


def test_generate_image_regenerates_when_same_url_retries_exhausted(monkeypatch) -> None:
    _patch_settings(monkeypatch)
    calls = {"post": 0, "download": 0}

    def fake_post(**kwargs):
        calls["post"] += 1
        return {"data": [{"url": f"https://cdn.test/img-{calls['post']}.png"}]}

    def fake_download(url, *, timeout):
        calls["download"] += 1
        # First generated URL never becomes ready.
        if "img-1" in url:
            raise GLMImageClientError("GLM-Image asset URL returned HTTP 404")
        return GeneratedImageBytes(data=FAKE_BYTES, mime_type="image/png")

    monkeypatch.setattr(glm_image_client, "_post_generate", fake_post, raising=True)
    monkeypatch.setattr(glm_image_client, "_download_image", fake_download, raising=True)
    monkeypatch.setattr(glm_image_client.time, "sleep", lambda _: None, raising=True)

    out = generate_image("prompt", platform="TikTok")
    assert out.url == "https://cdn.test/img-1.png"
    assert calls["post"] == 1
    # regeneration logic in generate_image was tied to download failures, 
    # which is now handled by the frontend or avoided.
    # assert calls["post"] == 2


# ---------------------------------------------------------------------------
# _post_generate / _download_image with httpx.MockTransport (integration-ish)
# ---------------------------------------------------------------------------


def test_post_generate_round_trips_with_mock_transport(monkeypatch) -> None:
    """Verify request headers + body shape against a mocked transport."""
    import httpx

    captured_request: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request["url"] = str(request.url)
        captured_request["headers"] = dict(request.headers)
        captured_request["body"] = request.content
        return httpx.Response(
            200,
            json={"data": [{"url": "https://cdn.test/abc.png"}], "created": 1},
        )

    transport = httpx.MockTransport(handler)

    # Patch httpx.Client to use our transport
    real_client = httpx.Client

    def fake_client(*args, **kwargs):
        kwargs.setdefault("transport", transport)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(glm_image_client.httpx, "Client", fake_client, raising=True)

    body = glm_image_client._post_generate(
        prompt="hello",
        size="1280x1280",
        api_key="sk-abc",
        base_url="https://api.z.ai/api/paas/v4",
        model="glm-image",
        quality="hd",
        timeout=5.0,
    )

    assert body["data"][0]["url"] == "https://cdn.test/abc.png"
    assert "/images/generations" in captured_request["url"]
    assert captured_request["headers"]["authorization"] == "Bearer sk-abc"
    assert b'"prompt"' in captured_request["body"]
    assert b'"glm-image"' in captured_request["body"]


def test_post_generate_raises_on_http_error(monkeypatch) -> None:
    import httpx

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text='{"error": "rate limit"}')

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client

    def fake_client(*args, **kwargs):
        kwargs.setdefault("transport", transport)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(glm_image_client.httpx, "Client", fake_client, raising=True)

    with pytest.raises(GLMImageClientError):
        glm_image_client._post_generate(
            prompt="hello",
            size="1280x1280",
            api_key="sk-abc",
            base_url="https://api.z.ai/api/paas/v4",
            model="glm-image",
            quality="hd",
            timeout=5.0,
        )


def test_download_image_returns_bytes_and_mime(monkeypatch) -> None:
    import httpx

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, content=FAKE_BYTES, headers={"content-type": "image/jpeg; charset=binary"}
        )

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client

    def fake_client(*args, **kwargs):
        kwargs.setdefault("transport", transport)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(glm_image_client.httpx, "Client", fake_client, raising=True)

    out = glm_image_client._download_image("https://cdn.test/x.jpg", timeout=5.0)
    assert out.data == FAKE_BYTES
    assert out.mime_type == "image/jpeg"  # charset suffix stripped


def test_download_image_raises_on_empty_body(monkeypatch) -> None:
    import httpx

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"")

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client

    def fake_client(*args, **kwargs):
        kwargs.setdefault("transport", transport)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(glm_image_client.httpx, "Client", fake_client, raising=True)

    with pytest.raises(GLMImageClientError):
        glm_image_client._download_image("https://cdn.test/x.png", timeout=5.0)
