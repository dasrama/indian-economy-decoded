from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_pagination
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.ingestion_job import IngestionJobResponse
from app.schemas.raw_file import RawFileResponse
from app.services.ingestion_service import IngestionService

router = APIRouter(prefix="/ingestion", tags=["Ingestion & Jobs"])


@router.get("/jobs", response_model=PaginatedResponse[IngestionJobResponse])
def list_ingestion_jobs(
    indicator_id: Optional[int] = Query(None, description="Filter by indicator ID"),
    status: Optional[str] = Query(None, description="Filter by job status (PENDING, RUNNING, COMPLETED, FAILED, SKIPPED)"),
    pagination: PaginationParams = Depends(get_pagination),
    db: Session = Depends(get_db),
):
    """List data ingestion job runs with status and record counts (FR-7)."""
    items, total = IngestionService.list_jobs(
        db,
        indicator_id=indicator_id,
        status=status,
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


@router.get("/raw-files", response_model=PaginatedResponse[RawFileResponse])
def list_raw_files(
    indicator_id: Optional[int] = Query(None, description="Filter by indicator ID"),
    pagination: PaginationParams = Depends(get_pagination),
    db: Session = Depends(get_db),
):
    """List raw ingested files with download hashes and metadata (FR-5, FR-6)."""
    items, total = IngestionService.list_raw_files(
        db,
        indicator_id=indicator_id,
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
