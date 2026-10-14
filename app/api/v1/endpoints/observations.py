from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_pagination
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.data_revision import DataRevisionResponse
from app.schemas.observation import (
    ChartSeriesResponse,
    ObservationCreate,
    ObservationResponse,
)
from app.services.indicator_service import IndicatorService
from app.services.observation_service import ObservationService
from app.services.revision_service import RevisionService

router = APIRouter(tags=["Observations & Time Series"])


@router.get(
    "/indicators/{indicator_id}/series",
    response_model=ChartSeriesResponse,
)
def get_chart_series(
    indicator_id: int,
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    """
    Get chart-ready JSON time series including dates, values, units, and derived metrics (FR-16).
    """
    series = ObservationService.get_chart_series(
        db, indicator_id=indicator_id, start_date=start_date, end_date=end_date
    )
    if not series:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Indicator with id {indicator_id} not found",
        )
    return series


@router.get(
    "/indicators/{indicator_id}/observations",
    response_model=PaginatedResponse[ObservationResponse],
)
def list_observations(
    indicator_id: int,
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    status: str = Query("ACTIVE", description="Observation status (e.g. ACTIVE)"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order by date"),
    pagination: PaginationParams = Depends(get_pagination),
    db: Session = Depends(get_db),
):
    """
    List raw observations for an indicator with date filtering and pagination (FR-15, FR-20).
    """
    indicator = IndicatorService.get_by_id(db, indicator_id)
    if not indicator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Indicator with id {indicator_id} not found",
        )

    items, total = ObservationService.get_for_indicator(
        db,
        indicator_id=indicator_id,
        start_date=start_date,
        end_date=end_date,
        status=status,
        sort_order=sort_order,
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


@router.post(
    "/indicators/{indicator_id}/observations",
    response_model=ObservationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_or_update_observation(
    indicator_id: int,
    obs_in: ObservationCreate,
    revision_reason: Optional[str] = Query(None, description="Reason if revising prior value"),
    db: Session = Depends(get_db),
):
    """
    Insert or update an observation.
    If the value differs from an existing record, a historical revision is preserved (FR-13).
    """
    if obs_in.indicator_id != indicator_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Mismatched indicator_id in URL ({indicator_id}) and body ({obs_in.indicator_id})",
        )

    obs, _, _ = ObservationService.upsert_observation(
        db, obs_in, revision_reason=revision_reason
    )
    return obs


@router.get(
    "/indicators/{indicator_id}/revisions",
    response_model=PaginatedResponse[DataRevisionResponse],
)
def list_revisions(
    indicator_id: int,
    pagination: PaginationParams = Depends(get_pagination),
    db: Session = Depends(get_db),
):
    """
    Retrieve historical revision audit trail for an indicator (FR-13).
    """
    indicator = IndicatorService.get_by_id(db, indicator_id)
    if not indicator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Indicator with id {indicator_id} not found",
        )

    items, total = RevisionService.list_for_indicator(
        db, indicator_id=indicator_id, skip=pagination.offset, limit=pagination.page_size
    )
    total_pages = (total + pagination.page_size - 1) // pagination.page_size
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
    )
