from fastapi import APIRouter, HTTPException, status

from app.schemas.content import ContentGenerationRequest, ContentGenerationResponse
from app.services.content_generator import generate_content
from app.services.glm_client import GLMClientError, GLMNotConfiguredError
from app.services.glm_image_client import (
    GLMImageClientError,
    GLMImageNotConfiguredError,
)

router = APIRouter(prefix="/content", tags=["content"])


@router.post(
    "/generate",
    response_model=ContentGenerationResponse,
    summary="Generate 3 ad-copy variants + a GLM-Image-rendered image for the strategy",
)
def generate(payload: ContentGenerationRequest) -> ContentGenerationResponse:
    try:
        return generate_content(
            payload.strategy,
            product=payload.product,
            area=payload.area,
        )
    except (GLMNotConfiguredError, GLMImageNotConfiguredError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except (GLMClientError, GLMImageClientError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
