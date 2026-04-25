"""Part 1 — Risk Analyser.

Reads a product inventory CSV and groups items into high / medium / low risk
buckets based on a deterministic formula. This deliberately does not call an
LLM — risk is math, not opinion. Later pipeline parts (strategy, generation,
explanation) are where GLM comes in.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from app.schemas.risk import RiskAnalysisResponse, RiskProduct

REQUIRED_COLUMNS = {"product_name", "category", "stock_level", "price", "date_added"}
OPTIONAL_COLUMNS = {"expiry_date"}

HIGH_RISK_THRESHOLD = 70
MEDIUM_RISK_THRESHOLD = 40


class RiskAnalyserError(ValueError):
    """Raised when the uploaded CSV is malformed or missing required columns."""


@dataclass
class ParsedRow:
    """One typed inventory row parsed from the CSV.

    Public so other pipeline stages (e.g. the orchestrator) can re-use the
    parsed values (category, price) that the risk response intentionally drops.
    """

    product: str
    category: str
    stock_level: int
    price: float
    date_added: date
    expiry_date: Optional[date]


_ParsedRow = ParsedRow


def _parse_date(value: str, field: str, row_num: int) -> date:
    value = (value or "").strip()
    if not value:
        raise RiskAnalyserError(f"Row {row_num}: '{field}' is required.")
    
    formats = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"]
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
            
    raise RiskAnalyserError(
        f"Row {row_num}: '{field}' must be a valid date like YYYY-MM-DD (got '{value}')."
    )


def _parse_optional_date(value: str, field: str, row_num: int) -> Optional[date]:
    value = (value or "").strip()
    if not value:
        return None
    return _parse_date(value, field, row_num)


def _parse_int(value: str, field: str, row_num: int) -> int:
    value = (value or "").strip()
    if not value:
        raise RiskAnalyserError(f"Row {row_num}: '{field}' is required.")
    try:
        return int(float(value))
    except ValueError as exc:
        raise RiskAnalyserError(
            f"Row {row_num}: '{field}' must be a number (got '{value}')."
        ) from exc


def _parse_float(value: str, field: str, row_num: int) -> float:
    value = (value or "").strip()
    if not value:
        raise RiskAnalyserError(f"Row {row_num}: '{field}' is required.")
    try:
        return float(value)
    except ValueError as exc:
        raise RiskAnalyserError(
            f"Row {row_num}: '{field}' must be a number (got '{value}')."
        ) from exc


def parse_csv(content: str) -> list[ParsedRow]:
    """Validate columns and coerce rows into typed records.

    Public helper so the orchestrator can read the CSV once and reuse the
    typed rows for downstream parts (which need category/price), instead of
    re-parsing the file twice.
    """
    reader = csv.DictReader(io.StringIO(content))
    if reader.fieldnames is None:
        raise RiskAnalyserError("CSV appears to be empty.")

    headers = {h.strip() for h in reader.fieldnames}
    missing = REQUIRED_COLUMNS - headers
    if missing:
        raise RiskAnalyserError(
            f"CSV is missing required columns: {sorted(missing)}. "
            f"Expected at least {sorted(REQUIRED_COLUMNS)}."
        )

    rows: list[ParsedRow] = []
    for i, raw in enumerate(reader, start=2):
        product = (raw.get("product_name") or "").strip()
        if not product:
            raise RiskAnalyserError(f"Row {i}: 'product_name' is required.")

        rows.append(
            ParsedRow(
                product=product,
                category=(raw.get("category") or "").strip(),
                stock_level=_parse_int(raw.get("stock_level", ""), "stock_level", i),
                price=_parse_float(raw.get("price", ""), "price", i),
                date_added=_parse_date(raw.get("date_added", ""), "date_added", i),
                expiry_date=_parse_optional_date(
                    raw.get("expiry_date", ""), "expiry_date", i
                ),
            )
        )

    if not rows:
        raise RiskAnalyserError("CSV contains no product rows.")
    return rows


_parse_csv = parse_csv


def _format_exposure(value: float) -> str:
    """Format a RM value as 'RM 1,500' (integer ringgit, thousands separator)."""
    return f"RM {int(round(value)):,}"


def _score_expiry(days_to_expiry: Optional[int]) -> int:
    if days_to_expiry is None:
        return 0
    if days_to_expiry <= 7:
        return 45
    if days_to_expiry <= 14:
        return 35
    if days_to_expiry <= 30:
        return 20
    if days_to_expiry <= 60:
        return 10
    return 0


def _score_age(days_unsold: int) -> int:
    if days_unsold >= 60:
        return 35
    if days_unsold >= 30:
        return 25
    if days_unsold >= 14:
        return 15
    if days_unsold >= 7:
        return 8
    return 0


def _score_exposure(exposure_rm: float) -> int:
    if exposure_rm >= 5000:
        return 20
    if exposure_rm >= 2000:
        return 12
    if exposure_rm >= 500:
        return 6
    return 0


def _compute_risk_score(
    days_to_expiry: Optional[int],
    days_unsold: int,
    exposure_rm: float,
) -> int:
    score = (
        _score_expiry(days_to_expiry)
        + _score_age(days_unsold)
        + _score_exposure(exposure_rm)
    )
    return max(0, min(score, 100))


def _bucket(score: int) -> str:
    if score >= HIGH_RISK_THRESHOLD:
        return "high_risk"
    if score >= MEDIUM_RISK_THRESHOLD:
        return "medium_risk"
    return "low_risk"


def analyse_csv(content: str, *, today: Optional[date] = None) -> RiskAnalysisResponse:
    """Analyse a CSV string and return products grouped by risk bucket.

    Args:
        content: Raw CSV file contents (string).
        today: Override the reference "today" date; defaults to `date.today()`.
               Useful for deterministic tests.
    """
    reference_date = today or date.today()
    rows = parse_csv(content)
    return analyse_rows(rows, today=reference_date)


def analyse_rows(
    rows: list[ParsedRow], *, today: Optional[date] = None
) -> RiskAnalysisResponse:
    """Score already-parsed rows and group them into risk buckets.

    Useful for the orchestrator, which parses the CSV once and threads the
    typed rows through multiple downstream parts.
    """
    reference_date = today or date.today()

    buckets: dict[str, list[RiskProduct]] = {
        "high_risk": [],
        "medium_risk": [],
        "low_risk": [],
    }

    for row in rows:
        days_to_expiry: Optional[int] = (
            (row.expiry_date - reference_date).days
            if row.expiry_date is not None
            else None
        )
        days_unsold = max(0, (reference_date - row.date_added).days)
        exposure_rm = row.stock_level * row.price
        score = _compute_risk_score(days_to_expiry, days_unsold, exposure_rm)

        product = RiskProduct(
            product=row.product,
            units=row.stock_level,
            days_to_expiry=days_to_expiry,
            days_unsold=days_unsold,
            exposure=_format_exposure(exposure_rm),
            risk_score=score,
        )
        buckets[_bucket(score)].append(product)

    for key in buckets:
        buckets[key].sort(key=lambda p: p.risk_score, reverse=True)

    return RiskAnalysisResponse(**buckets)
