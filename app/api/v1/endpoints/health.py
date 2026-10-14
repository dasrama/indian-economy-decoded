from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.core.config import settings
from app.schemas.common import HealthCheckResponse

router = APIRouter()


@router.get("/health", response_model=HealthCheckResponse, tags=["Health"])
def health_check(db: Session = Depends(get_db)) -> HealthCheckResponse:
    """
    Check the health of the API backend and database connection (FR-19).
    """
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"unhealthy: {exc}"

    return HealthCheckResponse(
        status="ok" if db_status == "connected" else "degraded",
        database_status=db_status,
        environment=settings.APP_ENV,
        app_name=settings.APP_NAME,
        version="1.0.0",
    )
