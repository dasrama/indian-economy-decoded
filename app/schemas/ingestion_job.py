from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


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
