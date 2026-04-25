"""Schemas for the two-phase orchestrator.

The pipeline is split into:
  Phase A — `POST /api/v1/ads/strategies`: Parts 1-3 (risk → context → 3 strategy options)
  Phase B — `POST /api/v1/ads/finalize`:   Parts 4-5 (content + image → explanation)

The frontend keeps the Phase A response in memory, lets the user pick a
StrategyOption, then sends back the chosen option + the intermediates we need
to feed Parts 4 and 5.
"""

from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.content import ContentGenerationResponse
from app.schemas.context import LiveContext
from app.schemas.explanation import ExplanationResponse
from app.schemas.product import ContentProduct
from app.schemas.risk import RiskAnalysisResponse
from app.schemas.strategy import StrategyOption


# ---------------------------------------------------------------------------
# Phase A — Strategies
# ---------------------------------------------------------------------------


class StrategiesMetadata(BaseModel):
    """Cross-cutting info about the Phase A run."""

    area: str
    timing_ms: dict[str, int] = Field(default_factory=dict)
    generated_at: str


class StrategiesResponse(BaseModel):
    """Phase A response: shows 3 strategy options for the user to pick."""

    risk_analysis: RiskAnalysisResponse
    live_context: LiveContext
    strategies: list[StrategyOption] = Field(
        ...,
        min_length=1,
        description="Diverse strategy options. Each has its own featured product.",
    )
    metadata: StrategiesMetadata


# ---------------------------------------------------------------------------
# Phase B — Finalize
# ---------------------------------------------------------------------------


class FinalizeRequest(BaseModel):
    """Phase B input — pass the chosen StrategyOption back along with
    the Phase A intermediates so the backend doesn't need to re-do Parts 1-3."""

    selected_strategy: StrategyOption
    risk_analysis: RiskAnalysisResponse = Field(
        ..., description="Echo from Phase A so explanation prose can reference it."
    )
    live_context: LiveContext = Field(
        ..., description="Echo from Phase A so explanation prose can reference it."
    )
    area: Optional[str] = Field(
        default=None,
        description="Override target region; defaults to settings.AREA.",
    )


class FinalizeMetadata(BaseModel):
    area: str
    featured_product: ContentProduct
    unit_price_rm: float = Field(ge=0)
    timing_ms: dict[str, int] = Field(default_factory=dict)
    generated_at: str


class FinalizeResponse(BaseModel):
    """Phase B response: full ad copy, image, and financial explanation."""

    content: ContentGenerationResponse
    explanation: ExplanationResponse
    metadata: FinalizeMetadata


# ---------------------------------------------------------------------------
# Error envelope used by both phases
# ---------------------------------------------------------------------------


class AdsGenerationErrorDetail(BaseModel):
    """Structured detail returned when a phase fails partway."""

    failed_part: str = Field(
        description="Which part failed: 'risk' | 'context' | 'strategy' | 'content' | 'explanation'."
    )
    error: str
    completed: dict[str, bool] = Field(default_factory=dict)
    featured_product: Optional[ContentProduct] = None
    area: Optional[str] = None
