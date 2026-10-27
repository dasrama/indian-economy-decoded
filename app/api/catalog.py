from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_pagination
from app.schemas import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    DataSourceCreate,
    DataSourceResponse,
    DataSourceUpdate,
    IndicatorCreate,
    IndicatorDetailResponse,
    IndicatorResponse,
    IndicatorUpdate,
    PaginatedResponse,
    PaginationParams,
)
from app.services import CatalogService

router = APIRouter()


# ---------------------------------------------------------------------------
# Categories Endpoints
# ---------------------------------------------------------------------------

@router.get("/categories", response_model=PaginatedResponse[CategoryResponse], tags=["Categories"])
def list_categories(
    pagination: PaginationParams = Depends(get_pagination),
    db: Session = Depends(get_db),
):
    """List indicator categories with pagination."""
    items, total = CatalogService.list_categories(db, skip=pagination.offset, limit=pagination.page_size)
    return PaginatedResponse.create(items, total, pagination)


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED, tags=["Categories"])
def create_category(category_in: CategoryCreate, db: Session = Depends(get_db)):
    """Create a new indicator category."""
    if CatalogService.get_category_by_slug(db, category_in.slug):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category with slug '{category_in.slug}' already exists",
        )
    return CatalogService.create_category(db, category_in)


@router.get("/categories/{category_id}", response_model=CategoryResponse, tags=["Categories"])
def get_category(category_id: int, db: Session = Depends(get_db)):
    """Get category by ID."""
    category = CatalogService.get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Category {category_id} not found")
    return category


@router.put("/categories/{category_id}", response_model=CategoryResponse, tags=["Categories"])
def update_category(category_id: int, category_in: CategoryUpdate, db: Session = Depends(get_db)):
    """Update an existing category."""
    category = CatalogService.get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Category {category_id} not found")
    return CatalogService.update_category(db, category, category_in)


# ---------------------------------------------------------------------------
# Data Sources Endpoints
# ---------------------------------------------------------------------------

@router.get("/sources", response_model=PaginatedResponse[DataSourceResponse], tags=["Data Sources"])
def list_sources(
    is_active: Optional[bool] = Query(None, description="Filter active status"),
    pagination: PaginationParams = Depends(get_pagination),
    db: Session = Depends(get_db),
):
    """List registered official RBI data sources."""
    items, total = CatalogService.list_sources(db, is_active=is_active, skip=pagination.offset, limit=pagination.page_size)
    return PaginatedResponse.create(items, total, pagination)


@router.post("/sources", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED, tags=["Data Sources"])
def create_source(source_in: DataSourceCreate, db: Session = Depends(get_db)):
    """Register a new official RBI data source."""
    if CatalogService.get_source_by_code(db, source_in.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Data source with code '{source_in.code}' already exists",
        )
    return CatalogService.create_source(db, source_in)


@router.get("/sources/{source_id}", response_model=DataSourceResponse, tags=["Data Sources"])
def get_source(source_id: int, db: Session = Depends(get_db)):
    """Get data source by ID."""
    source = CatalogService.get_source_by_id(db, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Data source {source_id} not found")
    return source


@router.put("/sources/{source_id}", response_model=DataSourceResponse, tags=["Data Sources"])
def update_source(source_id: int, source_in: DataSourceUpdate, db: Session = Depends(get_db)):
    """Update data source details."""
    source = CatalogService.get_source_by_id(db, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Data source {source_id} not found")
    return CatalogService.update_source(db, source, source_in)


# ---------------------------------------------------------------------------
# Indicators Endpoints (FR-15, FR-20)
# ---------------------------------------------------------------------------

@router.get("/indicators", response_model=PaginatedResponse[IndicatorResponse], tags=["Indicators"])
def list_indicators(
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    is_active: Optional[bool] = Query(None, description="Filter active status"),
    search: Optional[str] = Query(None, description="Search indicator name or code"),
    pagination: PaginationParams = Depends(get_pagination),
    db: Session = Depends(get_db),
):
    """List indicators with filtering, search, and pagination (FR-15, FR-20)."""
    items, total = CatalogService.list_indicators(
        db,
        category_id=category_id,
        is_active=is_active,
        search=search,
        skip=pagination.offset,
        limit=pagination.page_size,
    )
    return PaginatedResponse.create(items, total, pagination)


@router.post("/indicators", response_model=IndicatorResponse, status_code=status.HTTP_201_CREATED, tags=["Indicators"])
def create_indicator(indicator_in: IndicatorCreate, db: Session = Depends(get_db)):
    """Create a new economic indicator."""
    if CatalogService.get_indicator_by_code(db, indicator_in.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Indicator with code '{indicator_in.code}' already exists",
        )
    return CatalogService.create_indicator(db, indicator_in)


@router.get("/indicators/{indicator_id}", response_model=IndicatorDetailResponse, tags=["Indicators"])
def get_indicator(indicator_id: int, db: Session = Depends(get_db)):
    """Get indicator by ID including category and source details."""
    indicator = CatalogService.get_indicator_with_details(db, indicator_id)
    if not indicator:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Indicator {indicator_id} not found")
    return indicator


@router.put("/indicators/{indicator_id}", response_model=IndicatorResponse, tags=["Indicators"])
def update_indicator(indicator_id: int, indicator_in: IndicatorUpdate, db: Session = Depends(get_db)):
    """Update indicator details."""
    indicator = CatalogService.get_indicator_by_id(db, indicator_id)
    if not indicator:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Indicator {indicator_id} not found")
    return CatalogService.update_indicator(db, indicator, indicator_in)
