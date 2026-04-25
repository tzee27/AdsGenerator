"""Part 2 — Live Context Gatherer.

Uses GLM-5.1's built-in web search to gather today's fresh signals for the given
area and product list. Returns a normalized `LiveContext` so downstream parts
(strategy, content generation) receive a stable shape regardless of what the
model wrote.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Callable, Optional

from pydantic import ValidationError

from app.core.config import settings
from app.schemas.context import (
    LiveContext,
    LiveContextResponse,
    ProductForContext,
)
from app.services import glm_client as _glm

SYSTEM_PROMPT = """You are an advertising strategist assistant with live web-search access.
Your only job is to return a single JSON object describing today's marketing context
for the given region and product list. Use web search to find today's trends,
upcoming holidays/events, and current paid-media costs. Do not invent numbers."""

JSON_SCHEMA_HINT = """Return EXACTLY this JSON shape (no markdown, no prose, no code fences):
{
  "context": {
    "upcoming_events": [
      "<event name> in <N> days"
    ],
    "trending_formats": [
      "<short phrase, e.g. 'Unboxing videos'>"
    ],
    "platform_insights": {
      "tiktok": "CPM RM <X>, peaks <time window>",
      "facebook": "CPM RM <X>, peaks <time window>",
      "instagram": "CPM RM <X>, peaks <time window>"
    },
    "seasonal_opportunity": "<one short sentence, e.g. 'High — Raya gifting season'>"
  }
}"""

RULES = """Rules:
- upcoming_events: 2-5 items, only events/holidays in the next 6 months that matter for retail/advertising. Each item must follow the exact format "<name> in <N> days".
- trending_formats: 2-5 short phrases describing ad creative formats trending RIGHT NOW (this week) in {area}.
- platform_insights: include at minimum tiktok and facebook. Add instagram/shopee/lazada if relevant. Values must be one-liners like "CPM RM 8, peaks 8-10PM".
- seasonal_opportunity: one short phrase capped at ~12 words summarizing the overall demand window.
- All prices must be in Malaysian Ringgit (RM).
- Output raw JSON only. No commentary, no markdown fences."""


def _build_user_prompt(
    *,
    area: str,
    today: date,
    products: list[ProductForContext],
) -> str:
    product_lines = "\n".join(
        f"- {p.product}" + (f" (category: {p.category})" if p.category else "")
        for p in products
    )
    return (
        f"Today is {today.isoformat()}. Target region: {area}.\n\n"
        f"Products we are planning to promote:\n{product_lines}\n\n"
        f"Use web search to find the LATEST (as of {today.isoformat()}) information "
        f"about upcoming events/holidays in {area}, ad-creative formats trending this "
        f"week, and current CPM/peak-hour data for major ad platforms in {area}.\n\n"
        f"{JSON_SCHEMA_HINT}\n\n{RULES.format(area=area)}"
    )


def _coerce_context(raw: dict) -> LiveContext:
    """Normalize assorted model outputs into our `LiveContext` schema."""
    payload = raw.get("context") if isinstance(raw.get("context"), dict) else raw

    insights_raw = payload.get("platform_insights", {}) or {}
    if isinstance(insights_raw, list):
        insights: dict[str, str] = {}
        for item in insights_raw:
            if not isinstance(item, dict):
                continue
            key = str(item.get("platform") or item.get("name") or "").strip().lower()
            value = str(item.get("insight") or item.get("info") or item.get("value") or "").strip()
            if key and value:
                insights[key] = value
    elif isinstance(insights_raw, dict):
        insights = {str(k).lower(): str(v) for k, v in insights_raw.items() if v}
    else:
        insights = {}

    def _str_list(value) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(x).strip() for x in value if str(x).strip()]

    try:
        return LiveContext(
            upcoming_events=_str_list(payload.get("upcoming_events")),
            trending_formats=_str_list(payload.get("trending_formats")),
            platform_insights=insights,
            seasonal_opportunity=str(payload.get("seasonal_opportunity") or "").strip(),
        )
    except ValidationError as exc:
        raise ValueError(f"Live context JSON failed validation: {exc}") from exc


# Type alias for the GLM callable. Tests inject a fake that takes the same args
# as `glm_client.chat_json` and returns a dict.
GlmCallable = Callable[..., dict]


def gather_live_context(
    products: list[ProductForContext],
    *,
    area: Optional[str] = None,
    today: Optional[date] = None,
    glm_fn: Optional[GlmCallable] = None,
) -> LiveContextResponse:
    """Call GLM-5.1 to gather today's marketing context for `products` in `area`.

    Args:
        products: Products to inform the context (typically high+medium risk).
        area: Override for the target region; falls back to `settings.AREA`.
        today: Override reference date (useful for tests).
        glm_fn: Injected GLM callable; defaults to the real ilmu client.
    """
    if not products:
        raise ValueError("At least one product is required.")

    effective_area = (area or settings.AREA or "Malaysia").strip() or "Malaysia"
    reference_date = today or date.today()
    call_glm: GlmCallable = glm_fn or _glm.chat_json

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": _build_user_prompt(
                area=effective_area, today=reference_date, products=products
            ),
        },
    ]

    raw = call_glm(messages, enable_web_search=True, temperature=0.4)
    context = _coerce_context(raw)

    web_search_used = True
    if glm_fn is None:
        bundle_supports = getattr(_glm, "_bundle", None)
        if bundle_supports is not None:
            web_search_used = bool(getattr(bundle_supports, "supports_web_search", True))

    return LiveContextResponse(
        context=context,
        area=effective_area,
        web_search_used=web_search_used,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    )
