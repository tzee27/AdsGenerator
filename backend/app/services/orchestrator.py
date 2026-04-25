"""Two-phase orchestrator that runs the 5-part pipeline.

Phase A — `run_phase_a(csv)` → Parts 1-3
    Returns 3 diverse `StrategyOption`s (each with its own featured product
    and unit price) so the user can pick before we burn a slow image call.

Phase B — `run_phase_b(selected_strategy, intermediates)` → Parts 4-5
    Generates ad copy + image for the chosen strategy, then renders the
    deterministic financial projection + LLM prose explanation.

Failure policy: **all-or-nothing within each phase**. If any part raises, we
wrap the original exception in `OrchestratorError` carrying the failed-part
name and the set of parts that completed before the break.
"""

from __future__ import annotations

import time
from datetime import date, datetime, timezone
from typing import Callable, Optional

from app.core.config import settings
from app.schemas.ads import (
    FinalizeMetadata,
    FinalizeResponse,
    StrategiesMetadata,
    StrategiesResponse,
)
from app.schemas.content import ContentGenerationResponse
from app.schemas.context import LiveContext, ProductForContext
from app.schemas.explanation import ExplanationResponse
from app.schemas.product import ContentProduct
from app.schemas.risk import RiskAnalysisResponse, RiskProduct
from app.schemas.strategy import StrategyOption
from app.services import glm_image_client as _image
from app.services.content_generator import generate_content
from app.services.context_gatherer import gather_live_context
from app.services.explanation_generator import generate_explanation
from app.services.risk_analyser import (
    ParsedRow,
    RiskAnalyserError,
    analyse_rows,
    parse_csv,
)
from app.services.strategy_decider import decide_strategy

PHASE_A_PARTS = ("risk", "context", "strategy")
PHASE_B_PARTS = ("content", "explanation")
PIPELINE_PARTS = PHASE_A_PARTS + PHASE_B_PARTS

# Hard cap on how many products we hand to the live-context gatherer.
MAX_CONTEXT_PRODUCTS = 8


GlmCallable = Callable[..., dict]
ImageCallable = Callable[..., _image.GeneratedImageResult]


class OrchestratorError(RuntimeError):
    """Raised when one of the pipeline parts fails."""

    def __init__(
        self,
        *,
        failed_part: str,
        original: BaseException,
        completed: dict[str, bool],
        featured_product: Optional[ContentProduct] = None,
        area: Optional[str] = None,
    ) -> None:
        super().__init__(f"Pipeline failed at '{failed_part}': {original}")
        self.failed_part = failed_part
        self.original = original
        self.completed = completed
        self.featured_product = featured_product
        self.area = area


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso_z() -> str:
    return (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )


def _ms_since(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def _products_for_context(
    risk: RiskAnalysisResponse, rows: list[ParsedRow]
) -> list[ProductForContext]:
    """Pick the top high+medium-risk products to feed Part 2."""
    by_name = {row.product.strip().lower(): row for row in rows}
    chosen: list[ProductForContext] = []

    def _add(items: list[RiskProduct]) -> None:
        for p in items:
            row = by_name.get(p.product.strip().lower())
            chosen.append(
                ProductForContext(
                    product=p.product,
                    category=(row.category or None) if row else None,
                )
            )
            if len(chosen) >= MAX_CONTEXT_PRODUCTS:
                return

    _add(risk.high_risk)
    if len(chosen) < MAX_CONTEXT_PRODUCTS:
        _add(risk.medium_risk)
    if not chosen:
        _add(risk.low_risk)
    return chosen


def _enrich_strategies_with_categories(
    strategies: list[StrategyOption], rows: list[ParsedRow]
) -> list[StrategyOption]:
    """Backfill `featured_product.category` from the parsed CSV rows.

    The strategy decider only sees risk products (which drop the category
    column to keep the prompt short), so we inject categories here so
    Phase B can pass them down to content generation for richer copy.
    """
    by_name = {row.product.strip().lower(): row for row in rows}
    enriched: list[StrategyOption] = []
    for opt in strategies:
        match = by_name.get(opt.featured_product.product.strip().lower())
        if match is None or not match.category:
            enriched.append(opt)
            continue
        enriched.append(
            opt.model_copy(
                update={
                    "featured_product": ContentProduct(
                        product=opt.featured_product.product,
                        category=match.category,
                    ),
                    "unit_price_rm": (
                        opt.unit_price_rm
                        if opt.unit_price_rm > 0
                        else round(match.price, 2)
                    ),
                }
            )
        )
    return enriched


# ---------------------------------------------------------------------------
# Phase A — Risk + Context + Strategies
# ---------------------------------------------------------------------------


def run_phase_a(
    csv_content: str,
    *,
    area: Optional[str] = None,
    today: Optional[date] = None,
    count: int = 2,
    glm_fn: Optional[GlmCallable] = None,
) -> StrategiesResponse:
    """Run Parts 1-3 against an inventory CSV.

    Args:
        csv_content: Raw CSV string (already decoded as UTF-8).
        area: Override target region; falls back to `settings.AREA`.
        today: Override reference date.
        count: How many strategy options to generate (1-5, clamped).
        glm_fn: Inject a fake GLM callable for tests.

    Raises:
        RiskAnalyserError: bad CSV (caller maps to 422).
        OrchestratorError: Part 2 or 3 failed upstream.
    """
    effective_area = (area or settings.AREA or "Malaysia").strip() or "Malaysia"
    reference_date = today or date.today()

    timing_ms: dict[str, int] = {}
    completed: dict[str, bool] = {part: False for part in PHASE_A_PARTS}

    # Part 1 — risk
    t0 = time.perf_counter()
    rows = parse_csv(csv_content)
    risk = analyse_rows(rows, today=reference_date)
    timing_ms["risk"] = _ms_since(t0)
    completed["risk"] = True

    context_products = _products_for_context(risk, rows)

    # Part 2 — live context
    t1 = time.perf_counter()
    try:
        context_response = gather_live_context(
            context_products,
            area=effective_area,
            today=reference_date,
            glm_fn=glm_fn,
        )
    except Exception as exc:
        raise OrchestratorError(
            failed_part="context",
            original=exc,
            completed=completed,
            area=effective_area,
        ) from exc
    live_context: LiveContext = context_response.context
    timing_ms["context"] = _ms_since(t1)
    completed["context"] = True

    # Part 3 — strategies (now plural)
    price_lookup = {row.product.strip().lower(): row.price for row in rows}
    t2 = time.perf_counter()
    try:
        strategy_response = decide_strategy(
            risk,
            live_context,
            area=effective_area,
            today=reference_date,
            count=count,
            glm_fn=glm_fn,
            unit_price_lookup=price_lookup,
        )
    except Exception as exc:
        raise OrchestratorError(
            failed_part="strategy",
            original=exc,
            completed=completed,
            area=effective_area,
        ) from exc
    timing_ms["strategy"] = _ms_since(t2)
    completed["strategy"] = True

    strategies = _enrich_strategies_with_categories(
        strategy_response.strategies, rows
    )

    metadata = StrategiesMetadata(
        area=effective_area,
        timing_ms=timing_ms,
        generated_at=_now_iso_z(),
    )

    return StrategiesResponse(
        risk_analysis=risk,
        live_context=live_context,
        strategies=strategies,
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# Phase B — Content + Explanation
# ---------------------------------------------------------------------------


def run_phase_b(
    *,
    selected: StrategyOption,
    risk: RiskAnalysisResponse,
    context: LiveContext,
    area: Optional[str] = None,
    today: Optional[date] = None,
    glm_fn: Optional[GlmCallable] = None,
    image_fn: Optional[ImageCallable] = None,
) -> FinalizeResponse:
    """Run Parts 4-5 for the chosen strategy.

    Args:
        selected: The StrategyOption the user picked from Phase A.
        risk: Echo of the Phase A risk analysis (for explanation prose).
        context: Echo of the Phase A live context (for explanation prose).
        area: Override target region.
        today: Override reference date.
        glm_fn: Inject a fake GLM callable for tests.
        image_fn: Inject a fake image generator for tests.

    Raises:
        OrchestratorError: Part 4 or 5 failed upstream.
    """
    effective_area = (area or settings.AREA or "Malaysia").strip() or "Malaysia"
    reference_date = today or date.today()

    timing_ms: dict[str, int] = {}
    completed: dict[str, bool] = {part: False for part in PHASE_B_PARTS}
    featured = selected.featured_product

    # Part 4 — content + image
    t0 = time.perf_counter()
    try:
        content: ContentGenerationResponse = generate_content(
            selected.strategy,
            product=featured,
            area=effective_area,
            today=reference_date,
            glm_fn=glm_fn,
            image_fn=image_fn,
        )
    except Exception as exc:
        raise OrchestratorError(
            failed_part="content",
            original=exc,
            completed=completed,
            featured_product=featured,
            area=effective_area,
        ) from exc
    timing_ms["content"] = _ms_since(t0)
    completed["content"] = True

    # Part 5 — explanation
    t1 = time.perf_counter()
    try:
        explanation: ExplanationResponse = generate_explanation(
            risk=risk,
            context=context,
            strategy=selected.strategy,
            variants=content.content_variants,
            product=featured,
            unit_price_rm=selected.unit_price_rm,
            area=effective_area,
            today=reference_date,
            glm_fn=glm_fn,
        )
    except Exception as exc:
        raise OrchestratorError(
            failed_part="explanation",
            original=exc,
            completed=completed,
            featured_product=featured,
            area=effective_area,
        ) from exc
    timing_ms["explanation"] = _ms_since(t1)
    completed["explanation"] = True

    metadata = FinalizeMetadata(
        area=effective_area,
        featured_product=featured,
        unit_price_rm=round(selected.unit_price_rm, 2),
        timing_ms=timing_ms,
        generated_at=_now_iso_z(),
    )

    return FinalizeResponse(
        content=content,
        explanation=explanation,
        metadata=metadata,
    )


__all__ = [
    "OrchestratorError",
    "PHASE_A_PARTS",
    "PHASE_B_PARTS",
    "PIPELINE_PARTS",
    "RiskAnalyserError",
    "run_phase_a",
    "run_phase_b",
]
