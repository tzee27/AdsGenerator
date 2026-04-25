from fastapi import APIRouter, HTTPException, status

from app.schemas.explanation import ExplanationRequest, ExplanationResponse
from app.services.explanation_generator import generate_explanation
from app.services.glm_client import GLMClientError, GLMNotConfiguredError

router = APIRouter(prefix="/explanation", tags=["explanation"])


@router.post(
    "/generate",
    response_model=ExplanationResponse,
    summary="Explain the chosen strategy + deterministic financial projection",
)
def generate(payload: ExplanationRequest) -> ExplanationResponse:
    try:
        return generate_explanation(
            risk=payload.risk_analysis,
            context=payload.live_context,
            strategy=payload.strategy,
            variants=payload.content_variants,
            product=payload.product,
            unit_price_rm=payload.unit_price_rm,
            area=payload.area,
        )
    except GLMNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except GLMClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
