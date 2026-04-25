from datetime import date
from io import BytesIO

from fastapi.testclient import TestClient

from app.main import app
from app.services.risk_analyser import RiskAnalyserError, analyse_csv

TODAY = date(2026, 4, 25)


def _csv(rows: list[str]) -> str:
    header = "product_name,category,stock_level,price,date_added,expiry_date"
    return "\n".join([header, *rows]) + "\n"


def test_high_risk_when_expiry_is_imminent() -> None:
    csv_content = _csv(
        [
            # Expires in 3 days -> +45; 45 units * RM10 = RM450 -> +0 exposure;
            # added 5 days ago -> +0 age. Score = 45 (medium).
            "Bread,Groceries,45,10.00,2026-04-20,2026-04-28",
            # Expires in 3 days -> +45; 40 days unsold -> +25; exposure RM4500 -> +12.
            # Score = 82 (high).
            "Old Yogurt,Groceries,300,15.00,2026-03-16,2026-04-28",
        ]
    )

    result = analyse_csv(csv_content, today=TODAY)

    assert len(result.high_risk) == 1
    assert result.high_risk[0].product == "Old Yogurt"
    assert result.high_risk[0].days_to_expiry == 3
    assert result.high_risk[0].days_unsold == 40
    assert result.high_risk[0].exposure == "RM 4,500"
    assert result.high_risk[0].risk_score == 82

    assert len(result.medium_risk) == 1
    assert result.medium_risk[0].product == "Bread"
    assert result.medium_risk[0].risk_score == 45


def test_low_risk_for_fresh_low_exposure_items() -> None:
    csv_content = _csv(
        [
            # Added 2 days ago, no expiry, low exposure -> score 0.
            "Phone Case,Electronics,10,20.00,2026-04-23,",
        ]
    )

    result = analyse_csv(csv_content, today=TODAY)

    assert len(result.low_risk) == 1
    p = result.low_risk[0]
    assert p.product == "Phone Case"
    assert p.days_to_expiry is None
    assert p.days_unsold == 2
    assert p.exposure == "RM 200"
    assert p.risk_score == 0


def test_null_expiry_still_scores_via_age_and_exposure() -> None:
    csv_content = _csv(
        [
            # No expiry, 90 days unsold -> +35, exposure 300*5=RM1500 -> +6. Score = 41 (medium).
            "Stale Gadget,Electronics,300,5.00,2026-01-25,",
        ]
    )

    result = analyse_csv(csv_content, today=TODAY)

    assert len(result.medium_risk) == 1
    p = result.medium_risk[0]
    assert p.days_to_expiry is None
    assert p.days_unsold == 90
    assert p.risk_score == 41


def test_missing_required_column_raises() -> None:
    bad_csv = "product_name,category,stock_level,price\nX,Y,1,1.00\n"
    try:
        analyse_csv(bad_csv, today=TODAY)
    except RiskAnalyserError as exc:
        assert "date_added" in str(exc)
    else:
        raise AssertionError("Expected RiskAnalyserError for missing column.")


def test_invalid_date_format_raises() -> None:
    bad_csv = _csv(["X,Y,1,1.00,25-04-2026,"])
    try:
        analyse_csv(bad_csv, today=TODAY)
    except RiskAnalyserError as exc:
        assert "YYYY-MM-DD" in str(exc)
    else:
        raise AssertionError("Expected RiskAnalyserError for bad date format.")


def test_endpoint_accepts_csv_upload() -> None:
    client = TestClient(app)
    csv_bytes = _csv(["Phone Case,Electronics,10,20.00,2026-04-23,"]).encode("utf-8")

    response = client.post(
        "/api/v1/risk/analyse",
        files={"file": ("inventory.csv", BytesIO(csv_bytes), "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    assert {"high_risk", "medium_risk", "low_risk"} <= data.keys()
    assert isinstance(data["high_risk"], list)


def test_endpoint_rejects_non_csv_filename() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/risk/analyse",
        files={"file": ("inventory.txt", BytesIO(b"x"), "text/plain")},
    )

    assert response.status_code == 400


def test_endpoint_returns_422_for_bad_csv() -> None:
    client = TestClient(app)

    bad = b"product_name,category,stock_level,price\nX,Y,1,1.00\n"
    response = client.post(
        "/api/v1/risk/analyse",
        files={"file": ("inventory.csv", BytesIO(bad), "text/csv")},
    )

    assert response.status_code == 422
