from fastapi import APIRouter
from app.api.v1.endpoints import (
    categories,
    health,
    indicators,
    ingestion,
    observations,
    sources,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(categories.router)
api_router.include_router(sources.router)
api_router.include_router(indicators.router)
api_router.include_router(observations.router)
api_router.include_router(ingestion.router)
