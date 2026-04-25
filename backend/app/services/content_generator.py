"""Part 4 — Generate Content.

Two-step pipeline:
  1. Ask GLM-5.1 for 3 complete ad-copy variants AND one unified image prompt.
  2. Feed the image prompt to GLM-Image (Z.AI) to produce a single shared
     visual for the campaign. Aspect ratio is auto-picked from the strategy's
     platform (e.g. TikTok → 9:16 portrait, Facebook → 16:9 landscape).

Returns inline base64 image + the three copy variants.
"""

from __future__ import annotations

import base64
import logging
from datetime import date, datetime, timezone
from typing import Callable, Optional

from pydantic import ValidationError

from app.core.config import settings
from app.schemas.content import (
    ContentGenerationResponse,
    ContentProduct,
    ContentVariant,
    GeneratedImage,
)
from app.schemas.strategy import AdStrategy
from app.services import glm_client as _glm
from app.services import glm_image_client as _image

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior performance-marketing copywriter and creative director.
Given an ad strategy, you must produce THREE distinct, scroll-stopping content
variants plus ONE unified image-generation prompt that will be sent to a
text-to-image model (GLM-Image). Reply with a single JSON object only — no prose,
no markdown fences."""

JSON_SCHEMA_HINT = """Return EXACTLY this JSON shape:
{
  "content_variants": [
    {
      "headline": "<5-10 words, scroll-stopping>",
      "caption": "<2-4 sentences, platform-appropriate voice>",
      "call_to_action": "<short imperative, e.g. 'Shop now', 'Grab yours'>",
      "hashtags": ["#Tag1", "#Tag2", "..."]
    },
    { "...variant 2..." },
    { "...variant 3..." }
  ],
  "image_prompt": "<one detailed paragraph describing subject, composition, style, lighting, mood and colors for a text-to-image model>"
}"""

RULES = """Rules:
- Exactly 3 content_variants. Each variant must feel distinct (different hook/angle),
  not just paraphrases. At least one should be value-led, at least one emotion-led.
- Match the strategy's platform voice: TikTok = casual/trending, Facebook = direct/clear,
  Instagram = aspirational/visual, Shopee/Lazada = deal-focused.
- Hashtags: use your judgement for count; each must start with '#' and contain no spaces.
- image_prompt: describe ONE cohesive scene that clearly communicates the active promotion.
  Include promotional elements tied to the strategy pricing (e.g. discount badge, sale sticker,
  voucher tag, price slash card). If the pricing contains a concrete offer like "20% off",
  "RM 30 off", or "Buy 2 Free 1", include that exact offer text in the visual direction.
  Keep any overlay text very short (max 3-5 words) and high-contrast.
- If a featured product is provided, the image prompt must depict that exact product/model
  as the hero subject (not a generic category substitute). Mention distinctive physical cues
  so the generated image aligns with the specific item.
- Do NOT include brand logos/trademarks in the image prompt.
- All copy should be in English unless the product clearly demands another language.
- Output RAW JSON only. No commentary, no code fences."""


def _format_strategy_block(strategy: AdStrategy) -> str:
    return (
        f"- platform: {strategy.platform}\n"
        f"- format: {strategy.format}\n"
        f"- audience: {strategy.audience}\n"
        f"- pricing: {strategy.pricing}\n"
        f"- timing: {strategy.timing}\n"
        f"- budget: {strategy.budget}\n"
        f"- angle: {strategy.angle}\n"
        f"- predicted_reach: {strategy.predicted_reach}\n"
        f"- predicted_roi: {strategy.predicted_roi}"
    )


def _build_user_prompt(
    *,
    area: str,
    today: date,
    strategy: AdStrategy,
    product: Optional[ContentProduct],
) -> str:
    product_block = (
        f"Featured product: {product.product}"
        + (f" (category: {product.category})" if product and product.category else "")
        if product
        else "No specific featured product — write at the strategy level."
    )
    return (
        f"Today is {today.isoformat()}. Target region: {area}.\n\n"
        f"--- STRATEGY ---\n{_format_strategy_block(strategy)}\n\n"
        f"--- PRODUCT ---\n{product_block}\n\n"
        f"Promotion to emphasize visually: {strategy.pricing}\n\n"
        "When a featured product is provided above, use that exact product/model as the "
        "main hero object in the image prompt.\n\n"
        f"{JSON_SCHEMA_HINT}\n\n{RULES}"
    )


def _coerce_hashtags(value) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned: list[str] = []
    for item in value:
        tag = str(item).strip()
        if not tag:
            continue
        if not tag.startswith("#"):
            tag = "#" + tag
        tag = tag.replace(" ", "")
        cleaned.append(tag)
    return cleaned


def _coerce_variant(raw: dict) -> ContentVariant:
    try:
        return ContentVariant(
            headline=str(raw.get("headline") or "").strip(),
            caption=str(raw.get("caption") or "").strip(),
            call_to_action=str(raw.get("call_to_action") or raw.get("cta") or "").strip(),
            hashtags=_coerce_hashtags(raw.get("hashtags")),
        )
    except ValidationError as exc:
        raise ValueError(f"Content variant failed validation: {exc}") from exc


def _coerce_payload(raw: dict) -> tuple[list[ContentVariant], str]:
    variants_raw = raw.get("content_variants") or raw.get("variants") or []
    if not isinstance(variants_raw, list) or not variants_raw:
        raise ValueError("Model response did not include a non-empty content_variants array.")

    variants = [_coerce_variant(v if isinstance(v, dict) else {}) for v in variants_raw]

    while len(variants) < 3 and variants:
        variants.append(variants[-1])
    variants = variants[:3]

    if any(not v.headline and not v.caption for v in variants):
        raise ValueError("At least one content variant is empty.")

    image_prompt = str(raw.get("image_prompt") or raw.get("visual_prompt") or "").strip()
    if not image_prompt:
        raise ValueError("Model response did not include an image_prompt.")

    return variants, image_prompt


GlmCallable = Callable[..., dict]
ImageCallable = Callable[..., _image.GeneratedImageBytes]


def generate_content(
    strategy: AdStrategy,
    *,
    product: Optional[ContentProduct] = None,
    area: Optional[str] = None,
    today: Optional[date] = None,
    glm_fn: Optional[GlmCallable] = None,
    image_fn: Optional[ImageCallable] = None,
) -> ContentGenerationResponse:
    """Generate 3 ad-copy variants + 1 shared image for the given strategy."""
    effective_area = (area or settings.AREA or "Malaysia").strip() or "Malaysia"
    reference_date = today or date.today()
    call_glm: GlmCallable = glm_fn or _glm.chat_json
    call_image: ImageCallable = image_fn or _image.generate_image

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": _build_user_prompt(
                area=effective_area,
                today=reference_date,
                strategy=strategy,
                product=product,
            ),
        },
    ]

    raw = call_glm(messages, enable_web_search=False, temperature=0.8)
    variants, image_prompt = _coerce_payload(raw)
    logger.info("GLM-Image prompt: %s", image_prompt)

    image_bytes = call_image(
        image_prompt,
        platform=strategy.platform,
        format_hint=strategy.format,
    )
    image = GeneratedImage(
        mime_type=image_bytes.mime_type,
        base64=base64.b64encode(image_bytes.data).decode("ascii"),
    )

    return ContentGenerationResponse(
        content_variants=variants,
        image_prompt=image_prompt,
        image=image,
        generated_at=datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
    )
