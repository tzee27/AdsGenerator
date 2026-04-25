from typing import Optional

from pydantic import BaseModel, Field


class RiskProduct(BaseModel):
    """One product entry in the risk analyser response."""

    product: str
    units: int
    days_to_expiry: Optional[int] = None
    days_unsold: int
    exposure: str = Field(description="Capital exposure formatted as 'RM X,XXX'.")
    risk_score: int = Field(ge=0, le=100)


class RiskAnalysisResponse(BaseModel):
    """Grouped products by risk bucket."""

    high_risk: list[RiskProduct] = Field(default_factory=list)
    medium_risk: list[RiskProduct] = Field(default_factory=list)
    low_risk: list[RiskProduct] = Field(default_factory=list)
