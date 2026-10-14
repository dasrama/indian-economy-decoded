from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_pagination
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.indicator import (
    IndicatorCreate,
    IndicatorDetailResponse,
    IndicatorResponse,
    IndicatorUpdate,
)
from app.services.indicator_service import IndicatorService

router = APIRouter(prefix="/indicators", tags=["Indicators"])


@router.get("", response_model=PaginatedResponse[IndicatorResponse])
def list_indicators(
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    is_active: Optional[bool] = Query(None, description="Filter active status"),
    search: Optional[str] = Query(None, description="Search indicator name or code"),
    pagination: PaginationParams = Depends(get_pagination),
    db: Session = Depends(get_db),
):
    """List indicators with filtering, search, and pagination (FR-15, FR-20)."""
    items, total = IndicatorService.list(
        db,
        category_id=category_id,
        is_active=is_active,
        search=search,
        skip=pagination.offset,
        limit=pagination.page_size,
    )
    total_pages = (total + pagination.page_size - 1) // pagination.page_size
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
    )


@router.post("", response_model=IndicatorResponse, status_code=status.HTTP_201_CREATED)
def create_indicator(
    indicator_in: IndicatorCreate,
    db: Session = Depends(get_db),
):
    """Create a new economic indicator."""
    existing = IndicatorService.get_by_code(db, indicator_in.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Indicator with code '{indicator_in.code}' already exists",
        )
    return IndicatorService.create(db, indicator_in)


@router.get("/{indicator_id}", response_model=IndicatorDetailResponse)
def get_indicator(
    indicator_id: int,
    db: Session = Depends(get_db),
):
    """Get indicator by ID including category and source details."""
    indicator = IndicatorService.get_with_details(db, indicator_id)
    if not indicator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Indicator with id {indicator_id} not found",
        )
    return indicator


@router.put("/{indicator_id}", response_model=IndicatorResponse)
def update_indicator(
    indicator_id: int,
    indicator_in: IndicatorUpdate,
    db: Session = Depends(get_db),
):
    """Update indicator details."""
    indicator = IndicatorService.get_by_id(db, indicator_id)
    if not indicator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Indicator with id {indicator_id} not found",
        )
    return IndicatorService.update(db, indicator, indicator_in)
