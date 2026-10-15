from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_pagination
from app.ingestion.selenium_scraper import RbiStatisticsScraper
from app.schemas import IngestionJobResponse, PaginatedResponse, PaginationParams, RawFileResponse
from app.services import IngestionService

router = APIRouter(prefix="/ingestion", tags=["Ingestion & Jobs"])


@router.get("/jobs", response_model=PaginatedResponse[IngestionJobResponse])
def list_ingestion_jobs(
    indicator_id: Optional[int] = Query(None, description="Filter by indicator ID"),
    status: Optional[str] = Query(None, description="Filter status (PENDING, RUNNING, COMPLETED, FAILED, SKIPPED)"),
    pagination: PaginationParams = Depends(get_pagination),
    db: Session = Depends(get_db),
):
    """List data ingestion job runs with status and record counts (FR-7)."""
    items, total = IngestionService.list_jobs(
        db, indicator_id=indicator_id, status=status, skip=pagination.offset, limit=pagination.page_size
    )
    return PaginatedResponse.create(items, total, pagination)


@router.get("/raw-files", response_model=PaginatedResponse[RawFileResponse])
def list_raw_files(
    indicator_id: Optional[int] = Query(None, description="Filter by indicator ID"),
    pagination: PaginationParams = Depends(get_pagination),
    db: Session = Depends(get_db),
):
    """List raw ingested files with download hashes and metadata (FR-5, FR-6)."""
    items, total = IngestionService.list_raw_files(
        db, indicator_id=indicator_id, skip=pagination.offset, limit=pagination.page_size
    )
    return PaginatedResponse.create(items, total, pagination)


@router.post("/trigger-selenium", status_code=status.HTTP_200_OK)
def trigger_selenium_statistics(
    indicator: str = Query("all", pattern="^(all|cpi|forex|payments)$", description="Target indicator to collect"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Trigger Selenium automation to collect official statistical data from RBI Statistics
    and store raw and processed files into the data/ directory (FR-2, FR-4).
    """
    scraper = RbiStatisticsScraper()
    if indicator == "cpi":
        return scraper.collect_cpi_inflation(db)
    elif indicator == "forex":
        return scraper.collect_forex_reference_rates(db)
    elif indicator == "payments":
        return scraper.collect_payment_systems(db)
    else:
        return scraper.collect_all(db)
