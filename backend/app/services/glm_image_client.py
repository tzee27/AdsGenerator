"""Z.AI GLM-Image client (text → image).

Two-step flow inside `generate_image`:
  1. POST to `/paas/v4/images/generations` with bearer auth → response carries a
     temporary URL (valid 30 days per docs).
  2. Download that URL → return raw bytes + MIME so the rest of the pipeline can
     base64-encode it inline so the frontend can render it without a CDN hop.

Aspect ratio is auto-picked from the strategy's `platform` (and an optional
`format_hint`) so e.g. TikTok gets a 9:16 portrait, Facebook gets 16:9
landscape, and Instagram feed defaults to 1:1 square.
"""

from __future__ import annotations

import logging
import mimetypes
import time
from dataclasses import dataclass
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)
MAX_GENERATE_ATTEMPTS = 2
RETRYABLE_ASSET_HTTP_CODES = (404, 408, 429, 500, 502, 503, 504)
ASSET_FETCH_ATTEMPTS_PER_URL = 3
ASSET_FETCH_RETRY_DELAYS_SECONDS = (0.4, 1.0)


class GLMImageClientError(RuntimeError):
    """Raised when GLM-Image cannot be reached or returns no usable image."""


class GLMImageNotConfiguredError(GLMImageClientError):
    """Raised when ZAI_API_KEY is not set."""


@dataclass(slots=True)
class GeneratedImageBytes:
    data: bytes
    mime_type: str


# ---------------------------------------------------------------------------
# Platform → size mapping
# ---------------------------------------------------------------------------
# Sizes chosen from the GLM-Image "recommended common resolutions":
#   1280x1280 (1:1), 1056x1568 (≈2:3 portrait), 1728x960 (≈16:9 landscape).
# Each platform keyword resolves greedily — first match wins.

SIZE_PORTRAIT = "1056x1568"
SIZE_SQUARE = "1280x1280"
SIZE_LANDSCAPE = "1728x960"

PORTRAIT_KEYWORDS = ("tiktok", "reel", "story", "stories", "shorts")
LANDSCAPE_KEYWORDS = ("youtube", "facebook", "fb")
SQUARE_KEYWORDS = ("instagram", "ig", "shopee", "lazada", "feed")


def size_for(platform: Optional[str], format_hint: Optional[str] = None) -> str:
    """Pick a GLM-Image `size` string from a strategy's platform + format."""
    haystack = " ".join(s.lower() for s in (platform or "", format_hint or "") if s)
    if not haystack.strip():
        return SIZE_SQUARE

    # Portrait wins over square wins over landscape — short-form vertical is
    # the most distinctive shape and the most damaging to get wrong.
    if any(kw in haystack for kw in PORTRAIT_KEYWORDS):
        return SIZE_PORTRAIT
    if any(kw in haystack for kw in LANDSCAPE_KEYWORDS):
        return SIZE_LANDSCAPE
    if any(kw in haystack for kw in SQUARE_KEYWORDS):
        return SIZE_SQUARE
    return SIZE_SQUARE


# ---------------------------------------------------------------------------
# HTTP helpers (kept module-level so tests can monkeypatch them)
# ---------------------------------------------------------------------------


def _post_generate(
    *,
    prompt: str,
    size: str,
    api_key: str,
    base_url: str,
    model: str,
    quality: str,
    timeout: float,
) -> dict:
    """POST to the GLM-Image generation endpoint and return parsed JSON."""
    url = f"{base_url.rstrip('/')}/images/generations"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "quality": quality,
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        raise GLMImageClientError(f"GLM-Image network error: {exc}") from exc

    if resp.status_code >= 400:
        # Try to surface the server's error message for easier debugging.
        body_snippet = (resp.text or "")[:500]
        raise GLMImageClientError(
            f"GLM-Image returned HTTP {resp.status_code}: {body_snippet}"
        )

    try:
        return resp.json()
    except ValueError as exc:
        raise GLMImageClientError(
            f"GLM-Image returned non-JSON body: {resp.text[:200]!r}"
        ) from exc


def _download_image(url: str, *, timeout: float) -> GeneratedImageBytes:
    """Fetch the temporary image URL and return raw bytes + MIME type."""
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url)
    except httpx.HTTPError as exc:
        raise GLMImageClientError(
            f"GLM-Image asset download failed: {exc}"
        ) from exc

    if resp.status_code >= 400:
        raise GLMImageClientError(
            f"GLM-Image asset URL returned HTTP {resp.status_code}"
        )

    data = resp.content
    if not data:
        raise GLMImageClientError("GLM-Image asset URL returned empty body.")

    mime = (
        resp.headers.get("content-type")
        or mimetypes.guess_type(url)[0]
        or "image/png"
    )
    # Some CDNs append "; charset=..." — strip parameters for cleanliness.
    mime = mime.split(";", 1)[0].strip() or "image/png"
    return GeneratedImageBytes(data=data, mime_type=mime)


def _download_with_retry(url: str, *, timeout: float) -> GeneratedImageBytes:
    """Retry fetching the same URL for short-lived CDN propagation delays."""
    last_error: Optional[GLMImageClientError] = None
    for attempt in range(1, ASSET_FETCH_ATTEMPTS_PER_URL + 1):
        try:
            return _download_image(url, timeout=timeout)
        except GLMImageClientError as exc:
            last_error = exc
            # Only short-retry transient HTTP cases (e.g. early 404 on fresh URL).
            if attempt >= ASSET_FETCH_ATTEMPTS_PER_URL or not _is_retryable_asset_error(exc):
                raise
            delay = ASSET_FETCH_RETRY_DELAYS_SECONDS[min(attempt - 1, len(ASSET_FETCH_RETRY_DELAYS_SECONDS) - 1)]
            logger.warning(
                "GLM-Image asset fetch failed (%s). Retrying same URL in %.1fs (%d/%d).",
                exc,
                delay,
                attempt + 1,
                ASSET_FETCH_ATTEMPTS_PER_URL,
            )
            time.sleep(delay)
    raise last_error or GLMImageClientError("GLM-Image asset fetch failed without explicit error.")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_image(
    prompt: str,
    *,
    platform: Optional[str] = None,
    format_hint: Optional[str] = None,
) -> GeneratedImageBytes:
    """Generate one image from a text prompt using GLM-Image.

    Args:
        prompt: Free-form text describing the desired image.
        platform: Strategy platform (e.g. 'TikTok'). Used to pick aspect ratio.
        format_hint: Optional ad format (e.g. 'Reel', 'Image'). Helps refine
            the aspect-ratio decision when the platform alone is ambiguous.

    Returns:
        Raw image bytes + MIME type so callers can base64-encode inline.

    Raises:
        GLMImageNotConfiguredError: if ZAI_API_KEY is missing.
        GLMImageClientError: if the API call or asset download fails.
    """
    if not prompt or not prompt.strip():
        raise GLMImageClientError("Image prompt is empty.")

    if not settings.ZAI_API_KEY:
        raise GLMImageNotConfiguredError(
            "ZAI_API_KEY is not set. Add it to backend/.env to enable image generation."
        )

    size = size_for(platform, format_hint)
    logger.info(
        "GLM-Image request: model=%s size=%s quality=%s platform=%s format_hint=%s",
        settings.ZAI_IMAGE_MODEL,
        size,
        settings.ZAI_IMAGE_QUALITY,
        platform,
        format_hint,
    )

    last_error: Optional[GLMImageClientError] = None
    for attempt in range(1, MAX_GENERATE_ATTEMPTS + 1):
        body = _post_generate(
            prompt=prompt,
            size=size,
            api_key=settings.ZAI_API_KEY,
            base_url=settings.ZAI_BASE_URL,
            model=settings.ZAI_IMAGE_MODEL,
            quality=settings.ZAI_IMAGE_QUALITY,
            timeout=settings.ZAI_IMAGE_TIMEOUT_SECONDS,
        )

        data_arr = body.get("data") if isinstance(body, dict) else None
        if not isinstance(data_arr, list) or not data_arr:
            raise GLMImageClientError(
                f"GLM-Image response missing 'data' array: {str(body)[:200]!r}"
            )
        first = data_arr[0]
        url = first.get("url") if isinstance(first, dict) else None
        if not url:
            raise GLMImageClientError(
                f"GLM-Image response missing image URL: {str(first)[:200]!r}"
            )
        logger.info(
            "GLM-Image generated asset URL (attempt %d/%d): %s",
            attempt,
            MAX_GENERATE_ATTEMPTS,
            url,
        )

        try:
            return _download_with_retry(url, timeout=settings.ZAI_IMAGE_TIMEOUT_SECONDS)
        except GLMImageClientError as exc:
            last_error = exc
            if attempt >= MAX_GENERATE_ATTEMPTS or not _is_retryable_asset_error(exc):
                raise
            logger.warning(
                "GLM-Image asset fetch failed (%s). Retrying image generation (%d/%d).",
                exc,
                attempt + 1,
                MAX_GENERATE_ATTEMPTS,
            )
            time.sleep(0.5)

    # Defensive: loop should always return or raise before this point.
    raise last_error or GLMImageClientError("GLM-Image failed without explicit error.")


def _is_retryable_asset_error(exc: GLMImageClientError) -> bool:
    msg = str(exc)
    if "GLM-Image asset URL returned HTTP " not in msg:
        return False
    for code in RETRYABLE_ASSET_HTTP_CODES:
        if f"HTTP {code}" in msg:
            return True
    return False


__all__ = [
    "GeneratedImageBytes",
    "GLMImageClientError",
    "GLMImageNotConfiguredError",
    "PORTRAIT_KEYWORDS",
    "LANDSCAPE_KEYWORDS",
    "SQUARE_KEYWORDS",
    "SIZE_PORTRAIT",
    "SIZE_SQUARE",
    "SIZE_LANDSCAPE",
    "generate_image",
    "size_for",
]
