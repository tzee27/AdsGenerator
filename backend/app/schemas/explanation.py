from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.content import ContentProduct, ContentVariant
from app.schemas.context import LiveContext
from app.schemas.risk import RiskAnalysisResponse
from app.schemas.strategy import AdStrategy


class PlatformChoice(BaseModel):
    """Why this platform was picked over alternatives."""

    platform: str
    reasons: list[str] = Field(
        default_factory=list,
        description="3-5 short bullet reasons grounded in live context + strategy.",
    )


class FinancialProjection(BaseModel):
    """Deterministic spend → revenue waterfall.

    All numeric fields are computed in Python so the output is reliable and
    auditable. The frontend can render them directly into the 💰 section.
    """

    spend_rm: float
    predicted_reach: int
    click_through_rate: float = Field(description="Decimal, e.g. 0.08 for 8%.")
    predicted_clicks: int
    conversion_rate: float = Field(description="Decimal, e.g. 0.125 for 12.5%.")
    predicted_sales: int
    average_order_value_rm: float
    predicted_revenue_rm: float
    roi_percent: float
    summary_line: str = Field(
        description="One-line human summary, e.g. 'Spend RM80 → 4,200 reach → ...'."
    )


class RiskVsReward(BaseModel):
    risks: list[str] = Field(default_factory=list)
    rewards: list[str] = Field(default_factory=list)
    verdict: str = Field(default="", description="One-sentence go/no-go.")


class ExplanationRequest(BaseModel):
    """Input combining outputs from Parts 1-4."""

    risk_analysis: RiskAnalysisResponse
    live_context: LiveContext
    strategy: AdStrategy
    content_variants: Optional[list[ContentVariant]] = Field(
        default=None,
        description="From Part 4. Optional but recommended for richer prose.",
    )
    product: Optional[ContentProduct] = Field(
        default=None,
        description="Featured product. Used to derive AOV from risk_analysis if known.",
    )
    unit_price_rm: Optional[float] = Field(
        default=None,
        ge=0,
        description="Override AOV. If omitted, derived from risk_analysis or default.",
    )
    area: Optional[str] = None


class ExplanationResponse(BaseModel):
    platform_choice: PlatformChoice
    financial_projection: FinancialProjection
    risk_vs_reward: RiskVsReward
    area: str
    generated_at: str
