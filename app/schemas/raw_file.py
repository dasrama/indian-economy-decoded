from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class RawFileBase(BaseModel):
    source_id: Optional[int] = None
    indicator_id: Optional[int] = None
    source_url: str = Field(..., max_length=1000)
    file_path: str = Field(..., max_length=1000)
    file_name: str = Field(..., max_length=255)
    file_format: str = Field(default="XLSX", max_length=20)
    file_size_bytes: Optional[int] = None
    file_hash: str = Field(..., max_length=64, description="SHA-256 hash of file contents")
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
