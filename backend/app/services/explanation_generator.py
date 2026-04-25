"""Part 5 — Explain & Score.

Combines:
  - **Deterministic** financial projection (CTR → clicks → sales → revenue → ROI)
    computed in pure Python so the numbers are reliable, reproducible, and
    auditable. No LLM hallucination on math.
  - **LLM-written prose** for `platform_choice.reasons` and `risk_vs_reward`,
    grounded in the inputs from Parts 1-4 so it actually reflects the data.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Callable, Optional

from app.core.config import settings
from app.schemas.content import ContentProduct, ContentVariant
from app.schemas.context import LiveContext
from app.schemas.explanation import (
    ExplanationResponse,
    FinancialProjection,
    PlatformChoice,
    RiskVsReward,
)
from app.schemas.risk import RiskAnalysisResponse, RiskProduct
from app.schemas.strategy import AdStrategy
from app.services import glm_client as _glm

# Per-platform CTR and click→sale conversion-rate heuristics (decimals).
# Tuned to match the example output (TikTok 8% CTR, ~12.5% conversion).
PLATFORM_HEURISTICS: dict[str, dict[str, float]] = {
    "tiktok": {"ctr": 0.08, "conversion_rate": 0.125},
    "facebook": {"ctr": 0.04, "conversion_rate": 0.05},
    "instagram": {"ctr": 0.05, "conversion_rate": 0.06},
    "shopee": {"ctr": 0.12, "conversion_rate": 0.10},
    "lazada": {"ctr": 0.10, "conversion_rate": 0.08},
}
DEFAULT_HEURISTIC = {"ctr": 0.05, "conversion_rate": 0.05}
DEFAULT_AOV_RM = 50.0


# ---------------------------------------------------------------------------
# Financial projection (pure Python, no LLM)
# ---------------------------------------------------------------------------


def _parse_rm(value: str) -> float:
    """Parse 'RM 80' → 80.0; 'RM 1,500' → 1500.0; '80' → 80.0."""
    if value is None:
        return 0.0
    cleaned = re.sub(r"[^\d.]", "", str(value))
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0


def _parse_exposure_to_unit_price(exposure_rm: float, units: int) -> Optional[float]:
    if units <= 0 or exposure_rm <= 0:
        return None
    return exposure_rm / units


def _find_product_in_risk(
    product_name: str, risk: RiskAnalysisResponse
) -> Optional[RiskProduct]:
    target = product_name.strip().lower()
    if not target:
        return None
    for bucket in (risk.high_risk, risk.medium_risk, risk.low_risk):
        for p in bucket:
            if p.product.strip().lower() == target:
                return p
    return None


def _resolve_aov(
    *,
    explicit_unit_price: Optional[float],
    product: Optional[ContentProduct],
    risk: RiskAnalysisResponse,
) -> float:
    if explicit_unit_price is not None and explicit_unit_price > 0:
        return float(explicit_unit_price)

    if product is not None:
        match = _find_product_in_risk(product.product, risk)
        if match is not None:
            unit_price = _parse_exposure_to_unit_price(
                _parse_rm(match.exposure), match.units
            )
            if unit_price is not None:
                return unit_price

    return DEFAULT_AOV_RM


def _heuristics_for_platform(platform: str) -> dict[str, float]:
    return PLATFORM_HEURISTICS.get(platform.strip().lower(), DEFAULT_HEURISTIC)


def _format_int_with_commas(value: int) -> str:
    return f"{value:,}"


def compute_financial_projection(
    *,
    strategy: AdStrategy,
    risk: RiskAnalysisResponse,
    product: Optional[ContentProduct] = None,
    unit_price_rm: Optional[float] = None,
) -> FinancialProjection:
    """Deterministic spend→revenue waterfall."""
    spend = _parse_rm(strategy.budget)
    reach = max(0, int(strategy.predicted_reach))
    heur = _heuristics_for_platform(strategy.platform)
    ctr = heur["ctr"]
    conversion_rate = heur["conversion_rate"]
    aov = _resolve_aov(
        explicit_unit_price=unit_price_rm, product=product, risk=risk
    )

    clicks = int(round(reach * ctr))
    sales = int(round(clicks * conversion_rate))
    revenue = round(sales * aov, 2)
    roi_percent = (
        round(((revenue - spend) / spend) * 100.0, 2) if spend > 0 else 0.0
    )

    summary = (
        f"Spend RM {int(round(spend))} → Reach {_format_int_with_commas(reach)} → "
        f"{_format_int_with_commas(clicks)} clicks → "
        f"{_format_int_with_commas(sales)} sales → "
        f"RM {int(round(revenue)):,} revenue (ROI {int(round(roi_percent))}%)"
    )

    return FinancialProjection(
        spend_rm=round(spend, 2),
        predicted_reach=reach,
        click_through_rate=round(ctr, 4),
        predicted_clicks=clicks,
        conversion_rate=round(conversion_rate, 4),
        predicted_sales=sales,
        average_order_value_rm=round(aov, 2),
        predicted_revenue_rm=revenue,
        roi_percent=roi_percent,
        summary_line=summary,
    )


# ---------------------------------------------------------------------------
# Prose explanation (GLM)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a senior marketing analyst.
Given the inventory risk analysis, today's live market context, the chosen ad
strategy, and the generated ad copy, you must explain WHY this strategy was
chosen and lay out the risks vs rewards. Reply with a single JSON object only —
no prose, no markdown fences."""

JSON_SCHEMA_HINT = """Return EXACTLY this JSON shape:
{
  "platform_reasons": [
    "<short bullet, ideally with a concrete number from the live context>",
    "<another short bullet>",
    "<3-5 bullets total>"
  ],
  "risks": [
    "<short bullet describing a real risk in this campaign>",
    "<2-4 bullets total>"
  ],
  "rewards": [
    "<short bullet describing a tangible upside>",
    "<2-4 bullets total>"
  ],
  "verdict": "<one short sentence: clear go / cautious go / no-go>"
}"""

RULES = """Rules:
- platform_reasons must reference the chosen platform by name and tie at least
  one bullet to a concrete number from the live context (CPM, peak time, trend
  percent) and one bullet to the target audience match.
- risks should be specific to THIS strategy — inventory pressure, audience
  saturation, low margin, holiday timing risk, etc. Avoid generic platitudes.
- rewards should be specific to THIS strategy too — scarcity leverage, seasonal
  timing, bundle margin, viral hashtag fit.
- Each bullet must be <= 18 words. No emojis. No markdown.
- Do NOT include financial numbers (CTR, ROI, revenue) — those are computed
  separately and shown to the user elsewhere.
- Output RAW JSON only. No commentary, no code fences."""


def _format_risk_summary(risk: RiskAnalysisResponse) -> str:
    def _line(p: RiskProduct) -> str:
        expiry = (
            f"{p.days_to_expiry}d to expiry"
            if p.days_to_expiry is not None
            else "no expiry"
        )
        return (
            f"  - {p.product} | {p.units} units | {expiry} | "
            f"{p.days_unsold}d unsold | exposure {p.exposure} | "
            f"risk {p.risk_score}"
        )

    sections: list[str] = []
    for label, items in (
        ("HIGH RISK", risk.high_risk),
        ("MEDIUM RISK", risk.medium_risk),
        ("LOW RISK", risk.low_risk),
    ):
        if items:
            sections.append(label + ":\n" + "\n".join(_line(p) for p in items[:4]))
        else:
            sections.append(f"{label}: (none)")
    return "\n".join(sections)


def _format_context_summary(ctx: LiveContext) -> str:
    parts: list[str] = []
    if ctx.upcoming_events:
        parts.append("Upcoming events: " + "; ".join(ctx.upcoming_events))
    if ctx.trending_formats:
        parts.append("Trending formats: " + "; ".join(ctx.trending_formats))
    if ctx.platform_insights:
        parts.append(
            "Platform insights:\n"
            + "\n".join(f"  - {k}: {v}" for k, v in ctx.platform_insights.items())
        )
    if ctx.seasonal_opportunity:
        parts.append(f"Seasonal opportunity: {ctx.seasonal_opportunity}")
    return "\n".join(parts) if parts else "(no live context)"


def _format_strategy_block(strategy: AdStrategy) -> str:
    return (
        f"  platform: {strategy.platform}\n"
        f"  format: {strategy.format}\n"
        f"  audience: {strategy.audience}\n"
        f"  pricing: {strategy.pricing}\n"
        f"  timing: {strategy.timing}\n"
        f"  budget: {strategy.budget}\n"
        f"  angle: {strategy.angle}\n"
        f"  predicted_reach: {strategy.predicted_reach}\n"
        f"  predicted_roi: {strategy.predicted_roi}"
    )


def _format_content_block(variants: Optional[list[ContentVariant]]) -> str:
    if not variants:
        return "(no content variants supplied)"
    lines: list[str] = []
    for i, v in enumerate(variants[:3], 1):
        lines.append(
            f"  Variant {i}: {v.headline} | CTA: {v.call_to_action} | "
            f"hashtags: {' '.join(v.hashtags[:6])}"
        )
    return "\n".join(lines)


def _build_user_prompt(
    *,
    area: str,
    today: date,
    risk: RiskAnalysisResponse,
    context: LiveContext,
    strategy: AdStrategy,
    variants: Optional[list[ContentVariant]],
    product: Optional[ContentProduct],
) -> str:
    product_line = (
        f"Featured product: {product.product}"
        + (f" (category: {product.category})" if product.category else "")
        if product
        else "No specific featured product."
    )
    return (
        f"Today is {today.isoformat()}. Target region: {area}.\n\n"
        f"--- INVENTORY RISK ---\n{_format_risk_summary(risk)}\n\n"
        f"--- LIVE CONTEXT ---\n{_format_context_summary(context)}\n\n"
        f"--- STRATEGY ---\n{_format_strategy_block(strategy)}\n\n"
        f"--- {product_line} ---\n\n"
        f"--- AD COPY VARIANTS ---\n{_format_content_block(variants)}\n\n"
        f"{JSON_SCHEMA_HINT}\n\n{RULES}"
    )


def _coerce_str_list(value, max_items: int) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            cleaned.append(text)
        if len(cleaned) >= max_items:
            break
    return cleaned


def _coerce_prose(raw: dict, *, platform: str) -> tuple[PlatformChoice, RiskVsReward]:
    platform_choice = PlatformChoice(
        platform=platform,
        reasons=_coerce_str_list(raw.get("platform_reasons"), max_items=5),
    )
    risk_vs_reward = RiskVsReward(
        risks=_coerce_str_list(raw.get("risks"), max_items=4),
        rewards=_coerce_str_list(raw.get("rewards"), max_items=4),
        verdict=str(raw.get("verdict") or "").strip(),
    )
    return platform_choice, risk_vs_reward


# ---------------------------------------------------------------------------
# Public service entry point
# ---------------------------------------------------------------------------

GlmCallable = Callable[..., dict]


def generate_explanation(
    *,
    risk: RiskAnalysisResponse,
    context: LiveContext,
    strategy: AdStrategy,
    variants: Optional[list[ContentVariant]] = None,
    product: Optional[ContentProduct] = None,
    unit_price_rm: Optional[float] = None,
    area: Optional[str] = None,
    today: Optional[date] = None,
    glm_fn: Optional[GlmCallable] = None,
) -> ExplanationResponse:
    """Build the structured explanation: deterministic finance + LLM prose."""
    effective_area = (area or settings.AREA or "Malaysia").strip() or "Malaysia"
    reference_date = today or date.today()
    call_glm: GlmCallable = glm_fn or _glm.chat_json

    projection = compute_financial_projection(
        strategy=strategy,
        risk=risk,
        product=product,
        unit_price_rm=unit_price_rm,
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": _build_user_prompt(
                area=effective_area,
                today=reference_date,
                risk=risk,
                context=context,
                strategy=strategy,
                variants=variants,
                product=product,
            ),
        },
    ]

    raw = call_glm(messages, enable_web_search=False, temperature=0.5)
    platform_choice, risk_vs_reward = _coerce_prose(raw, platform=strategy.platform)

    return ExplanationResponse(
        platform_choice=platform_choice,
        financial_projection=projection,
        risk_vs_reward=risk_vs_reward,
        area=effective_area,
        generated_at=datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
    )
