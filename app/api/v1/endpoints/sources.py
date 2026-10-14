from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_pagination
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.data_source import DataSourceCreate, DataSourceResponse, DataSourceUpdate
from app.services.data_source_service import DataSourceService

router = APIRouter(prefix="/sources", tags=["Data Sources"])


@router.get("", response_model=PaginatedResponse[DataSourceResponse])
def list_data_sources(
    is_active: Optional[bool] = Query(None, description="Filter active status"),
    pagination: PaginationParams = Depends(get_pagination),
    db: Session = Depends(get_db),
):
    """List registered RBI/DBIE data sources."""
    items, total = DataSourceService.list(
        db, is_active=is_active, skip=pagination.offset, limit=pagination.page_size
    )
    total_pages = (total + pagination.page_size - 1) // pagination.page_size
    return PaginatedResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
    )


@router.post("", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED)
def create_data_source(
    source_in: DataSourceCreate,
    db: Session = Depends(get_db),
):
    """Register a new official RBI data source."""
    existing = DataSourceService.get_by_code(db, source_in.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Data source with code '{source_in.code}' already exists",
        )
    return DataSourceService.create(db, source_in)


@router.get("/{source_id}", response_model=DataSourceResponse)
def get_data_source(
    source_id: int,
    db: Session = Depends(get_db),
):
    """Get data source by ID."""
    source = DataSourceService.get_by_id(db, source_id)
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source with id {source_id} not found",
        )
    return source


@router.put("/{source_id}", response_model=DataSourceResponse)
def update_data_source(
    source_id: int,
    source_in: DataSourceUpdate,
    db: Session = Depends(get_db),
):
    """Update data source details."""
    source = DataSourceService.get_by_id(db, source_id)
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source with id {source_id} not found",
        )
    return DataSourceService.update(db, source, source_in)
