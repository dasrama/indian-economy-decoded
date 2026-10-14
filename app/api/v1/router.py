from fastapi import APIRouter
from app.api.v1 import catalog, health, ingestion, observations

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(catalog.router)
api_router.include_router(observations.router)
api_router.include_router(ingestion.router)
