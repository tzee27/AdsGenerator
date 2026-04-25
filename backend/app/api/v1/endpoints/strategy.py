from fastapi import APIRouter, HTTPException, status

from app.schemas.strategy import StrategyRequest, StrategyResponse
from app.services.glm_client import GLMClientError, GLMNotConfiguredError
from app.services.strategy_decider import decide_strategy

router = APIRouter(prefix="/strategy", tags=["strategy"])


@router.post(
    "/decide",
    response_model=StrategyResponse,
    summary="Decide N diverse ad strategies from risk analysis + live context",
)
def decide(payload: StrategyRequest) -> StrategyResponse:
    try:
        return decide_strategy(
            payload.risk_analysis,
            payload.live_context,
            area=payload.area,
            count=payload.count,
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
