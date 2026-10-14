from fastapi import Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.common import PaginationParams


def get_pagination(
    page: int = Query(default=1, ge=1, description="Page number starting at 1"),
    page_size: int = Query(default=50, ge=1, le=1000, description="Items per page"),
) -> PaginationParams:
    return PaginationParams(page=page, page_size=page_size)


__all__ = ["get_db", "get_pagination", "Session", "Depends"]
