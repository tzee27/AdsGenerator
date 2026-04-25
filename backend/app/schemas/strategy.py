from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.context import LiveContext
from app.schemas.product import ContentProduct
from app.schemas.risk import RiskAnalysisResponse


class AdStrategy(BaseModel):
    """The core strategy fields the LLM must commit to."""

    platform: str = Field(description="e.g. 'TikTok', 'Facebook', 'Instagram'")
    format: str = Field(description="e.g. 'Short Video', 'Image', 'Carousel'")
    audience: str = Field(description="Short description: age/gender/interest")
    pricing: str = Field(description="Pricing mechanic: Discount, Bundle, Flash Sale, ...")
    timing: str = Field(description="Day+time+duration phrase, e.g. 'Friday 8PM, 5 days'")
    budget: str = Field(description="Budget string like 'RM 80'")
    angle: str = Field(description="Creative hook / angle, e.g. 'Raya gift idea'")
    predicted_reach: int = Field(ge=0, description="Estimated people reached")
    predicted_roi: str = Field(description="ROI as percent string, e.g. '1850%'")


class StrategyOption(BaseModel):
    """One end-to-end strategy choice the user can pick from.

    Bundles the strategy itself with the product it features and the price we
    derived from the CSV, so Phase B doesn't need to re-look-up anything.
    """

    strategy: AdStrategy
    featured_product: ContentProduct
    unit_price_rm: float = Field(
        ge=0, description="Featured product's unit price (drives Phase B's AOV calc)."
    )
    rationale: str = Field(
        default="",
        description="Short 1-2 sentence justification grounded in the risk + context inputs.",
    )


class StrategyRequest(BaseModel):
    """Input combining Part 1 risk output with Part 2 live context."""

    risk_analysis: RiskAnalysisResponse
    live_context: LiveContext
    area: Optional[str] = Field(
        default=None,
        description="Override target region; defaults to settings.AREA.",
    )
    count: int = Field(
        default=2,
        ge=1,
        le=5,
        description="How many distinct strategies to generate.",
    )


class StrategyResponse(BaseModel):
    """Now returns N strategy options for the user to choose from."""

    strategies: list[StrategyOption] = Field(
        ...,
        min_length=1,
        description="Diverse strategy options. Strategies should differ meaningfully in product/platform/angle.",
    )
    area: str
    generated_at: str
