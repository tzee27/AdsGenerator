from fastapi import APIRouter, HTTPException, status

from app.schemas.context import LiveContextRequest, LiveContextResponse
from app.services.context_gatherer import gather_live_context
from app.services.glm_client import GLMClientError, GLMNotConfiguredError

router = APIRouter(prefix="/context", tags=["context"])


@router.post(
    "/gather",
    response_model=LiveContextResponse,
    summary="Gather today's live marketing context via GLM-5.1 web search",
)
def gather_context(payload: LiveContextRequest) -> LiveContextResponse:
    try:
        return gather_live_context(payload.products, area=payload.area)
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
