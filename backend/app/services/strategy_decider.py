"""Part 3 — Decide Ads Strategies.

Given the risk analysis from Part 1 and the live market context from Part 2,
asks GLM-5.1 for N **diverse** ad strategies that the user can pick from. Each
strategy comes paired with the product it features and a short rationale.

Web search is intentionally disabled — Part 2 already gathered fresh context
and we don't want the model re-fetching during strategy decisions.

A single GLM round-trip returns the whole list (cheaper + faster than N
parallel calls). Diversity is enforced post-hoc: if the model returns two
strategies that target the same product+platform, we replace the duplicate
with the next-best risk product on a different platform.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Callable, Optional

from pydantic import ValidationError

from app.core.config import settings
from app.schemas.context import LiveContext
from app.schemas.product import ContentProduct
from app.schemas.risk import RiskAnalysisResponse, RiskProduct
from app.schemas.strategy import AdStrategy, StrategyOption, StrategyResponse
from app.services import glm_client as _glm

DEFAULT_STRATEGY_COUNT = 2
MAX_STRATEGY_COUNT = 5
DEFAULT_PLATFORM_FALLBACKS = ["TikTok", "Facebook", "Instagram", "Shopee", "Lazada"]
DEFAULT_AOV_RM = 50.0


SYSTEM_PROMPT = """You are a senior performance-marketing strategist.
Given an inventory risk analysis and today's live market context, you must
propose N **diverse** advertising strategies that a hackathon team can pick
from. Each strategy should be a different combination of product + platform
+ angle. You must reply with a single JSON object only — no prose, no
markdown fences, no explanations."""


def _json_schema_hint(count: int) -> str:
    return (
        "Return EXACTLY this JSON shape (no markdown, no prose, no code fences):\n"
        "{\n"
        '  "strategies": [\n'
        '    {\n'
        '      "featured_product": "<exact product name from the risk lists>",\n'
        '      "rationale": "<1-2 sentences: why THIS product on THIS platform now>",\n'
        '      "strategy": {\n'
        '        "platform": "<one of TikTok | Facebook | Instagram | Shopee | Lazada>",\n'
        '        "format": "<Short Video | Image | Carousel | Text | Reel | Story>",\n'
        '        "audience": "<e.g. \'Males 18-30, tech interest\'>",\n'
        '        "pricing": "<e.g. \'Bundle 3 for price of 2\', \'Flash Sale 30%\'>",\n'
        '        "timing": "<e.g. \'Friday 8PM, 5 days\'>",\n'
        '        "budget": "RM <integer>",\n'
        '        "angle": "<short creative hook, <= 8 words>",\n'
        '        "predicted_reach": <integer, estimated people reached>,\n'
        '        "predicted_roi": "<integer>%"\n'
        "      }\n"
        "    }\n"
        f"    // ... exactly {count} entries total, each meaningfully different ...\n"
        "  ]\n"
        "}"
    )


RULES_TEMPLATE = """Rules:
- Generate EXACTLY {count} strategies. Do not skip; do not exceed.
- Strategies MUST be meaningfully diverse. Try to vary combinations of:
    (a) which product is featured,
    (b) which platform is chosen,
    (c) which creative angle is taken.
  At minimum no two strategies may share the same (product, platform) pair.
- Prefer products from `high_risk` first; use `medium_risk` if there aren't enough
  high-risk products to fill {count} distinct entries; only use `low_risk` as a
  last resort.
- `featured_product` MUST exactly match a product name from the risk lists
  (case-sensitive). Do NOT invent product names.
- `predicted_reach` must be a plain integer (no commas, no 'k').
- `predicted_roi` must be a string like "688%".
- `budget` must start with "RM " and be a whole ringgit amount (no decimals).
- Base your reach/ROI heuristics on the platform_insights CPM values in the
  context when available. Be reasonable, not fantastical.
- Tie at least one strategy's `angle` to the nearest upcoming_event or to the
  seasonal_opportunity.
- `rationale`: 1-2 short sentences. Reference the risk score and one concrete
  context signal (CPM, trend name, peak time). No fluff.
- Output RAW JSON only. No code fences, no commentary."""


def _format_risk_summary(risk: RiskAnalysisResponse) -> str:
    """Compact textual summary fed to the model."""

    def _rows(items, bucket_label: str) -> list[str]:
        if not items:
            return [f"{bucket_label}: (none)"]
        rows = [f"{bucket_label}:"]
        for p in items[:5]:
            expiry = (
                f"{p.days_to_expiry}d to expiry"
                if p.days_to_expiry is not None
                else "no expiry"
            )
            rows.append(
                f"  - {p.product} | {p.units} units | {expiry} | "
                f"{p.days_unsold}d unsold | exposure {p.exposure} | "
                f"risk {p.risk_score}"
            )
        if len(items) > 5:
            rows.append(f"  ... and {len(items) - 5} more")
        return rows

    lines = []
    lines += _rows(risk.high_risk, "HIGH RISK")
    lines += _rows(risk.medium_risk, "MEDIUM RISK")
    lines += _rows(risk.low_risk, "LOW RISK")
    return "\n".join(lines)


def _format_context_summary(ctx: LiveContext) -> str:
    parts: list[str] = []
    if ctx.upcoming_events:
        parts.append("Upcoming events: " + "; ".join(ctx.upcoming_events))
    if ctx.trending_formats:
        parts.append("Trending formats: " + "; ".join(ctx.trending_formats))
    if ctx.platform_insights:
        insight_lines = [f"  - {k}: {v}" for k, v in ctx.platform_insights.items()]
        parts.append("Platform insights:\n" + "\n".join(insight_lines))
    if ctx.seasonal_opportunity:
        parts.append(f"Seasonal opportunity: {ctx.seasonal_opportunity}")
    return "\n".join(parts) if parts else "(no live context available)"


def _build_user_prompt(
    *,
    area: str,
    today: date,
    risk: RiskAnalysisResponse,
    context: LiveContext,
    count: int,
) -> str:
    return (
        f"Today is {today.isoformat()}. Target region: {area}.\n\n"
        f"--- INVENTORY RISK ANALYSIS ---\n{_format_risk_summary(risk)}\n\n"
        f"--- LIVE MARKET CONTEXT ---\n{_format_context_summary(context)}\n\n"
        f"Decide {count} diverse ad strategies for the team to choose from.\n\n"
        f"{_json_schema_hint(count)}\n\n{RULES_TEMPLATE.format(count=count)}"
    )


# ---------------------------------------------------------------------------
# Coercion helpers (mirror the older single-strategy normaliser)
# ---------------------------------------------------------------------------


def _coerce_reach(value) -> int:
    if isinstance(value, int):
        return max(0, value)
    if isinstance(value, float):
        return max(0, int(round(value)))
    if isinstance(value, str):
        cleaned = re.sub(r"[^\d]", "", value)
        return int(cleaned) if cleaned else 0
    return 0


def _coerce_roi(value) -> str:
    if isinstance(value, (int, float)):
        return f"{int(round(value))}%"
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.endswith("%"):
            return stripped
        cleaned = re.sub(r"[^\d]", "", stripped)
        if cleaned:
            return f"{cleaned}%"
    return "0%"


def _coerce_budget(value) -> str:
    if isinstance(value, (int, float)):
        return f"RM {int(round(value))}"
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.upper().startswith("RM"):
            amount = re.sub(r"[^\d]", "", stripped)
            return f"RM {int(amount)}" if amount else "RM 0"
        cleaned = re.sub(r"[^\d]", "", stripped)
        return f"RM {int(cleaned)}" if cleaned else "RM 0"
    return "RM 0"


def _coerce_strategy(raw: dict) -> AdStrategy:
    """Normalize a single strategy dict into our strict schema."""
    payload = raw if isinstance(raw, dict) else {}
    try:
        return AdStrategy(
            platform=str(payload.get("platform") or "").strip() or "TikTok",
            format=str(payload.get("format") or "").strip() or "Short Video",
            audience=str(payload.get("audience") or "").strip() or "General audience",
            pricing=str(payload.get("pricing") or "").strip() or "Full price",
            timing=str(payload.get("timing") or "").strip() or "This weekend",
            budget=_coerce_budget(payload.get("budget")),
            angle=str(payload.get("angle") or "").strip() or "Limited time offer",
            predicted_reach=_coerce_reach(payload.get("predicted_reach")),
            predicted_roi=_coerce_roi(payload.get("predicted_roi")),
        )
    except ValidationError as exc:
        raise ValueError(f"Strategy JSON failed validation: {exc}") from exc


# ---------------------------------------------------------------------------
# Featured-product matching (against the parsed risk catalogue)
# ---------------------------------------------------------------------------


def _flatten_risk_products(risk: RiskAnalysisResponse) -> list[RiskProduct]:
    """All products in priority order: high-risk first, then medium, then low."""
    return [*risk.high_risk, *risk.medium_risk, *risk.low_risk]


def _find_risk_product(name: str, catalogue: list[RiskProduct]) -> Optional[RiskProduct]:
    target = name.strip().lower()
    if not target:
        return None
    for p in catalogue:
        if p.product.strip().lower() == target:
            return p
    return None


def _unit_price_from_risk(p: RiskProduct) -> float:
    """Reverse-engineer unit price from the formatted exposure string."""
    cleaned = re.sub(r"[^\d.]", "", p.exposure or "")
    try:
        exposure = float(cleaned) if cleaned else 0.0
    except ValueError:
        exposure = 0.0
    if exposure > 0 and p.units > 0:
        return round(exposure / p.units, 2)
    return DEFAULT_AOV_RM


def _coerce_option(
    raw: dict,
    *,
    catalogue: list[RiskProduct],
    fallback_product: Optional[RiskProduct],
    unit_price_lookup: dict[str, float],
) -> StrategyOption:
    """Build one StrategyOption, snapping to a real catalogue product if possible."""
    strategy = _coerce_strategy(raw.get("strategy") if isinstance(raw.get("strategy"), dict) else raw)

    requested_name = str(raw.get("featured_product") or "").strip()
    matched = _find_risk_product(requested_name, catalogue) if requested_name else None
    if matched is None:
        matched = fallback_product

    if matched is None:
        # Catalogue is somehow empty — synthesize a placeholder so we don't crash.
        product = ContentProduct(product=requested_name or "Unknown", category=None)
        unit_price = DEFAULT_AOV_RM
    else:
        product = ContentProduct(product=matched.product, category=None)
        unit_price = unit_price_lookup.get(
            matched.product.strip().lower(), _unit_price_from_risk(matched)
        )

    rationale = str(raw.get("rationale") or "").strip()

    return StrategyOption(
        strategy=strategy,
        featured_product=product,
        unit_price_rm=round(unit_price, 2),
        rationale=rationale,
    )


def _enforce_diversity(
    options: list[StrategyOption],
    *,
    catalogue: list[RiskProduct],
    unit_price_lookup: dict[str, float],
    target_count: int,
) -> list[StrategyOption]:
    """Drop (product, platform) duplicates and pad up to target_count from catalogue."""
    seen_pairs: set[tuple[str, str]] = set()
    unique: list[StrategyOption] = []
    for opt in options:
        key = (
            opt.featured_product.product.strip().lower(),
            opt.strategy.platform.strip().lower(),
        )
        if key in seen_pairs:
            continue
        seen_pairs.add(key)
        unique.append(opt)
        if len(unique) >= target_count:
            break

    if len(unique) >= target_count:
        return unique[:target_count]

    # Pad: cycle through remaining catalogue products on alternate platforms so
    # we always return the requested count even when the model under-delivers.
    seen_products = {opt.featured_product.product.strip().lower() for opt in unique}
    fallback_idx = 0
    for product in catalogue:
        if len(unique) >= target_count:
            break
        if product.product.strip().lower() in seen_products:
            continue

        platform = DEFAULT_PLATFORM_FALLBACKS[
            fallback_idx % len(DEFAULT_PLATFORM_FALLBACKS)
        ]
        fallback_idx += 1

        # Don't synthesise a duplicate (product, platform) pair.
        pair = (product.product.strip().lower(), platform.lower())
        while pair in seen_pairs and fallback_idx < len(DEFAULT_PLATFORM_FALLBACKS) * 2:
            platform = DEFAULT_PLATFORM_FALLBACKS[
                fallback_idx % len(DEFAULT_PLATFORM_FALLBACKS)
            ]
            fallback_idx += 1
            pair = (product.product.strip().lower(), platform.lower())

        unit_price = unit_price_lookup.get(
            product.product.strip().lower(), _unit_price_from_risk(product)
        )
        unique.append(
            StrategyOption(
                strategy=AdStrategy(
                    platform=platform,
                    format="Short Video" if platform == "TikTok" else "Image",
                    audience="General shoppers",
                    pricing="Full price",
                    timing="This weekend",
                    budget="RM 50",
                    angle=f"Move {product.product} fast",
                    predicted_reach=max(500, int(product.risk_score * 30)),
                    predicted_roi="200%",
                ),
                featured_product=ContentProduct(product=product.product, category=None),
                unit_price_rm=round(unit_price, 2),
                rationale=(
                    "Auto-padded fallback because the model returned fewer than "
                    f"{target_count} distinct strategies."
                ),
            )
        )
        seen_products.add(product.product.strip().lower())
        seen_pairs.add(pair)

    return unique[:target_count]


# ---------------------------------------------------------------------------
# Public service entry point
# ---------------------------------------------------------------------------


GlmCallable = Callable[..., dict]


def decide_strategy(
    risk: RiskAnalysisResponse,
    context: LiveContext,
    *,
    area: Optional[str] = None,
    today: Optional[date] = None,
    count: int = DEFAULT_STRATEGY_COUNT,
    glm_fn: Optional[GlmCallable] = None,
    unit_price_lookup: Optional[dict[str, float]] = None,
) -> StrategyResponse:
    """Decide N diverse ad strategies from Part 1 + Part 2 outputs.

    Args:
        risk: Output of Part 1.
        context: Output of Part 2.
        area: Override target region; defaults to settings.AREA.
        today: Override reference date (used in the prompt).
        count: How many strategies to ask for. Clamped to [1, 5].
        glm_fn: Inject a fake GLM callable for tests.
        unit_price_lookup: Optional `{product_name_lower: price_rm}` so the
            orchestrator can hand in CSV prices instead of having us
            reverse-engineer them from the risk exposure string.
    """
    effective_area = (area or settings.AREA or "Malaysia").strip() or "Malaysia"
    reference_date = today or date.today()
    target_count = max(1, min(int(count), MAX_STRATEGY_COUNT))
    call_glm: GlmCallable = glm_fn or _glm.chat_json
    price_lookup = {k.strip().lower(): v for k, v in (unit_price_lookup or {}).items()}

    catalogue = _flatten_risk_products(risk)
    fallback_product = catalogue[0] if catalogue else None

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": _build_user_prompt(
                area=effective_area,
                today=reference_date,
                risk=risk,
                context=context,
                count=target_count,
            ),
        },
    ]

    raw = call_glm(messages, enable_web_search=False, temperature=0.6)

    raw_options = raw.get("strategies") if isinstance(raw.get("strategies"), list) else None
    if not raw_options:
        # Backward-compat: tolerate the old single-strategy shape too.
        if isinstance(raw.get("strategy"), dict):
            raw_options = [{"strategy": raw["strategy"], "featured_product": (fallback_product.product if fallback_product else "")}]
        else:
            raw_options = []

    options = [
        _coerce_option(
            opt if isinstance(opt, dict) else {},
            catalogue=catalogue,
            fallback_product=fallback_product,
            unit_price_lookup=price_lookup,
        )
        for opt in raw_options
    ]

    options = _enforce_diversity(
        options,
        catalogue=catalogue,
        unit_price_lookup=price_lookup,
        target_count=target_count,
    )

    if not options:
        raise ValueError("Strategy decider returned no usable options.")

    return StrategyResponse(
        strategies=options,
        area=effective_area,
        generated_at=datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
    )
