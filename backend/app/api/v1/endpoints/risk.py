from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.schemas.risk import RiskAnalysisResponse
from app.services.risk_analyser import RiskAnalyserError, analyse_csv

router = APIRouter(prefix="/risk", tags=["risk"])

MAX_UPLOAD_BYTES = 5 * 1024 * 1024


@router.post(
    "/analyse",
    response_model=RiskAnalysisResponse,
    summary="Analyse product inventory CSV for risk buckets",
)
async def analyse_inventory(
    file: UploadFile = File(..., description="CSV file with product inventory"),
) -> RiskAnalysisResponse:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .csv files are supported.",
        )

    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large (max {MAX_UPLOAD_BYTES // 1024 // 1024} MB).",
        )

    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV must be UTF-8 encoded.",
        ) from exc

    try:
        return analyse_csv(content)
    except RiskAnalyserError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
