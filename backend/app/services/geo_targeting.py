"""Geo targeting helper using GLM web search + Firestore cache."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from typing import Any, Optional

from app.core.firebase import get_db
from app.services import glm_client as _glm

CACHE_COLLECTION = "geoCache"
CACHE_TTL_HOURS = 24


@dataclass(slots=True)
class GeoTargetingResult:
    success: bool
    data: dict[str, Any]
    source: str


def _cache_key(product_name: str, store_location: str) -> str:
    return f"{product_name}_{store_location}".replace(" ", "_").lower()


def _today_label() -> str:
    return datetime.now().strftime("%d %B %Y")


def _fallback_result(
    product_name: str, product_category: str, store_location: str
) -> dict[str, Any]:
    return {
        "targetZones": [],
        "avoidZones": [],
        "recommendedRadiusKm": 5,
        "targetDemographic": {
            "ageRange": "25-45",
            "gender": "All",
            "interests": [product_category or "General shoppers"],
            "language": "Malay",
        },
        "bestPlatform": "Facebook",
        "bestTiming": "Weekday evenings 7-10PM",
        "adLanguage": "Malay",
        "overallConfidence": "LOW",
        "searchSummary": "Search unavailable at this time.",
        "reasoning": (
            f"Default targeting applied for {product_name} in {store_location}. "
            "Please retry for better results."
        ),
    }


def _normalize_zone(zone: Any) -> Optional[dict[str, Any]]:
    if isinstance(zone, str):
        area = zone.strip()
        if not area:
            return None
        return {"area": area, "reason": "Matched from live search trends.", "confidence": 60}
    if isinstance(zone, dict):
        area = str(zone.get("area") or zone.get("zone") or zone.get("name") or "").strip()
        if not area:
            return None
        reason = str(
            zone.get("reason")
            or zone.get("why")
            or zone.get("rationale")
            or "Matched from live search trends."
        ).strip()
        confidence_raw = zone.get("confidence", zone.get("score", 60))
        try:
            confidence = int(float(confidence_raw))
        except (TypeError, ValueError):
            confidence = 60
        confidence = max(0, min(100, confidence))
        return {"area": area, "reason": reason, "confidence": confidence}
    return None


def _normalize_geo_result(raw: dict[str, Any]) -> dict[str, Any]:
    target = [_normalize_zone(z) for z in (raw.get("targetZones") or [])]
    avoid = [_normalize_zone(z) for z in (raw.get("avoidZones") or [])]
    target = [z for z in target if z is not None]
    avoid = [z for z in avoid if z is not None]

    demographic_raw = raw.get("targetDemographic")
    demographic = demographic_raw if isinstance(demographic_raw, dict) else {}
    interests = demographic.get("interests")
    if not isinstance(interests, list):
        interests = [str(interests)] if interests else []

    confidence = str(raw.get("overallConfidence") or "LOW").strip().upper()
    if confidence not in {"HIGH", "MEDIUM", "LOW"}:
        confidence = "LOW"

    try:
        radius = int(float(raw.get("recommendedRadiusKm", 5)))
    except (TypeError, ValueError):
        radius = 5
    radius = max(1, min(100, radius))

    return {
        "targetZones": target,
        "avoidZones": avoid,
        "recommendedRadiusKm": radius,
        "targetDemographic": {
            "ageRange": str(demographic.get("ageRange") or "25-45"),
            "gender": str(demographic.get("gender") or "All"),
            "interests": [str(x) for x in interests if str(x).strip()],
            "language": str(demographic.get("language") or "Malay"),
        },
        "bestPlatform": str(raw.get("bestPlatform") or "Facebook"),
        "bestTiming": str(raw.get("bestTiming") or "Weekday evenings 7-10PM"),
        "adLanguage": str(raw.get("adLanguage") or "Malay"),
        "overallConfidence": confidence,
        "searchSummary": str(raw.get("searchSummary") or "No search summary available."),
        "reasoning": str(raw.get("reasoning") or "No reasoning provided."),
    }


def _read_cache(product_name: str, store_location: str) -> Optional[GeoTargetingResult]:
    try:
        doc_ref = get_db().collection(CACHE_COLLECTION).document(
            _cache_key(product_name, store_location)
        )
        snap = doc_ref.get()
        if not snap.exists:
            return None
        payload = snap.to_dict() or {}
        cached_at = int(payload.get("cachedAt") or 0)
        age_hours = (datetime.now().timestamp() * 1000 - cached_at) / (1000 * 60 * 60)
        if age_hours >= CACHE_TTL_HOURS:
            return None
        result = payload.get("result")
        if isinstance(result, dict):
            return GeoTargetingResult(
                success=True, data=_normalize_geo_result(result), source="cache"
            )
    except Exception:
        return None
    return None


def _write_cache(product_name: str, store_location: str, result: dict[str, Any]) -> None:
    try:
        get_db().collection(CACHE_COLLECTION).document(
            _cache_key(product_name, store_location)
        ).set(
            {
                "result": result,
                "cachedAt": int(datetime.now().timestamp() * 1000),
                "productName": product_name,
                "storeLocation": store_location,
            }
        )
    except Exception:
        # Cache writes must never break pipeline.
        return


def get_geo_targeting(
    *,
    product_name: str,
    product_category: str,
    store_location: str,
    primary_customers: str = "Mixed",
) -> GeoTargetingResult:
    """Get geo recommendation with 24h cache + strict web-search prompting."""
    cached = _read_cache(product_name, store_location)
    if cached is not None:
        return cached

    today = _today_label()
    year = datetime.now().year

    system_prompt = f"""
You are a geo-targeting specialist for Malaysian retail advertising. Today's date is {today}.

Your job is to research and decide the most effective geographic targeting for a product ad in Malaysia.
You MUST use web search to find current real information.

You must perform ALL of these searches before answering:
SEARCH 1: "{product_name} popular demand which area Malaysia {year}"
SEARCH 2: "demographic breakdown {store_location} Malaysia population ethnicity"
SEARCH 3: "best areas to advertise {product_category} near {store_location} Malaysia"
SEARCH 4: "who buys {product_name} Malaysia age group income level"
SEARCH 5: "best time to post {product_category} ads Facebook TikTok Malaysia {year}"

Return ONLY raw JSON. No prose, no code fences.
    """.strip()

    user_prompt = f"""
Determine the best geo targeting for this ad:
Product: {product_name}
Category: {product_category}
Seller location: {store_location}
Seller's current customers: {primary_customers}
Today's date: {today}

Return JSON with:
targetZones, avoidZones, recommendedRadiusKm, targetDemographic, bestPlatform,
bestTiming, adLanguage, overallConfidence, searchSummary, reasoning.

targetZones and avoidZones must be arrays of objects:
{{"area":"...","reason":"...","confidence":0-100}}
    """.strip()

    try:
        result = _glm.chat_json(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            enable_web_search=True,
            temperature=0.4,
        )
        normalized = _normalize_geo_result(result)
        _write_cache(product_name, store_location, normalized)
        return GeoTargetingResult(
            success=True, data=normalized, source="glm_web_search"
        )
    except Exception:
        try:
            retry = _glm.chat_json(
                [
                    {
                        "role": "system",
                        "content": "Use web search and return only raw JSON for geo targeting.",
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Find geo targeting for {product_name} in {store_location}, Malaysia. "
                            "Return JSON with targetZones, avoidZones, recommendedRadiusKm, "
                            "targetDemographic, bestPlatform, bestTiming, adLanguage, "
                            "overallConfidence, searchSummary, reasoning."
                        ),
                    },
                ],
                enable_web_search=True,
                temperature=0.3,
            )
            normalized_retry = _normalize_geo_result(retry)
            _write_cache(product_name, store_location, normalized_retry)
            return GeoTargetingResult(
                success=True, data=normalized_retry, source="glm_retry"
            )
        except Exception:
            return GeoTargetingResult(
                success=False,
                data=_fallback_result(product_name, product_category, store_location),
                source="fallback_defaults",
            )


def build_geo_context(geo_results: list[dict[str, Any]]) -> str:
    """Format geo recommendations into prompt context for Part 3."""
    lines = ["LIVE GEO TARGETING DATA (from web search today):"]
    for item in geo_results:
        product = item.get("product", "Unknown")
        source = item.get("source", "unknown")
        geo = item.get("geo", {}) if isinstance(item.get("geo"), dict) else {}
        target = ", ".join(
            z.get("area", "")
            for z in (geo.get("targetZones") or [])
            if isinstance(z, dict) and z.get("area")
        )
        avoid = ", ".join(
            z.get("area", "")
            for z in (geo.get("avoidZones") or [])
            if isinstance(z, dict) and z.get("area")
        )
        lines.append(f"- Product: {product} (source: {source})")
        lines.append(f"  Target areas: {target or 'None'}")
        lines.append(f"  Avoid areas: {avoid or 'None'}")
        lines.append(f"  Best platform: {geo.get('bestPlatform', 'Unknown')}")
        lines.append(f"  Best timing: {geo.get('bestTiming', 'Unknown')}")
        demographic = geo.get("targetDemographic", {})
        lines.append(f"  Target demographic: {json.dumps(demographic)}")
        lines.append(f"  Recommended ad language: {geo.get('adLanguage', 'Unknown')}")
        lines.append(f"  Confidence: {geo.get('overallConfidence', 'LOW')}")
    lines.append(
        "Use this geo data to inform platform choice, audience targeting, timing, and ad language decisions."
    )
    return "\n".join(lines)
