from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class DataSourceBase(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=50, description="Short code like RBI_DBIE or RBI_BULLETIN")
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
