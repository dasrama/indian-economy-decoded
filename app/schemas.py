from datetime import date, datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Common / Pagination Schemas
# ---------------------------------------------------------------------------

class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None


class HealthCheckResponse(BaseModel):
    status: str = "ok"
    database_status: str = "connected"
    environment: str
    app_name: str
    version: str = "1.0.0"


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, description="Page number starting from 1")
    page_size: int = Field(default=50, ge=1, le=1000, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def create(cls, items: List[T], total: int, pagination: PaginationParams) -> "PaginatedResponse[T]":
        total_pages = (total + pagination.page_size - 1) // pagination.page_size if pagination.page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=total_pages,
        )


# ---------------------------------------------------------------------------
# Categories Schemas
# ---------------------------------------------------------------------------

class CategoryBase(BaseModel):
    name: str = Field(..., max_length=100)
    slug: str = Field(..., max_length=100)
    description: Optional[str] = None
    display_order: int = Field(default=0)


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    slug: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    display_order: Optional[int] = None


class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Data Sources Schemas
# ---------------------------------------------------------------------------

class DataSourceBase(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=50)
    base_url: str = Field(..., max_length=500)
    description: Optional[str] = None
    source_type: str = Field(default="EXCEL_DOWNLOAD", max_length=50)
    is_active: bool = True


class DataSourceCreate(DataSourceBase):
    pass


class DataSourceUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    code: Optional[str] = Field(None, max_length=50)
    base_url: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    source_type: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None


class DataSourceResponse(DataSourceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Indicators Schemas
# ---------------------------------------------------------------------------

class IndicatorBase(BaseModel):
    category_id: Optional[int] = None
    source_id: Optional[int] = None
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=100)
    description: Optional[str] = None
    frequency: str = Field(default="MONTHLY", max_length=20)
    units: str = Field(..., max_length=50)
    is_active: bool = True


class IndicatorCreate(IndicatorBase):
    pass


class IndicatorUpdate(BaseModel):
    category_id: Optional[int] = None
    source_id: Optional[int] = None
    name: Optional[str] = Field(None, max_length=255)
    slug: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    frequency: Optional[str] = Field(None, max_length=20)
    units: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None
    latest_observation_date: Optional[date] = None
    latest_value: Optional[float] = None


class IndicatorResponse(IndicatorBase):
    id: int
    latest_observation_date: Optional[date] = None
    latest_value: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IndicatorDetailResponse(IndicatorResponse):
    category: Optional[CategoryResponse] = None
    source: Optional[DataSourceResponse] = None


# ---------------------------------------------------------------------------
# Observations & Time Series Schemas (FR-11, FR-16)
# ---------------------------------------------------------------------------

class ObservationBase(BaseModel):
    indicator_id: int
    raw_file_id: Optional[int] = None
    observation_date: date
    value: float
    units: Optional[str] = None
    is_provisional: bool = False
    is_revised: bool = False
    revision_number: int = 0
    status: str = "ACTIVE"
    yoy_change: Optional[float] = None
    mom_change: Optional[float] = None
    moving_avg_3m: Optional[float] = None
    moving_avg_12m: Optional[float] = None
    metadata_json: Optional[Dict[str, Any]] = None


class ObservationCreate(ObservationBase):
    pass


class ObservationUpdate(BaseModel):
    value: Optional[float] = None
    units: Optional[str] = None
    is_provisional: Optional[bool] = None
    is_revised: Optional[bool] = None
    revision_number: Optional[int] = None
    status: Optional[str] = None
    yoy_change: Optional[float] = None
    mom_change: Optional[float] = None
    moving_avg_3m: Optional[float] = None
    moving_avg_12m: Optional[float] = None
    metadata_json: Optional[Dict[str, Any]] = None


class ObservationResponse(ObservationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TimeSeriesPoint(BaseModel):
    date: date
    value: float
    yoy_change: Optional[float] = None
    mom_change: Optional[float] = None
    moving_avg_3m: Optional[float] = None
    moving_avg_12m: Optional[float] = None
    is_provisional: bool = False
    is_revised: bool = False

    model_config = ConfigDict(from_attributes=True)


class ChartSeriesResponse(BaseModel):
    indicator_id: int
    indicator_code: str
    indicator_name: str
    units: str
    frequency: str
    data_points: List[TimeSeriesPoint]
    latest_date: Optional[date] = None
    latest_value: Optional[float] = None


class ObservationFilterParams(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = "ACTIVE"
    sort_order: str = Field(default="asc", pattern="^(asc|desc)$")


# ---------------------------------------------------------------------------
# Raw Files & Ingestion Schemas (FR-5, FR-7)
# ---------------------------------------------------------------------------

class RawFileBase(BaseModel):
    source_id: Optional[int] = None
    indicator_id: Optional[int] = None
    source_url: str = Field(..., max_length=1000)
    file_path: str = Field(..., max_length=1000)
    file_name: str = Field(..., max_length=255)
    file_format: str = Field(default="XLSX", max_length=20)
    file_size_bytes: Optional[int] = None
    file_hash: str = Field(..., max_length=64)
    status: str = Field(default="DOWNLOADED", max_length=30)
    error_message: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None


class RawFileCreate(RawFileBase):
    pass


class RawFileResponse(RawFileBase):
    id: int
    download_timestamp: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IngestionJobBase(BaseModel):
    indicator_id: Optional[int] = None
    raw_file_id: Optional[int] = None
    job_type: str = Field(default="SCHEDULED", max_length=50)
    status: str = Field(default="PENDING", max_length=30)
    records_extracted: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    error_message: Optional[str] = None
    log_summary: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None


class IngestionJobCreate(IngestionJobBase):
    pass


class IngestionJobUpdate(BaseModel):
    status: Optional[str] = None
    completed_at: Optional[datetime] = None
    records_extracted: Optional[int] = None
    records_inserted: Optional[int] = None
    records_updated: Optional[int] = None
    records_skipped: Optional[int] = None
    error_message: Optional[str] = None
    log_summary: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None


class IngestionJobResponse(IngestionJobBase):
    id: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Data Revision Schemas (FR-13)
# ---------------------------------------------------------------------------

class DataRevisionBase(BaseModel):
    indicator_id: int
    observation_id: Optional[int] = None
    raw_file_id: Optional[int] = None
    observation_date: date
    previous_value: float
    new_value: float
    difference: Optional[float] = None
    percentage_change: Optional[float] = None
    revision_reason: Optional[str] = Field(None, max_length=255)
    metadata_json: Optional[Dict[str, Any]] = None


class DataRevisionCreate(DataRevisionBase):
    pass


class DataRevisionResponse(DataRevisionBase):
    id: int
    revision_timestamp: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
