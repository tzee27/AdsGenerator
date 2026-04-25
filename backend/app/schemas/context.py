from typing import Optional

from pydantic import BaseModel, Field


class ProductForContext(BaseModel):
    """Minimal product info needed by the live-context gatherer."""

    product: str
    category: Optional[str] = None


class LiveContextRequest(BaseModel):
    """Input for POST /api/v1/context/gather."""

    products: list[ProductForContext] = Field(
        ...,
        min_length=1,
        description="Products to gather context for (usually high/medium risk from Part 1).",
    )
    area: Optional[str] = Field(
        default=None,
        description="Override target region. Defaults to settings.AREA.",
    )


class LiveContext(BaseModel):
    """Structured live context matching the pipeline spec."""

    upcoming_events: list[str] = Field(default_factory=list)
    trending_formats: list[str] = Field(default_factory=list)
    platform_insights: dict[str, str] = Field(default_factory=dict)
    seasonal_opportunity: str = ""


class LiveContextResponse(BaseModel):
    context: LiveContext
    area: str
    web_search_used: bool
    generated_at: str
