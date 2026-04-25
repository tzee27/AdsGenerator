from fastapi import APIRouter

from app.api.v1.endpoints import (
    ads,
    content,
    context,
    explanation,
    health,
    risk,
    strategy,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(risk.router)
api_router.include_router(context.router)
api_router.include_router(strategy.router)
api_router.include_router(content.router)
api_router.include_router(explanation.router)
api_router.include_router(ads.router)
