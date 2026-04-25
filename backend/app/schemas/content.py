from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.product import ContentProduct
from app.schemas.strategy import AdStrategy

# Re-exported here for backward compat — older imports do
# `from app.schemas.content import ContentProduct`.
__all__ = [
    "ContentGenerationRequest",
    "ContentGenerationResponse",
    "ContentProduct",
    "ContentVariant",
    "GeneratedImage",
]


class ContentVariant(BaseModel):
    """One complete ad copy bundle."""

    headline: str
    caption: str
    call_to_action: str
    hashtags: list[str] = Field(default_factory=list)


class GeneratedImage(BaseModel):
    """Image produced by GLM-Image, either inline or via URL."""

    mime_type: Optional[str] = None
    base64: Optional[str] = None
    url: Optional[str] = None


class ContentGenerationRequest(BaseModel):
    """Input for POST /api/v1/content/generate."""

    strategy: AdStrategy
    product: Optional[ContentProduct] = Field(
        default=None,
        description="Specific product to feature. If omitted, copy will be strategy-driven only.",
    )
    area: Optional[str] = Field(
        default=None,
        description="Override target region; defaults to settings.AREA.",
    )


class ContentGenerationResponse(BaseModel):
    content_variants: list[ContentVariant]
    image_prompt: str
    image: GeneratedImage
    generated_at: str
