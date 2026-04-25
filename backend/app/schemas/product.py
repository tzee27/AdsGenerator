"""Shared product reference type used across multiple pipeline parts.

Lives in its own module to avoid circular imports between `strategy.py` (which
embeds a featured product per `StrategyOption`) and `content.py` (which used
to define this).
"""

from typing import Optional

from pydantic import BaseModel


class ContentProduct(BaseModel):
    """A featured product threaded through Parts 3, 4, and 5."""

    product: str
    category: Optional[str] = None
