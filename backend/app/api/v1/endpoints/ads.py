"""Two-phase ads pipeline endpoints.

POST /api/v1/ads/strategies   (multipart) — Phase A: CSV → 3 strategy options
POST /api/v1/ads/finalize     (json)      — Phase B: chosen option → ad copy + image + explanation

Status codes:
    200 — phase succeeded
    400 — non-CSV upload / bad encoding (Phase A)
    413 — file too large (Phase A)
    422 — bad CSV / invalid request body
    502 — upstream LLM/image API failure (with which-part-failed detail)
    503 — required AI provider missing API key
"""

from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status, Depends
from app.core.security import get_current_user

from app.schemas.ads import (
    AdsGenerationErrorDetail,
    FinalizeRequest,
    FinalizeResponse,
    StrategiesResponse,
)
from app.services.glm_client import GLMClientError, GLMNotConfiguredError
from app.services.glm_image_client import (
    GLMImageClientError,
    GLMImageNotConfiguredError,
)
from app.services.orchestrator import (
    OrchestratorError,
    run_phase_a,
    run_phase_b,
)
from app.services.risk_analyser import RiskAnalyserError

router = APIRouter(prefix="/ads", tags=["ads"])

MAX_UPLOAD_BYTES = 5 * 1024 * 1024


# ---------------------------------------------------------------------------
# Shared error mapping
# ---------------------------------------------------------------------------


def _build_error_detail(
    *, exc: OrchestratorError, fallback_message: str
) -> dict:
    detail = AdsGenerationErrorDetail(
        failed_part=exc.failed_part,
        error=str(exc.original) or fallback_message,
        completed=exc.completed,
        featured_product=exc.featured_product,
        area=exc.area,
    )
    return detail.model_dump()


def _raise_for_orchestrator_error(exc: OrchestratorError) -> None:
    """Map an OrchestratorError to the right HTTPException."""
    if isinstance(exc.original, (GLMNotConfiguredError, GLMImageNotConfiguredError)):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_build_error_detail(
                exc=exc, fallback_message="Required AI provider is not configured."
            ),
        ) from exc
    if isinstance(exc.original, (GLMClientError, GLMImageClientError)):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=_build_error_detail(
                exc=exc, fallback_message="Upstream AI provider call failed."
            ),
        ) from exc
    if isinstance(exc.original, ValueError):
        raise HTTPException(
            status_code=422,
            detail=_build_error_detail(
                exc=exc, fallback_message="Pipeline produced invalid intermediate data."
            ),
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=_build_error_detail(
            exc=exc, fallback_message="Pipeline failed unexpectedly."
        ),
    ) from exc


# ---------------------------------------------------------------------------
# Phase A — Strategies
# ---------------------------------------------------------------------------


@router.post(
    "/strategies",
    response_model=StrategiesResponse,
    summary="Phase A — analyse CSV, gather live context, propose 3 strategies",
    responses={
        502: {"description": "Upstream LLM API failed", "model": AdsGenerationErrorDetail},
        503: {"description": "GLM not configured (missing API key)"},
    },
)
async def strategies(
    file: UploadFile = File(..., description="CSV file with product inventory"),
    area: Optional[str] = Form(
        default=None,
        description="Optional. Override target region (e.g. 'Kuala Lumpur').",
    ),
    count: int = Form(
        default=2,
        ge=1,
        le=5,
        description="How many distinct strategies to propose (default 2, max 5).",
    ),
    current_user: dict = Depends(get_current_user),
) -> StrategiesResponse:
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
        res = run_phase_a(content, area=area, count=count)
        return res
    except RiskAnalyserError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except OrchestratorError as exc:
        _raise_for_orchestrator_error(exc)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Phase B — Finalize
# ---------------------------------------------------------------------------


@router.post(
    "/finalize",
    response_model=FinalizeResponse,
    summary="Phase B — generate ad copy + image + explanation for the chosen strategy",
    responses={
        502: {"description": "Upstream LLM/image API failed", "model": AdsGenerationErrorDetail},
        503: {"description": "GLM-text or GLM-Image not configured (missing API key)"},
    },
)
def finalize(
    payload: FinalizeRequest,
    current_user: dict = Depends(get_current_user),
) -> FinalizeResponse:
    try:
        res = run_phase_b(
            selected=payload.selected_strategy,
            risk=payload.risk_analysis,
            context=payload.live_context,
            area=payload.area,
        )
        return res
    except OrchestratorError as exc:
        _raise_for_orchestrator_error(exc)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
